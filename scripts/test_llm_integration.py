#!/usr/bin/env python3
# scripts/test_llm_integration.py
"""
Test script for LangChain + OpenRouter integration.

This script demonstrates:
1. LLM service initialization
2. Command extraction from natural language
3. Multi-language support
4. Command queue generation
5. Confidence scoring
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Now we can import our modules
from server.src.server.services.llm.base import LLMConfig
from server.src.server.services.llm.langchain_service import LangChainService, ChatRequest

console = Console()


class TestScenario:
    """Test scenario for LLM integration"""
    
    def __init__(self, name: str, inputs: List[str], language: str = "en"):
        self.name = name
        self.inputs = inputs
        self.language = language
        self.results = []


async def test_llm_service():
    """Test the LLM service with various scenarios"""
    
    console.print(Panel.fit("🤖 DroneSphere LLM Integration Test", style="bold blue"))
    
    # Initialize service
    console.print("\n[yellow]Initializing LangChain service...[/yellow]")
    
    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        console.print("[red]❌ OPENROUTER_API_KEY not found in environment![/red]")
        console.print("Please set: export OPENROUTER_API_KEY=your-key-here")
        return False
    
    # Create config
    config = LLMConfig(
        provider="openrouter",
        model=os.getenv("OPENROUTER_MODEL", "google/gemma-2-9b-it:free"),
        api_key=api_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        temperature=0.7,
        max_tokens=2000,
        confidence_threshold=0.7,
        require_confirmation=True,
        headers={
            "HTTP-Referer": "https://dronesphere.ai",
            "X-Title": "DroneSphere Test"
        }
    )
    
    # Initialize service
    service = LangChainService()
    try:
        await service.initialize(config)
        console.print("[green]✅ Service initialized successfully![/green]")
    except Exception as e:
        console.print(f"[red]❌ Failed to initialize: {e}[/red]")
        return False
    
    # Define test scenarios
    scenarios = [
        TestScenario(
            "Basic Takeoff",
            [
                "Take off to 20 meters",
                "Launch the drone to 50 feet please",
                "Can you make the drone go up to 15 meters?"
            ]
        ),
        TestScenario(
            "Basic Landing",
            [
                "Land the drone",
                "Please land now",
                "Bring it down safely"
            ]
        ),
        TestScenario(
            "Multi-Command",
            [
                "Take off to 10 meters and then land",
                "Launch to 20m, wait a bit, then come back down",
                "First takeoff to 15 meters, then land slowly"
            ]
        ),
        TestScenario(
            "Persian Commands",
            [
                "پرواز کن به ارتفاع ۲۰ متر",
                "فرود بیا",
                "برخیز و بعد فرود بیا"
            ],
            language="fa"
        ),
        TestScenario(
            "Ambiguous Commands",
            [
                "Go up high",
                "Take off",  # No altitude specified
                "Land somewhere safe"
            ]
        ),
        TestScenario(
            "Safety & Status",
            [
                "What's the drone status?",
                "Is it safe to take off?",
                "Emergency stop!"
            ]
        )
    ]
    
    # Run scenarios
    session_id = "test-session-001"
    
    for scenario in scenarios:
        console.print(f"\n[bold cyan]Testing: {scenario.name}[/bold cyan]")
        console.print("=" * 50)
        
        for i, user_input in enumerate(scenario.inputs, 1):
            console.print(f"\n[blue]Test {i}:[/blue] {user_input}")
            
            try:
                # Create chat request
                request = ChatRequest(
                    message=user_input,
                    session_id=f"{session_id}-{scenario.name}",
                    drone_id="test-drone-01",
                    language=scenario.language if scenario.language != "en" else None,
                    extract_commands=True,
                    execute_immediately=False
                )
                
                # Process
                response = await service.process_chat(request)
                
                # Display response
                console.print(f"[green]AI Response:[/green] {response.response}")
                console.print(f"[dim]Language: {response.language} | Confidence: {response.confidence:.2f}[/dim]")
                
                # Display extracted commands
                if response.commands:
                    table = Table(title="Extracted Commands")
                    table.add_column("Type", style="cyan")
                    table.add_column("Parameters", style="yellow")
                    table.add_column("Confidence",