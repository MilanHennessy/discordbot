"""Mudae-style hockey card pulls from the real 2025-26 Upper Deck Series 1 set.

Basic on purpose: a small static pool, no API calls, stdlib only.

- Each card is a real card from 2025-26 UD Series 1 (base, Young Guns,
  Canvas, Portraits, Dazzlers, parallels).
- Rarity tiers mirror the real set: pack odds / serial numbers decide
  both pull weight AND value. A High Gloss #/10 is worth more than a
  base card because only 10 exist - same logic as real collecting.
- Single user, so the collection is one local JSON file (no user tracking).
- Hockey only for now; basketball can copy this file later.
"""

import json
import os
import random

COLLECTION_FILE = os.path.join(os.path.dirname(__file__), "hockey_cards.json")

# NHL player IDs for the free official headshot CDN:
# https://assets.nhle.com/mugs/nhl/20252026/{TEAM}/{ID}.png
# Single-user project, so a static table is fine. None = no photo found
# (card still pulls, the message just shows without an image).
HEADSHOTS = {
    "David Pastrnak": ("BOS", 8477956),
    "Rasmus Dahlin": ("BUF", 8480839),
    "Seth Jarvis": ("CAR", 8482073),
    "Leo Carlsson": ("ANA", 8481549),
    "Mason McTavish": ("ANA", 8481590),
    "Frank Nazar": ("CHI", 8481904),
    "Pyotr Kochetkov": ("CAR", 8481030),
    "Matt Coronato": ("CGY", 8482147),
    "Jackson Blake": ("CAR", 8482060),
    "Connor McDavid": ("EDM", 8478402),
    "Nathan MacKinnon": ("COL", 8477492),
    "Auston Matthews": ("TOR", 8479318),
    "Leon Draisaitl": ("EDM", 8477934),
    "Cale Makar": ("COL", 8480069),
    "Nikita Kucherov": ("TBL", 8476453),
    "Ivan Demidov": ("MTL", 8483455),
    "Artyom Levshunov": ("CHI", 8484187),
    "Zayne Parekh": ("CGY", 8484141),
    "Dalibor Dvorsky": ("STL", 8481596),
    "Sam Rinzel": ("CHI", 8482070),
    "Ryan Suzuki": ("CAR", 8481522),
    "Matthew Wood": ("NSH", 8481906),
    "Noah Ostlund": ("BUF", 8482111),
    "Oliver Moore": ("CHI", 8481907),
    "Colton Dach": ("CHI", 8482080),
    "Ville Koivunen": ("PIT", 8482243),
    "Cam Lund": ("SJS", 8482107),
    "Kirill Kaprizov": ("MIN", 8478864),
    "Aleksander Barkov": ("FLA", 8477493),
    "Dylan Holloway": ("STL", 8482078),
    "Connor Bedard": ("CHI", 8484144),
    "Alex Ovechkin": ("WSH", 8471214),
    "Evgeni Malkin": ("PIT", 8471215),
    "Quinn Hughes": ("VAN", 8480800),
    "Matthew Tkachuk": ("FLA", 8475176),
    "Tage Thompson": ("BUF", 8479420),
    "Wyatt Johnston": ("DAL", 8482055),
    "Brandon Hagel": ("TBL", 8479542),
    "Moritz Seider": ("DET", 8481542),
    "Josh Morrissey": ("WPG", 8477504),
    "Adam Fox": ("NYR", 8479323),
    "William Eklund": ("SJS", 8481541),
    "Dylan Cozens": ("OTT", 8481529),
    "Jared McCann": ("SEA", 8477955),
    "Anders Lee": ("NYI", 8475317),
}

