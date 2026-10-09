"""ESPN fantasy basketball lookups. Sync functions; caller offloads to a thread."""

import logging
import os
import time

from dotenv import load_dotenv
from espn_api.basketball import League

load_dotenv()  # no-op if bot.py already loaded .env; makes direct import safe

logger = logging.getLogger("fantasy")

_CACHE_TTL_SECONDS = 120  # reuse one snapshot for back-to-back !fantasy calls
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


def build_report(team_name):
    """Return the Discord message text for a team, or a *_ERROR sentinel."""
    try:
        league = get_league()
    except Exception:  # noqa: BLE001 - surfaced as user-friendly text
        logger.exception("ESPN league fetch failed")
        return "FANTASY_ERROR: could not reach ESPN right now. Try again in a bit."

    team = find_team(league, team_name)
    if team is None:
        names = "\n".join(f"- {t.team_name}" for t in league.teams)
        return (
            f"FANTASY_ERROR: couldn't find a team matching "
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
        return (
            f"Your basketball fantasy team {team.team_name} is currently "
            f"{place} place. No matchup found for this week. Good Luck"
        )

    home, away = matchup.home_team, matchup.away_team
    home_is_us = getattr(home, "team_id", home) == team.team_id
    us_score = matchup.home_score if home_is_us else matchup.away_score
    them_score = matchup.away_score if home_is_us else matchup.home_score
    opponent = away if home_is_us else home
    opp_name = getattr(opponent, "team_name", opponent)

    lineup = matchup.home_lineup if home_is_us else matchup.away_lineup
    starters = [p for p in (lineup or []) if p.slot_position not in ("BE", "IR", "")]
    top = sorted(starters, key=lambda p: p.points or 0, reverse=True)[:3]

    if not top:
        return (
            f"Your basketball fantasy team {team.team_name} is currently "
            f"{place} place. Your current score in matchup is {us_score} - "
            f"{them_score} vs {opp_name}. No games counted yet this week. "
            f"Good Luck"
        )

    contribs = ", ".join(f"{p.name} ({p.points})" for p in top)
    return (
        f"Your basketball fantasy team {team.team_name} is currently "
        f"{place} place. Your current score in matchup is {us_score} - "
        f"{them_score} vs {opp_name}. Your top contributors this week are "
        f"{contribs}. Good Luck"
    )
