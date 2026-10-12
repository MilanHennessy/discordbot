"""!help text. Kept in its own module so the command list lives in one place.

bot.py calls build_help() - add new commands here and !help stays correct.
Plain functions returning strings, same style as the other helper modules.
"""


def _section(title, rows):
    """One titled block: each row is (command, description)."""
    lines = [title]
    lines.extend(f"{cmd} - {desc}" for cmd, desc in rows)
    return "\n".join(lines)


def build_help():
    """Return the full !help message text."""
    general = _section("General:", [
        ("!ping", "check the bot is alive"),
        ("!help", "show this message"),
    ])
    basketball = _section("Basketball:", [
        ("!basketball <team name>", "matchup report with win chance "
         "(e.g. !basketball The quintessential quintuplets)"),
        ("!basketball fa", "top 5 free agents to pick up"),
        ("!basketball <team name> traderec", "up to 3 trade ideas, "
         "browse with ◀ ▶ reactions"),
    ])
    hockey = _section("Hockey:", [
        ("!hockey <team name>", "matchup report with win chance "
         "(e.g. !hockey Mestizos on ice)"),
        ("!hockey fa", "top 5 free agents to pick up"),
        ("!hockey <team name> traderec", "up to 3 trade ideas, "
         "browse with ◀ ▶ reactions"),
    ])
    return "\n\n".join([general, basketball, hockey])
