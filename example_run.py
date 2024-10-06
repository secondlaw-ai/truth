from dotenv import load_dotenv
import os
from truth import VerifierAgent
from loguru import logger

# Disable logging
logger.remove()
logger.add(lambda _: None, level="CRITICAL")

load_dotenv()
mistral_api_key = os.getenv("MISTRAL_API_KEY")
brave_api_key = os.getenv("BRAVE_API_KEY")

# Initialize the VerifierAgent with the specified Mistral API key, Brave API key, and model
agent = VerifierAgent(
    mistral_api_key=mistral_api_key,
    brave_api_key=brave_api_key,
    model="mistral-small-latest",
)

# List of statements to verify
statements = [
    "The Earth is flat.",
    # "Water boils at 100 degrees Celsius at sea level.",
    "The capital of France is London.",
    # "Photosynthesis is the process by which plants convert sunlight into energy.",
]

# Verify each statement
for statement in statements:
    logger.info(f"Verifying: '{statement}'")
    output = agent.verify_statement(statement)
    print(
        f"Result: {output['result']}\nConfidence: {output['confidence']}\nSources: {output['sources']}\nExplanation: {output['explanation']}\n\n"
    )