# (tier label, value in "card bucks", pull weight per card)
# Weights are inspired by real pack odds, juiced slightly so rare hits
# actually happen sometimes. Higher weight = pulled more often.
TIERS = {
    "Base": (10, 70.0),
    "UD Portraits": (25, 12.0),
    "UD Canvas": (45, 4.0),
    "Young Guns": (60, 8.0),
    "Blue Dazzlers": (70, 2.5),
    "Outburst": (100, 1.5),
    "Clear Cut": (200, 0.5),
    "Deluxe #/250": (300, 0.4),
    "Exclusives #/100": (500, 0.25),
    "Outburst Red #/25": (1200, 0.1),
    "High Gloss #/10": (3000, 0.05),
    "Snow Spray Auto": (8000, 0.03),
    "Outburst Gold 1/1": (15000, 0.01),
}

# (player, team, tier). All real 2025-26 UD Series 1 cards.
CARDS = [
    # Base veterans and stars (cards 1-200)
    ("David Pastrnak", "Boston Bruins", "Base"),
    ("Rasmus Dahlin", "Buffalo Sabres", "Base"),
    ("Seth Jarvis", "Carolina Hurricanes", "Base"),
    ("Leo Carlsson", "Anaheim Ducks", "Base"),
    ("Mason McTavish", "Anaheim Ducks", "Base"),
    ("Frank Nazar", "Chicago Blackhawks", "Base"),
    ("Pyotr Kochetkov", "Carolina Hurricanes", "Base"),
    ("Matt Coronato", "Calgary Flames", "Base"),
    ("Jackson Blake", "Carolina Hurricanes", "Base"),
    ("Connor McDavid", "Edmonton Oilers", "Base"),
    ("Nathan MacKinnon", "Colorado Avalanche", "Base"),
    ("Auston Matthews", "Toronto Maple Leafs", "Base"),
    ("Leon Draisaitl", "Edmonton Oilers", "Base"),
    ("Cale Makar", "Colorado Avalanche", "Base"),
    ("Nikita Kucherov", "Tampa Bay Lightning", "Base"),
    # Young Guns rookies (the chase cards of Series 1)
    ("Ivan Demidov", "Montreal Canadiens", "Young Guns"),
    ("Artyom Levshunov", "Chicago Blackhawks", "Young Guns"),
    ("Zayne Parekh", "Calgary Flames", "Young Guns"),
    ("Dalibor Dvorsky", "St. Louis Blues", "Young Guns"),
    ("Sam Rinzel", "Chicago Blackhawks", "Young Guns"),
    ("Ryan Suzuki", "Carolina Hurricanes", "Young Guns"),
    ("Matthew Wood", "Nashville Predators", "Young Guns"),
    ("Noah Ostlund", "Buffalo Sabres", "Young Guns"),
    ("Oliver Moore", "Chicago Blackhawks", "Young Guns"),
    ("Colton Dach", "Chicago Blackhawks", "Young Guns"),
    ("Ville Koivunen", "Pittsburgh Penguins", "Young Guns"),
    ("Cam Lund", "San Jose Sharks", "Young Guns"),
    # UD Canvas veterans
    ("Kirill Kaprizov", "Minnesota Wild", "UD Canvas"),
    ("Aleksander Barkov", "Florida Panthers", "UD Canvas"),
    ("Dylan Holloway", "St. Louis Blues", "UD Canvas"),
    # UD Portraits stars (1:5 packs)
    ("Connor Bedard", "Chicago Blackhawks", "UD Portraits"),
    ("Alex Ovechkin", "Washington Capitals", "UD Portraits"),
    ("Evgeni Malkin", "Pittsburgh Penguins", "UD Portraits"),
    ("Quinn Hughes", "Vancouver Canucks", "UD Portraits"),
    ("Matthew Tkachuk", "Florida Panthers", "UD Portraits"),
    ("Tage Thompson", "Buffalo Sabres", "UD Portraits"),
    # Blue Dazzlers (1 per hobby box)
    ("Wyatt Johnston", "Dallas Stars", "Blue Dazzlers"),
    ("Brandon Hagel", "Tampa Bay Lightning", "Blue Dazzlers"),
    # Parallels and hits (serial-numbered = rare = valuable)
    ("Moritz Seider", "Detroit Red Wings", "Outburst"),
    ("Josh Morrissey", "Winnipeg Jets", "Outburst"),
    ("Adam Fox", "New York Rangers", "Clear Cut"),
    ("William Eklund", "San Jose Sharks", "Deluxe #/250"),
    ("Dylan Cozens", "Ottawa Senators", "Exclusives #/100"),
    ("Jared McCann", "Seattle Kraken", "Outburst Red #/25"),
    ("Anders Lee", "New York Islanders", "High Gloss #/10"),
    ("Ivan Demidov", "Montreal Canadiens", "Snow Spray Auto"),
    ("Connor Bedard", "Chicago Blackhawks", "Outburst Gold 1/1"),
]


