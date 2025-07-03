#!/usr/bin/env python3
import os
import re
import json
import glob
import yaml
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel, ValidationError
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI

# ─── 1. Load environment from ../.env ─────────────────────────────────────────
load_dotenv(find_dotenv())

# ─── 2. Discover all command YAML specs ────────────────────────────────────────
CMD_DIR = os.path.join(os.path.dirname(__file__), "..", "shared", "commands", "basic")
commands = {}
for path in glob.glob(os.path.join(CMD_DIR, "*.yaml")):
    with open(path) as f:
        spec = yaml.safe_load(f)
    name = spec["metadata"]["name"]
    commands[name] = open(path).read()

avail = ", ".join(commands.keys())

# ─── 3. Configure the LLM (OpenRouter via OpenAI‐compatible client) ─────────────
llm = ChatOpenAI(
    model_name=os.getenv("OPENROUTER_MODEL"),
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    openai_api_base=os.getenv("OPENROUTER_BASE_URL"),
    temperature=float(os.getenv("OPENROUTER_TEMPERATURE", 0.3)),
    max_tokens=int(os.getenv("OPENROUTER_MAX_TOKENS", 1000)),
)

# ─── 4. Chain to select which command to use ─────────────────────────────────
selector = PromptTemplate(
    input_variables=["text", "choices"],
    template=(
        "You are a drone command selector.\n"
        "Available commands: {choices}\n"
        "User says: “{text}”.\n"
        "Reply with exactly one command name, or “none” if none match."
    )
)
select_chain = LLMChain(llm=llm, prompt=selector)

# ─── 5. Chain to generate JSON for a chosen command ────────────────────────────
generator = PromptTemplate(
    input_variables=["text", "yaml_spec"],
    template=(
        "You are a drone controller.\n"
        "User: “{text}”\n\n"
        "Command specification:\n```yaml\n{yaml_spec}\n```\n\n"
        "Output **only** the JSON matching that spec, wrapped in ```json``` fences."
    )
)
gen_chain = LLMChain(llm=llm, prompt=generator)

# ─── 6. Pydantic schema to validate the result ─────────────────────────────────
class DroneCommand(BaseModel):
    command: str
    params: dict

# ─── 7. Helpers ───────────────────────────────────────────────────────────────
def strip_fences(markdown: str) -> str:
    """Remove ```json``` fences and return pure JSON."""
    return re.sub(r"```json\s*|\s*```", "", markdown).strip()

# ─── 8. Conversation REPL ────────────────────────────────────────────────────
def main():
    print(f"🤖 Drone demo (type ‘exit’ to quit)\nAvailable: {avail}\n")
    while True:
        text = input("USER: ").strip()
        if text.lower() in {"exit", "quit"}:
            print("👋 Goodbye!")
            break

        # 8a. Pick a command
        choice = (
            select_chain
            .predict(text=text, choices=avail)
            .strip()
            .lower()
        )
        if choice not in commands or choice == "none":
            print("❓ I couldn’t match any command. Could you rephrase?\n")
            continue

        # 8b. Generate the JSON
        raw_md = gen_chain.predict(text=text, yaml_spec=commands[choice])
        json_txt = strip_fences(raw_md)

        # 8c. Parse & validate
        try:
            payload = json.loads(json_txt)
            cmd = DroneCommand.model_validate(payload)
            print(f"✅ Executing '{cmd.command}' with params {cmd.params}\n")
        except (json.JSONDecodeError, ValidationError) as e:
            print("⚠️  Oops, couldn’t parse that JSON:\n", e, "\n")

if __name__ == "__main__":
    main()
