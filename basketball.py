"""ESPN fantasy basketball lookups. Sync functions; caller offloads to a thread."""

import logging
import os
import time

from dotenv import load_dotenv
from espn_api.basketball import League

import predictor

load_dotenv()  # no-op if bot.py already loaded .env; makes direct import safe

logger = logging.getLogger("basketball")

_CACHE_TTL_SECONDS = 120  # reuse one snapshot for back-to-back !basketball calls
_cache = {"at": 0.0, "league": None}
_config = None


def _get_config():
    """Read ESPN settings lazily so import order with load_dotenv can't break us."""
    global _config
    if _config is None:
        _config = {
            "league_id": int(os.environ["ESPN_LEAGUE_ID"]),
            "year": int(os.environ["ESPN_SEASON"]),
            "espn_s2": os.environ["ESPN_S2"],
            "swid": os.environ["ESPN_SWID"],
        }
    return _config


def get_league():
    """Fetch (or reuse a fresh cached) League snapshot."""
    now = time.monotonic()
    if _cache["league"] is not None and now - _cache["at"] < _CACHE_TTL_SECONDS:
        return _cache["league"]
    cfg = _get_config()
    league = League(cfg["league_id"], cfg["year"], espn_s2=cfg["espn_s2"], swid=cfg["swid"])
    _cache.update(at=now, league=league)
    return league


def find_team(league, name):
    """Case-insensitive exact match with partial-name fallback."""
    want = " ".join(name.split()).lower()
    if not want:
        return None
    for team in league.teams:
        if team.team_name.lower() == want:
            return team
    for team in league.teams:
        if want in team.team_name.lower():
            return team
    return None


def ordinal(n):
    n = int(n)
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def join_lines(*sentences):
    """One sentence per line in the Discord message."""
    return "\n".join(sentences)


def _free_agent_score(player):
    """Rank by projected average, falling back to last season average.

    Preseason: totals are 0, so projections are the only signal.
    In-season: projected avg still reflects expected rest-of-week value.
    Injured/OUT players sink to the bottom instead of being hidden,
    so users see *why* a big name isn't recommended.
    """
    proj = getattr(player, "projected_avg_points", 0) or 0
    base = proj if proj else (getattr(player, "avg_points", 0) or 0)
    if getattr(player, "injured", False):
        base -= 1000  # keeps them listed, but last
    return base


def build_free_agents(count=5):
    """Return a short ranked free-agent summary, or a *_ERROR sentinel."""
    try:
        league = get_league()
    except Exception:  # noqa: BLE001 - surfaced as user-friendly text
        logger.exception("ESPN league fetch failed")
        return "BASKETBALL_ERROR: could not reach ESPN right now. Try again in a bit."

    try:
        agents = league.free_agents(size=30)  # over-fetch, we filter + rank
    except Exception:  # noqa: BLE001 - surfaced as user-friendly text
        logger.exception("ESPN free agent fetch failed")
        return "BASKETBALL_ERROR: could not load free agents right now. Try again in a bit."

    ranked = sorted(agents, key=_free_agent_score, reverse=True)[:count]
    if not ranked:
        return "No free agents available right now."

    lines = ["Top basketball free agents to pick up:"]
    for i, p in enumerate(ranked, start=1):
        proj = getattr(p, "projected_avg_points", 0) or 0
        avg = getattr(p, "avg_points", 0) or 0
        flag = " (OUT)" if getattr(p, "injured", False) else ""
        lines.append(
            f"{i}. {p.name} ({p.position}, {p.proTeam}){flag} "
            f"- proj {proj:.1f}/game, avg {avg:.1f}/game"
        )
    return "\n".join(lines)


def build_report(team_name):
    """Return the Discord message text for a team, or a *_ERROR sentinel."""
    try:
        league = get_league()
    except Exception:  # noqa: BLE001 - surfaced as user-friendly text
        logger.exception("ESPN league fetch failed")
        return "BASKETBALL_ERROR: could not reach ESPN right now. Try again in a bit."

    team = find_team(league, team_name)
    if team is None:
        names = "\n".join(f"- {t.team_name}" for t in league.teams)
        return (
            f"BASKETBALL_ERROR: couldn't find a team matching "
            f"'{team_name}'. Try one of:\n{names}"
        )

    standing = next(
        (i for i, t in enumerate(league.standings(), start=1) if t.team_id == team.team_id),
        None,
    )
    place = ordinal(standing) if standing else "unranked"

    try:
        matchup = next(
            m
            for m in league.box_scores(matchup_total=True)
            if getattr(m.home_team, "team_id", m.home_team) == team.team_id
            or getattr(m.away_team, "team_id", m.away_team) == team.team_id
        )
    except StopIteration:
        matchup = None

    if matchup is None:
        return join_lines(
            f"Your basketball fantasy team {team.team_name} is currently "
            f"{place} place.",
            "No matchup found for this week.",
            "Good Luck!",
        )

    home, away = matchup.home_team, matchup.away_team
    home_is_us = getattr(home, "team_id", home) == team.team_id
    us_score = matchup.home_score if home_is_us else matchup.away_score
    them_score = matchup.away_score if home_is_us else matchup.home_score
    opponent = away if home_is_us else home
    opp_name = getattr(opponent, "team_name", opponent)

    lineup = matchup.home_lineup if home_is_us else matchup.away_lineup
    opp_lineup = matchup.away_lineup if home_is_us else matchup.home_lineup
    starters = [p for p in (lineup or []) if p.slot_position not in ("BE", "IR", "")]
    opp_starters = [
        p for p in (opp_lineup or []) if p.slot_position not in ("BE", "IR", "")
    ]
    top = sorted(starters, key=lambda p: p.points or 0, reverse=True)[:3]

    # Win chance from live score + pace + season record. Moves as games finish.
    us_record = (team.wins, team.losses, team.ties)
    opp = getattr(opponent, "team_id", None)  # opponent may be a plain id
    opp_team = next(
        (t for t in league.teams if t.team_id == getattr(opponent, "team_id", opp)),
        None,
    )
    them_record = (
        (opp_team.wins, opp_team.losses, opp_team.ties)
        if opp_team is not None
        else (0, 0, 0)
    )
    _, chance_text = predictor.summarize_matchup(
        starters, opp_starters, us_score, them_score, us_record, them_record
    )

    if not top:
        return join_lines(
            f"Your basketball fantasy team {team.team_name} is currently "
            f"{place} place.",
            f"Your current score in matchup is {us_score} - "
            f"{them_score} vs {opp_name}.",
            "No games counted yet this week.",
            chance_text,
            "Good Luck!",
        )

    contribs = ", ".join(f"{p.name} ({p.points})" for p in top)
    return join_lines(
        f"Your basketball fantasy team {team.team_name} is currently "
        f"{place} place.",
        f"Your current score in matchup is {us_score} - "
        f"{them_score} vs {opp_name}.",
        f"Your top contributors this week are {contribs}.",
        chance_text,
        "Good Luck!",
    )
