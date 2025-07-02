import importlib.metadata  # For getting package version reliably
import json
import os
import sys  # For getting Python version
import time

from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

# --- Configuration Section: Easily modify these parameters ---
# IMPORTANT: Store your OpenRouter API Key securely as an environment variable.
# For example, in your shell: export OPENROUTER_API_KEY="sk-or-v1-YOUR_OPENROUTER_API_KEY"
# DO NOT hardcode your API key directly in this file if you plan to commit it to a public repository!
# If you must hardcode for a quick, *local-only* test, uncomment the line below:
# OPENROUTER_API_KEY = "sk-or-v1-YOUR_OPENROUTER_API_KEY_HERE"

# Model to test. You can find available models and their statuses on openrouter.ai/models
# Example free models:
# "google/gemma-2-9b-it:free"
# "deepseek/deepseek-r1-0528-qwen3-8b:free"
MODEL_TO_TEST = "google/gemma-2-9b-it:free"

# Your system message: Defines the AI's persona or instructions for the conversation.
SYSTEM_MESSAGE = (
    "You are a helpful and concise AI assistant. Provide direct and factual answers."
)

# The user's prompt/question: The primary input for the LLM.
USER_PROMPT = "Tell me a very short and interesting fact about the Persian Empire."

# API parameters for the chat completion request
TEMPERATURE = 0.7  # Controls randomness. 0.0 is deterministic, 1.0 is highly creative.
MAX_TOKENS = 200  # Maximum number of tokens (approx. words/pieces of words) in the AI's response.
# Increase if responses are consistently cut off.
NUM_RETRIES = 3  # Number of times to retry the API call if it fails or returns empty.
RETRY_DELAY_SECONDS = (
    5  # Delay in seconds between retry attempts to avoid hammering the API.
)

# --- End Configuration Section ---


def get_openai_version():
    """Attempts to get the installed OpenAI library version."""
    try:
        # For openai>=1.0.0
        return importlib.metadata.version("openai")
    except importlib.metadata.PackageNotFoundError:
        try:
            # Fallback for older openai versions if __version__ existed directly
            import openai

            return getattr(openai, "__version__", "Unknown (older version?)")
        except ImportError:
            return "Not installed"
    except Exception:
        return "Error getting version"


