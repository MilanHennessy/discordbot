"""Shared free-agent ranking. Basic on purpose, no new dependencies.

Each sport's lib stores player stats differently, so this module has
one small scorer per sport plus shared display helpers:

- score_basketball(player) - uses projected_avg_points / avg_points
- score_hockey(player, year) - reads the stats dict (Projected/Last 30/Total)
- rank_and_format(...) - shared top-N sort + numbered-line formatting

basketball.py and hockey.py stay thin: fetch the league, fetch agents,
then call into here.
"""

INJURED_PENALTY = 100000  # sinks OUT players to the bottom instead of hiding them


def is_goalie(player):
    """True if this player staffs the net (hockey only)."""
    return (getattr(player, "position", "") or "").lower() == "goalie"


def is_out(player):
    """True if ESPN flags the player injured (either sport)."""
    return bool(getattr(player, "injured", False))


def out_flag(player):
    """Display suffix so users see *why* a big name isn't recommended."""
    return " (OUT)" if is_out(player) else ""


def score_basketball(player):
    """Rank by projected average, falling back to season average.

    Preseason totals are 0, so projections are the only signal.
    In-season, projected avg still reflects expected rest-of-week value.
    """
    proj = getattr(player, "projected_avg_points", 0) or 0
    base = proj if proj else (getattr(player, "avg_points", 0) or 0)
    if is_out(player):
        base -= INJURED_PENALTY / 100  # smaller scale than hockey totals
    return base


def _hockey_total(player, key):
    """Pull one fantasy-point number out of the hockey stats dict."""
    stats = getattr(player, "stats", {}) or {}
    entry = stats.get(key) or {}
    total = entry.get("total") or {}
    if not isinstance(total, dict):
        return 0
    for k in ("appliedTotal", "total", "PTS", "points"):
        if k in total and isinstance(total[k], (int, float)):
            return total[k]
    # No single total: goals + assists + power-play points is a decent proxy.
    parts = [total.get(k, 0) for k in ("G", "A", "PPG", "PPA")]
    if any(isinstance(v, (int, float)) and v for v in parts):
        return sum(v for v in parts if isinstance(v, (int, float)))
    if is_goalie(player):
        return 0  # goalie raw totals (saves, minutes) are useless; see below
    vals = [v for v in total.values() if isinstance(v, (int, float))]
    return sum(vals) / len(vals) if vals else 0


def _hockey_goalie_score(player, key):
    """Basic goalie proxy: wins + shutouts + save-pct / GAA edges.

    Raw save and minute totals are on a useless scale, so we build a
    small number from the stats that actually win fantasy weeks.
    """
    stats = getattr(player, "stats", {}) or {}
    total = (stats.get(key) or {}).get("total") or {}
    if not isinstance(total, dict):
        return 0

    def num(*keys):
        for k in keys:
            v = total.get(k)
            if isinstance(v, (int, float)):
                return v
        return 0

    wins = num("W")
    shutouts = num("SO")
    sv_pct = num("SV%", "SVP")
    gaa = num("GAA")
    games = num("GS", "GP", "30") or 1
    edge = (sv_pct - 0.900) * 100 if sv_pct else 0  # vs ~league-average .900
    gaa_edge = (3.0 - gaa) * 2 if gaa else 0  # vs rough-average 3.00 GAA
    per_game = (wins + shutouts * 2 + edge + gaa_edge) / games
    return per_game * 82  # full-season scale, comparable to skater totals


def score_hockey(player, year):
    """Rank by projected total, falling back to recent form.

    Tries this season's projection, then last season's (preseason gap).
    Goalies use a wins/shutouts/rates proxy on a skater-like scale.
    """
    keys = [f"Projected {year}", f"Projected {year - 1}"]
    base = 0
    if is_goalie(player):
        for key in keys + [f"Last 30 {year}", f"Total {year}"]:
            base = _hockey_goalie_score(player, key)
            if base:
                break
    else:
        for key in keys + [f"Last 30 {year}", f"Total {year}"]:
            base = _hockey_total(player, key)
            if base:
                break
    if is_out(player):
        base -= INJURED_PENALTY
    return base


def hockey_display_points(player, year):
    """Single readable number for the hockey message line."""
    if is_goalie(player):
        pts = score_hockey(player, year)
        if is_out(player):
            pts += INJURED_PENALTY  # show projection, not the penalty
        return pts
    pts = _hockey_total(player, f"Projected {year}")
    if not pts:
        pts = _hockey_total(player, f"Projected {year - 1}")
    return pts



def rank_and_format(players, count, header, line):
    """Sort healthy-first by score, then format the top N lines.

    players: list of (player, score, healthy_bool) tuples.
    line: callable (rank, player, score) -> display string.
    Falls back to raw score order if everyone is injured.
    """
    healthy = [(p, s) for p, s, ok in players if ok]
    pool = healthy or [(p, s) for p, s, _ in players]
    ranked = sorted(pool, key=lambda ps: ps[1], reverse=True)[:count]
    if not ranked:
        return "No free agents available right now."
    lines = [header]
    for i, (player, score) in enumerate(ranked, start=1):
        lines.append(line(i, player, score))
    return "\n".join(lines)


def basketball_rank_and_format(agents, count):
    """Top-N basketball free agents, one numbered line each."""
    players = [(p, score_basketball(p), not is_out(p)) for p in agents]

    def line(i, p, _score):
        proj = getattr(p, "projected_avg_points", 0) or 0
        avg = getattr(p, "avg_points", 0) or 0
        return (
            f"{i}. {p.name} ({p.position}, {p.proTeam}){out_flag(p)} "
            f"- proj {proj:.1f}/game, avg {avg:.1f}/game"
        )

    return rank_and_format(
        players, count, "Top basketball free agents to pick up:", line
    )


def hockey_rank_and_format(agents, year, count):
    """Top-N hockey free agents: best skaters + best goalie + best of rest."""
    scored = [(p, score_hockey(p, year), not is_out(p)) for p in agents]
    skaters = [t for t in scored if not is_goalie(t[0])]
    goalies = [t for t in scored if is_goalie(t[0])]

    def by_score(pairs):
        return sorted(pairs, key=lambda t: t[1], reverse=True)

    healthy_skaters = by_score([t for t in skaters if t[2]])
    healthy_goalies = by_score([t for t in goalies if t[2]])
    healthy_rest = by_score([t for t in scored if t[2]])

    picks = []
    for p, s, ok in healthy_skaters[:3] + healthy_goalies[:1] + healthy_rest:
        if (p, s, ok) not in picks:
            picks.append((p, s, ok))
        if len(picks) >= count:
            break
    if not picks:  # everyone injured; fall back to raw ranking
        picks = by_score(scored)[:count]
    if not picks:
        return "No free agents available right now."

    def line(i, p, _score):
        pts = hockey_display_points(p, year)
        try:
            pts_txt = f"{float(pts):.1f}"
        except (TypeError, ValueError):
            pts_txt = "n/a"
        return (
            f"{i}. {p.name} ({p.position}, {p.proTeam}){out_flag(p)} "
            f"- proj {pts_txt} pts"
        )

    lines = ["Top hockey free agents to pick up:"]
    for i, (player, score, _ok) in enumerate(picks, start=1):
        lines.append(line(i, player, score))
    return "\n".join(lines)