def _weights():
    """One pull weight per card, from its tier. Deterministic table."""
    return [TIERS[tier][1] for _, _, tier in CARDS]


def pull_card(rng=None):
    """Pull one random card, weighted by real-set rarity.

    rng is injectable for tests; defaults to random.random.
    Returns (player, team, tier, value).
    """
    rng = rng or random.random
    weights = _weights()
    total = sum(weights)
    roll = rng() * total
    running = 0.0
    for (player, team, tier), weight in zip(CARDS, weights):
        running += weight
        if roll < running:
            return player, team, tier, TIERS[tier][0]
    player, team, tier = CARDS[-1]  # float safety net, basically unreachable
    return player, team, tier, TIERS[tier][0]


def load_collection():
    """Read the local collection file. Returns a list of card dicts."""
    try:
        with open(COLLECTION_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_pull(player, team, tier, value):
    """Append one pulled card to the collection. Returns total count."""
    collection = load_collection()
    collection.append({"player": player, "team": team,
                       "tier": tier, "value": value})
    with open(COLLECTION_FILE, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2)
    return len(collection)


def collection_value():
    """Total value of every card pulled so far."""
    return sum(card.get("value", 0) for card in load_collection())


def headshot_url(player):
    """Official NHL headshot for a player, or None if unknown.

    Free CDN, no key needed. Discord embeds the image from the URL -
    the bot never downloads or stores photos.
    """
    entry = HEADSHOTS.get(player)
    if not entry:
        return None
    team, player_id = entry
    return f"https://assets.nhle.com/mugs/nhl/20252026/{team}/{player_id}.png"


def build_pull_embed(player, team, tier, value, count):
    """Discord embed for one pull: card art on the side, stats in fields.

    Rarity gets a color: grey commons, blue mid, purple rare, gold 1/1s.
    Returns (embed_dict, image_url_or_None) - bot.py sends it.
    """
    colors = {
        "Base": 0x95A5A6, "UD Portraits": 0x3498DB, "UD Canvas": 0x3498DB,
        "Young Guns": 0x2ECC71, "Blue Dazzlers": 0x2ECC71,
        "Outburst": 0x9B59B6, "Clear Cut": 0x9B59B6,
        "Deluxe #/250": 0x9B59B6, "Exclusives #/100": 0xE67E22,
        "Outburst Red #/25": 0xE67E22, "High Gloss #/10": 0xE74C3C,
        "Snow Spray Auto": 0xF1C40F, "Outburst Gold 1/1": 0xF1C40F,
    }
    return {
        "title": f"{player} ({team})",
        "description": f"2025-26 Upper Deck Series 1 - {tier}",
        "color": colors.get(tier, 0x95A5A6),
        "fields": [
            {"name": "Value", "value": f"{value} card bucks", "inline": True},
            {"name": "Collection",
             "value": f"{count} cards, {collection_value()} total",
             "inline": True},
        ],
    }, headshot_url(player)


def format_pull(player, team, tier, value, count):
    """The Discord message for one pull. Value scales with real rarity."""
    return "\n".join([
        f"Pulled: {player} ({team})",
        f"Card: 2025-26 Upper Deck Series 1 - {tier}",
        f"Value: {value} card bucks",
        f"Collection: {count} cards, {collection_value()} total value",
    ])
