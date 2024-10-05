#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install the project in editable mode along with its dependencies
pip install -e .

# Install development dependencies
pip install pytest

# Create a .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOL
MISTRAL_API_KEY=your_mistral_api_key_here
BRAVE_API_KEY=your_brave_api_key_here
ECMWF_API_KEY=your_ecmwf_api_key_here
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_CHANNEL_ID=your_discord_channel_id_here
EOL
    echo ".env file created. Please update it with your actual API keys and credentials."
else
    echo ".env file already exists. Skipping creation."
fi

echo "Environment setup complete. To activate it, run: source venv/bin/activate"