def run_llm_test():
    """
    Executes a test API call to an LLM via OpenRouter, reporting comprehensive details
    about the request, response, and any errors encountered.
    Includes robust retry logic for transient issues and clear developer/user output.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("\n" + "=" * 80)
        print("!!! ERROR: OpenRouter API Key Not Found !!!".center(80))
        print(
            "Please set the 'OPENROUTER_API_KEY' environment variable before running this script."
        )
        print(
            '  Example for Linux/macOS: export OPENROUTER_API_KEY="sk-or-v1-YOUR_KEY_HERE"'
        )
        print(
            '  Example for Windows (CMD): set OPENROUTER_API_KEY="sk-or-v1-YOUR_KEY_HERE"'
        )
        print(
            '  Example for Windows (PowerShell): $env:OPENROUTER_API_KEY="sk-or-v1-YOUR_KEY_HERE"'
        )
        print(
            "\nFor local development ONLY, you can uncomment and assign 'OPENROUTER_API_KEY' directly in the script,"
        )
        print("but BE CAREFUL NOT TO COMMIT YOUR KEY TO VERSION CONTROL!")
        print("=" * 80 + "\n")
        return

    print("\n" + "=" * 80)
    print("--- OpenRouter LLM Test Tool v1.0 ---".center(80))
    print(f"Python Version: {sys.version.split()[0]}".center(80))
    print(f"OpenAI Library Version: {get_openai_version()}".center(80))
    print(f"API Key loaded (first 5 chars): {api_key[:5]}...".center(80))
    print("=" * 80 + "\n")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": USER_PROMPT},
    ]

    request_payload = {
        "model": MODEL_TO_TEST,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "extra_headers": {
            "HTTP-Referer": "https://dronesphere.com",  # Replace with your project's actual URL/name
            "X-Title": "Dronesphere LLM Test Tool",  # Unique title for OpenRouter analytics
        },
    }

    print("\n" + "-" * 30 + " Request Details " + "-" * 30)
    print(f"Target Model: {MODEL_TO_TEST}")
    print(f"System Message: '{SYSTEM_MESSAGE}'")
    print(f"User Prompt: '{USER_PROMPT}'")
    print(f"Configured Temperature: {TEMPERATURE}")
    print(f"Configured Max Tokens: {MAX_TOKENS}")
    print("\nRaw Request Payload (for developer debugging):")
    # Use json.dumps for pretty printing the dict
    print(json.dumps(request_payload, indent=2))
    print("-" * (60 + len(" Request Details ")) + "\n")

    successful_response_received = False
    for attempt in range(1, NUM_RETRIES + 1):
        print(
            f"Attempt {attempt}/{NUM_RETRIES}: Sending request to '{MODEL_TO_TEST}'..."
        )

        try:
            completion = client.chat.completions.create(**request_payload)

            if completion.choices:
                assistant_response = completion.choices[0].message.content
                finish_reason = completion.choices[0].finish_reason

                print("\n" + "-" * 30 + " LLM Response Analysis " + "-" * 26)
                print(f"Model that responded: {completion.model}")
                print(f"Response ID: {completion.id}")
                print(
                    f"Finish Reason: {finish_reason} (Indicates why the model stopped generating)"
                )

                if assistant_response and assistant_response.strip():
                    print("\n" + "=" * 20 + " Assistant's Reply " + "=" * 20)
                    print(assistant_response.strip())
                    print("=" * 61 + "\n")
                    print(
                        "--- Status: TEST SUCCESSFUL! LLM provided a meaningful response. ---"
                    )
                    successful_response_received = True
                else:
                    print(
                        "\n--- WARNING: Empty or Whitespace-Only Response Content ---"
                    )
                    print(
                        "The model responded, but the content was empty or just whitespace."
                    )
                    print(f"Raw content received: '{assistant_response}'")
                    print(f"Finish Reason: {finish_reason}")
                    print(
                        "This often indicates high load on free models, or a very short `max_tokens`."
                    )

                # Always print token usage if available for transparency
                if completion.usage:
                    print("\n--- Token Usage Metrics ---")
                    print(f"  Prompt Tokens (Input): {completion.usage.prompt_tokens}")
                    print(
                        f"  Completion Tokens (Output): {completion.usage.completion_tokens}"
                    )
                    print(f"  Total Tokens: {completion.usage.total_tokens}")
                    print(
                        "Note: For free models, these might be reported as 0/0 or actual usage."
                    )
                print("-" * (60 + len(" LLM Response Analysis ")) + "\n")

            else:
                print("\n--- WARNING: No Message Choices Found in Response ---")
                print(
                    "The API call was successful, but the model did not return any 'choices' in its response."
                )
                print(
                    "This is unusual and suggests an unexpected API response structure or an issue with the model."
                )
                print("Dumping full completion object for developer debugging:")
                print(
                    json.dumps(completion.model_dump(), indent=2)
                )  # Use model_dump() for pydantic object
                print("-" * (60 + len(" LLM Response Analysis ")) + "\n")

            if successful_response_received:
                return  # Exit if we got a good response

        except AuthenticationError as e:
            print("\n" + "!" * 80)
            print("!!! AUTHENTICATION ERROR (401) !!!".center(80))
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {e.message}")
            print(
                "\nACTION REQUIRED: Your API key is likely incorrect, expired, or has insufficient permissions."
            )
            print(
                "Please regenerate your OpenRouter API key and update your environment variable."
            )
            print("!" * 80 + "\n")
            return  # Critical error, no point in retrying

        except RateLimitError as e:
            print("\n" + "!" * 80)
            print("!!! RATE LIMIT EXCEEDED (429) !!!".center(80))
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {e.message}")
            print("\nACTION: You are sending too many requests too quickly.")
            print(
                "Consider: waiting longer, reducing NUM_RETRIES/RETRY_DELAY_SECONDS, or upgrading your OpenRouter plan."
            )
            print("!" * 80 + "\n")
            if attempt < NUM_RETRIES:
                print(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                print("Max retries reached due to rate limits. Giving up.")
                return

        except APIStatusError as e:
            # Handles other HTTP errors (e.g., 400 Bad Request, 404 Not Found, 500 Internal Server Error)
            print(f"\n--- API STATUS ERROR (HTTP {e.status_code}) ---")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {e.message}")
            if e.response:
                print(f"Response Body (for developer debugging): {e.response.text}")
            print("\nPossible causes:")
            if e.status_code == 400:
                print(
                    "- Bad Request: Check your prompt format or API parameters against OpenRouter documentation."
                )
            elif e.status_code == 404:
                print(
                    "- Not Found: The model name might be incorrect or unavailable: '{MODEL_TO_TEST}'."
                )
            elif e.status_code >= 500:
                print(
                    "- Server Error: OpenRouter or the model provider might be experiencing temporary issues."
                )
            print("-------------------------------------------\n")
            if attempt < NUM_RETRIES:
                print(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                print("Max retries reached due to API status error. Giving up.")
                return

        except APIConnectionError as e:
            # Handles network-related errors (e.g., DNS resolution failure, connection refused)
            print("\n--- CONNECTION ERROR ---")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {e.message}")
            print(
                "\nACTION: Check your internet connection. Proxies or firewalls might be interfering."
            )
            print(
                "Given your location (Iran), network connectivity to external APIs can sometimes be challenging."
            )
            print("------------------------\n")
            if attempt < NUM_RETRIES:
                print(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                print("Max retries reached due to connection error. Giving up.")
                return

        except Exception as e:
            # Catches any other unexpected errors
            print("\n--- UNEXPECTED ERROR ---")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {e}")
            print(
                "\nThis is an unforeseen error. Please review the traceback (if any) above."
            )
            print("Consider reporting this with full details if it persists.")
            print("------------------------\n")
            if attempt < NUM_RETRIES:
                print(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                print("Max retries reached due to unexpected error. Giving up.")
                return

    if not successful_response_received:
        print("\n" + "=" * 80)
        print(
            "!!! FINAL STATUS: ALL ATTEMPTS FAILED TO GET A MEANINGFUL RESPONSE !!!".center(
                80
            )
        )
        print("\nRecommendations:")
        print("  - Double-check the `MODEL_TO_TEST` name in the script for typos.")
        print("  - Increase `MAX_TOKENS` if responses are consistently cut off.")
        print("  - Try a simpler or different `USER_PROMPT` or `SYSTEM_MESSAGE`.")
        print(
            "  - Consider using a different LLM model from OpenRouter (`openrouter.ai/models`)."
        )
        print("  - The free tier might be under very heavy load; try again later.")
        print("  - Review your OpenRouter account usage and limits.")
        print(
            "  - Investigate network stability, especially if you are in Iran, as connections to external services can be interrupted."
        )
        print("=" * 80 + "\n")


if __name__ == "__main__":
    run_llm_test()
