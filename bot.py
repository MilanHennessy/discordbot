import asyncio
import os

import discord
from dotenv import load_dotenv

import basketball
import cards
import helptext
import hockey
import trades

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise SystemExit("DISCORD_TOKEN not found")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents = intents)

LEFT, RIGHT = "◀", "▶"  # page arrows for trade cards
_trade_pages = {}  # message id -> paging state for send_paged_trades


async def send_paged_trades(channel, trade_list, sport, year):
    """Post trade 1/N with ◀ ▶ reactions; anyone can page with them."""
    if isinstance(trade_list, str):  # an *_ERROR sentinel came back
        await channel.send(trade_list)
        return
    if not trade_list:
        await channel.send(
            "No beneficial 1-for-1 trades found right now. "
            "Your starters already outrank other teams' bench players."
        )
        return
    index = 0
    msg = await channel.send(
        trades.format_trade(trade_list[index], sport, year, index, len(trade_list))
    )
    if len(trade_list) == 1:
        return  # nothing to page through
    for emoji in (LEFT, RIGHT):
        await msg.add_reaction(emoji)
    _trade_pages[msg.id] = {
        "trades": trade_list, "index": index, "sport": sport, "year": year,
    }


@client.event
async def on_reaction_add(reaction, user):
    if user == client.user:
        return  # ignore our own arrow seeds
    state = _trade_pages.get(reaction.message.id)
    if state is None:
        return  # not one of our trade cards
    if str(reaction.emoji) not in (LEFT, RIGHT):
        return
    if len(state["trades"]) < 2:
        return
    if str(reaction.emoji) == LEFT:
        state["index"] = (state["index"] - 1) % len(state["trades"])
    else:
        state["index"] = (state["index"] + 1) % len(state["trades"])
    await reaction.message.edit(
        content=trades.format_trade(
            state["trades"][state["index"]], state["sport"], state["year"],
            state["index"], len(state["trades"]),
        )
    )
    try:
        await reaction.message.remove_reaction(reaction.emoji, user)
    except discord.HTTPException:
        pass  # missing Manage Messages perm; harmless


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
    if message.content.lower().strip() == "!help":
        await message.channel.send(helptext.build_help())
        return
    if message.content.lower().strip() == "!hockeypull":
        player, team, tier, value = await asyncio.to_thread(cards.pull_card)
        count = await asyncio.to_thread(
            cards.save_pull, player, team, tier, value
        )
        embed_data, image_url = await asyncio.to_thread(
            cards.build_pull_embed, player, team, tier, value, count
        )
        embed = discord.Embed.from_dict(embed_data)
        if image_url:
            embed.set_thumbnail(url=image_url)
        await message.channel.send(embed=embed)
        return

    if message.content.lower().startswith("!basketball"):
        name = message.content[len("!basketball"):].strip()
        if not name:
            await message.channel.send(
                "Usage: !basketball <team name>  (e.g. !basketball The quintessential quintuplets)"
                " or !basketball fa for top free agents"
                " or !basketball <team name> traderec for trade ideas"
            )
            return
        if name.lower() == "fa":
            async with message.channel.typing():
                try:
                    report = await asyncio.wait_for(
                        asyncio.to_thread(basketball.build_free_agents), timeout=60
                    )
                except asyncio.TimeoutError:
                    report = "BASKETBALL_ERROR: ESPN is taking too long. Try again in a bit."
            await message.channel.send(report)
            return
        if name.lower().endswith("traderec"):
            team_name = name[: -len("traderec")].strip()
            if not team_name:
                await message.channel.send(
                    "Usage: !basketball <team name> traderec  "
                    "(e.g. !basketball The quintessential quintuplets traderec)"
                )
                return
            async with message.channel.typing():
                try:
                    found = await asyncio.wait_for(
                        asyncio.to_thread(basketball.build_trades, team_name),
                        timeout=120,
                    )
                except asyncio.TimeoutError:
                    found = "BASKETBALL_ERROR: ESPN is taking too long. Try again in a bit."
            await send_paged_trades(
                message.channel, found, "basketball",
                basketball._get_config()["year"],
            )
            return
        async with message.channel.typing():
            try:
                report = await asyncio.wait_for(
                    asyncio.to_thread(basketball.build_report, name), timeout=60
                )
            except asyncio.TimeoutError:
                report = "BASKETBALL_ERROR: ESPN is taking too long. Try again in a bit."
        await message.channel.send(report)
        return

    if message.content.lower().startswith("!hockey"):
        name = message.content[len("!hockey"):].strip()
        if not name:
            await message.channel.send(
                "Usage: !hockey <team name>  (e.g. !hockey Winter Wonderland)"
                " or !hockey fa for top free agents"
                " or !hockey <team name> traderec for trade ideas"
            )
            return
        if name.lower() == "fa":
            async with message.channel.typing():
                try:
                    report = await asyncio.wait_for(
                        asyncio.to_thread(hockey.build_free_agents), timeout=60
                    )
                except asyncio.TimeoutError:
                    report = "HOCKEY_ERROR: ESPN is taking too long. Try again in a bit."
            await message.channel.send(report)
            return
        if name.lower().endswith("traderec"):
            team_name = name[: -len("traderec")].strip()
            if not team_name:
                await message.channel.send(
                    "Usage: !hockey <team name> traderec  "
                    "(e.g. !hockey Winter Wonderland traderec)"
                )
                return
            async with message.channel.typing():
                try:
                    found = await asyncio.wait_for(
                        asyncio.to_thread(hockey.build_trades, team_name),
                        timeout=120,
                    )
                except asyncio.TimeoutError:
                    found = "HOCKEY_ERROR: ESPN is taking too long. Try again in a bit."
            await send_paged_trades(
                message.channel, found, "hockey",
                hockey._get_config()["year"],
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