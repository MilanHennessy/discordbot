"""Deterministic 1-for-1 trade suggestions. Basic on purpose.

Idea (plain English):
- Your weakest starter + another team's strongest bench player.
- "Weakest"/"strongest" = projected value (same scorers as freeagents.py).
- Fully deterministic: sorted by (gain, names...), no randomness, so the
  same stats always give the same trades in the same order.

bot.py shows one trade per message with ◀ ▶ reaction arrows to page.
"""

import freeagents

MAX_TRADES = 3  # keep the list short, as requested
BENCH_SLOTS = {"BE", "Bench", "IR", ""}  # both sports' bench labels


def player_value(player, sport, year=None):
    """One number per player: higher means more valuable rest-of-season."""
    if sport == "basketball":
        return freeagents.score_basketball(player)
    return freeagents.score_hockey(player, year)


def is_starter(player):
    """On the active roster (not bench/IR)."""
    return (getattr(player, "lineupSlot", "") or "") not in BENCH_SLOTS


def common_slots(player_a, player_b):
    """Eligible slots both players can fill (ignores bench/IR)."""
    a = set(getattr(player_a, "eligibleSlots", []) or []) - BENCH_SLOTS
    b = set(getattr(player_b, "eligibleSlots", []) or []) - BENCH_SLOTS
    return sorted(a & b)



def value_text(player, sport, year=None):
    """Short readable value for the trade card (mirrors fa lines)."""
    if sport == "basketball":
        proj = getattr(player, "projected_avg_points", 0) or 0
        avg = getattr(player, "avg_points", 0) or 0
        return f"proj {proj:.1f}/game, avg {avg:.1f}/game"
    pts = freeagents.hockey_display_points(player, year)
    try:
        return f"proj {float(pts):.1f} pts"
    except (TypeError, ValueError):
        return "proj n/a"


def suggest_trades(my_team, other_teams, sport, year=None):
    """Return up to MAX_TRADES dicts, best gain first. Deterministic.

    Each trade: give our weakest starter, get their strongest bench
    player at a shared eligible slot. Sorted by (gain desc, then names)
    so ties always break the same way.
    """
    my_starters = [p for p in (my_team.roster or []) if is_starter(p)]
    if not my_starters:
        return []

    my_values = {p.name: player_value(p, sport, year) for p in my_starters}

    trades = []
    for other in other_teams:
        if other.team_id == my_team.team_id:
            continue
        bench = [p for p in (other.roster or []) if not is_starter(p)]
        for target in bench:
            if freeagents.is_out(target):
                continue  # never suggest trading FOR an injured player
            target_value = player_value(target, sport, year)
            for giver in my_starters:
                slots = common_slots(giver, target)
                if not slots:
                    continue  # can't legally swap these two
                gain = target_value - my_values[giver.name]
                if gain <= 0:
                    continue  # only suggest upgrades
                trades.append({
                    "give": giver,
                    "give_value": my_values[giver.name],
                    "get": target,
                    "get_value": target_value,
                    "gain": gain,
                    "partner": other.team_name,
                    "slots": slots,
                })

    # Deterministic order: biggest gain first, names break ties.
    trades.sort(key=lambda t: (-t["gain"], t["give"].name.lower(),
                               t["get"].name.lower(),
                               t["partner"].lower()))
    return trades[:MAX_TRADES]


def format_trade(trade, sport, year, index, total):
    """One trade per message, with page position for the arrow buttons."""
    give, get = trade["give"], trade["get"]
    slots = "/".join(trade["slots"][:3])  # keep the card short
    return "\n".join([
        f"Trade idea {index + 1}/{total} for {trade.get('my_name', 'your team')}:",
        f"Give: {give.name} ({give.position}, {give.proTeam})"
        f"{freeagents.out_flag(give)} - {value_text(give, sport, year)}",
        f"Get: {get.name} ({get.position}, {get.proTeam})"
        f" from {trade['partner']} - {value_text(get, sport, year)}",
        f"Slot fit: {slots} (+{trade['gain']:.1f} projected value)",
        "React ◀ / ▶ to browse.",
    ])
