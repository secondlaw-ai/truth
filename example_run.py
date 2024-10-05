from dotenv import load_dotenv
load_dotenv()  # This loads the environment variables from .env

import os
from truth import Verifier

# Get API keys from environment variables
mistral_api_key = os.getenv("MISTRAL_API_KEY")
brave_api_key = os.getenv("BRAVE_API_KEY")

# Initialize the Verifier
verifier = Verifier(mistral_api_key=mistral_api_key, brave_api_key=brave_api_key)

# List of statements to verify
statements = [
    "The Earth is flat.",
    "Water boils at 100 degrees Celsius at sea level.",
    "The capital of France is London.",
    "Photosynthesis is the process by which plants convert sunlight into energy.",
]

# Verify each statement
for statement in statements:
    print(f"Verifying: '{statement}'")
    result = verifier.verify(statement)
    print(f"Result: {result}\n")