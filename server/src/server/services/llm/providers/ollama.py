"""
Ollama LLM provider – **v2** (normaliser-aware, provider-agnostic).
"""

from typing import Any, Dict, List, Optional, Tuple
import httpx, structlog, asyncio
from pydantic import BaseModel, Field
from ..base import (
    BaseLLMProvider,
    ClarificationRequest,
    ClarificationResponse,
    CommandExtractionResult,
    ConversationContext,
)
from ..config import OllamaConfig
from ..parsing import create_command_parser
from ..normalisation import normalise_commands          # ← NEW

logger = structlog.get_logger()


# ── Pydantic mirror for parser output ──────────────────────────────
class _Cmd(BaseModel):
    name: str
    category: str
    parameters: Dict[str, Any] = {}
    confidence: float = 1.0
    original_phrase: str = ""


class _Extraction(BaseModel):
    commands: List[_Cmd] = []
    response_text: str = ""
    requires_clarification: bool = False
    clarification_questions: List[str] = []
    detected_language: str = "en"
    overall_confidence: float = 1.0


# ── Ollama wire models ─────────────────────────────────────────────
class _OMessage(BaseModel):
    role: str
    content: str


class _ORequest(BaseModel):
    model: str
    messages: List[_OMessage]
    stream: bool = False
    temperature: Optional[float] = None
    num_predict: Optional[int] = None
    format: Optional[str] = None
    system: Optional[str] = None


# ── Provider implementation ───────────────────────────────────────
class OllamaProvider(BaseLLMProvider):
    def __init__(self, config: OllamaConfig):
        self._cfg = config
        self._cli = httpx.AsyncClient(base_url=config.base_url, timeout=config.timeout)
        super().__init__(config.dict(), parser=create_command_parser())
        logger.info("Ollama provider initialised", model=config.model)

    # ── low-level call helper ────────────────────────────────────
    async def _call(self, msgs: List[Dict[str, str]], temp: float, force_json: bool, sys: str = None) -> str:
        req = _ORequest(
            model=self._cfg.model,
            messages=[_OMessage(**m) for m in msgs],
            temperature=temp,
            num_predict=self._cfg.max_tokens,
            format="json" if force_json else None,
            system=sys,
        )
        resp = await self._cli.post("/api/chat", json=req.dict(exclude_none=True))
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    # ────────────────────────────────────────────────────────────
    async def extract_commands(
        self, user_input: str, context: ConversationContext, available_commands: List[Dict[str, Any]]
    ) -> CommandExtractionResult:
        from ..prompts.builder import prompt_builder

        sys_prompt = prompt_builder.build_extraction_prompt(
            user_input=user_input,
            available_commands=available_commands,
            context={
                "drone_id": context.drone_id,
                "status": context.drone_state.get("status", "unknown") if context.drone_state else "disconnected",
                "battery": context.drone_state.get("battery", 0) if context.drone_state else 0,
            },
        )

        msgs = [dict(role="user", content=user_input)]
        raw = await self._call(
            msgs, temp=self._cfg.command_extraction_temperature, force_json=True, sys=sys_prompt
        )
        logger.debug("Raw Ollama output", slice=raw[:200])

        parsed = self.parser.parse(raw, pydantic_model=_Extraction, original_prompt=user_input)
        cmds = normalise_commands([c.dict() for c in parsed.commands])
        needs_clar = parsed.requires_clarification or not cmds

        return CommandExtractionResult(
            commands=cmds,
            confidence=parsed.overall_confidence,
            response_text=parsed.response_text,
            requires_clarification=needs_clar,
            clarification_questions=parsed.clarification_questions,
            detected_language=parsed.detected_language,
        )

    # ── remaining helper methods (generate_response, etc.) stay the same ──
    async def generate_response(self, prompt: str, context: Optional[ConversationContext] = None, **_) -> str:
        msgs = [dict(role="user", content=prompt)]
        return await self._call(msgs, temp=self._cfg.conversation_temperature, force_json=False)

    async def handle_clarification(self, c: ClarificationRequest) -> ClarificationResponse:
        txt = await self.generate_response(f"Please clarify: {c.original_input}", c.context)
        return ClarificationResponse(clarified_input="", confidence=0.0, response_text=txt)

    async def format_error_response(self, error: Exception, context: ConversationContex
