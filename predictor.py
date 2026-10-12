"""Match win predictor using multinomial-style logistic regression.

Basic on purpose: a tiny self-contained softmax model, no sklearn needed.

How it works (plain English):
- Each team is summarized by 3 simple features:
    1. live_score  - points scored so far this week (moves as games finish)
    2. pace        - points per starter who has already played (are hot players hot?)
    3. record     - season win fraction (are you generally the better team?)
- A small weight table turns those features into one number ("logit") per team.
- Softmax turns the two logits into win chances that always add to 100%.
- Early in the week very few starters have played, so record matters most.
  Late in the week, live_score dominates and the chance moves with real results.
"""

import math

# Hand-picked weights: [live_score, pace, record]. Kept small and readable.
# These are NOT learned from data - just sensible defaults. Tweak freely.
WEIGHTS = [0.06, 1.5, 2.0]
BIAS = 0.0


def team_features(live_score, starters_played, starter_count, wins, losses, ties=0):
    """Turn raw numbers into the 3 model inputs. All plain floats."""
    live_score = float(live_score or 0)
    starters_played = max(int(starters_played or 0), 0)
    starter_count = max(int(starter_count or 0), 1)  # avoid divide-by-zero
    # Nobody has played yet -> pace is 0 so the season record decides.
    pace = live_score / starters_played if starters_played else 0.0
    games = (wins or 0) + (losses or 0) + (ties or 0)
    record = ((wins or 0) + 0.5 * (ties or 0)) / games if games else 0.5
    return [live_score, pace, record]


def logit(features):
    """One number per team: higher means more likely to win."""
    return BIAS + sum(w * f for w, f in zip(WEIGHTS, features))


def softmax(logit_a, logit_b):
    """Turn two logits into two chances that add to 1.0 (numerically safe)."""
    top = max(logit_a, logit_b)
    exp_a = math.exp(logit_a - top)
    exp_b = math.exp(logit_b - top)
    total = exp_a + exp_b
    return exp_a / total, exp_b / total


def win_chance(us_feats, them_feats):
    """Return our win chance as a 0-100 float. Basic binary case of softmax."""
    chance_us, _ = softmax(logit(us_feats), logit(them_feats))
    return round(chance_us * 100, 1)


def chance_line(chance):
    """The exact Discord line the bot prints."""
    return f"You have a {chance:.1f}% chance of winning."


def played_count(lineup):
    """How many starters have a finished game (game_played is 0-100)."""
    return sum(1 for p in (lineup or []) if getattr(p, "game_played", 0) == 100)


def summarize_matchup(us_lineup, them_lineup, us_score, them_score,
                       us_record, them_record):
    """Build both teams' features and return (chance, line).

    us_record / them_record are (wins, losses, ties) tuples.
    """
    us_feats = team_features(us_score, played_count(us_lineup),
                             len(us_lineup or []), *us_record)
    them_feats = team_features(them_score, played_count(them_lineup),
                               len(them_lineup or []), *them_record)
    chance = win_chance(us_feats, them_feats)
    return chance, chance_line(chance)
