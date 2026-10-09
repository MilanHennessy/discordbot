import asyncio
import os

import discord
from dotenv import load_dotenv

import fantasy
import hockey

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise SystemExit("DISCORD_TOKEN not found")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents = intents)

@client.event
async def on_ready():
    print(f"Logged in as {client.user} (id: {client.user.id})")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content == "!ping":
        await message.channel.send("pong")
        return

    if message.content.lower().startswith("!fantasy"):
        name = message.content[len("!fantasy"):].strip()
        if not name:
            await message.channel.send(
                "Usage: !fantasy <team name>  (e.g. !fantasy The quintessential quintuplets)"
            )
            return
        async with message.channel.typing():
            try:
                report = await asyncio.wait_for(
                    asyncio.to_thread(fantasy.build_report, name), timeout=60
                )
            except asyncio.TimeoutError:
                report = "FANTASY_ERROR: ESPN is taking too long. Try again in a bit."
        await message.channel.send(report)
        return

    if message.content.lower().startswith("!hockey"):
        name = message.content[len("!hockey"):].strip()
        if not name:
            await message.channel.send(
                "Usage: !hockey <team name>  (e.g. !hockey Winter Wonderland)"
            )
            return
        async with message.channel.typing():
            try:
                report = await asyncio.wait_for(
                    asyncio.to_thread(hockey.build_report, name), timeout=60
                )
            except asyncio.TimeoutError:
                report = "HOCKEY_ERROR: ESPN is taking too long. Try again in a bit."
        await message.channel.send(report)
        return

client.run(TOKEN)