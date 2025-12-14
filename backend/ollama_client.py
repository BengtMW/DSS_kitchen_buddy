# Helper to talk to the local Ollama model via HTTP
import os
import requests

# Use environment variables if available, otherwise default values
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

def ollama_chat(messages, temperature: float = 0.2) -> str:
    """
    Sends chat messages to the local Ollama model
    and returns the assistant's reply text.
    """
    payload = {
        "model": OLLAMA_MODEL,        # Which model to use (default = llama3)
        "messages": messages,         # Chat conversation: system + user
        "stream": False,              # Wait for full output
        "options": {
            "temperature": temperature  # Randomness control
        },
    }

    # Send POST request to Ollama server
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()  # Throw error if the request failed

    data = resp.json()       # Parse JSON response

    # Return ONLY the assistant's message text
    return data["message"]["content"]