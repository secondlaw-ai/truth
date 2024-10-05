import discord
import asyncio
from typing import List, Dict

class DiscordFetcher:
    def __init__(self, token: str):
        self.client = discord.Client(intents=discord.Intents.default())
        self.token = token

    async def fetch_messages(self, channel_id: int, limit: int = 100) -> List[Dict]:
        channel = await self.client.fetch_channel(channel_id)
        messages = []
        async for message in channel.history(limit=limit):
            messages.append({
                'id': message.id,
                'content': message.content,
                'author': str(message.author),
                'timestamp': message.created_at.isoformat()
            })
        return messages

    async def run_fetch(self, channel_id: int, limit: int = 100) -> List[Dict]:
        await self.client.login(self.token)
        try:
            return await self.fetch_messages(channel_id, limit)
        finally:
            await self.client.close()

    def get_messages(self, channel_id: int, limit: int = 100) -> List[Dict]:
        return asyncio.run(self.run_fetch(channel_id, limit))

# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    
    discord_token = os.getenv("DISCORD_TOKEN")
    channel_id = int(os.getenv("DISCORD_CHANNEL_ID"))

    fetcher = DiscordFetcher(discord_token)
    messages = fetcher.get_messages(channel_id)
    print(f"Fetched {len(messages)} messages")
    for msg in messages[:5]:  # Print first 5 messages
        print(f"{msg['author']}: {msg['content']}")