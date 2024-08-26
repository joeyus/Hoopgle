import re
from fuzzywuzzy import process

# Dictionary of NBA team names and abbreviations
nba_teams = {
    "atlanta hawks": "ATL", "boston celtics": "BOS", "brooklyn nets": "BKN", "charlotte hornets": "CHA",
    "chicago bulls": "CHI", "cleveland cavaliers": "CLE", "dallas mavericks": "DAL", "denver nuggets": "DEN",
    "detroit pistons": "DET", "golden state warriors": "GSW", "houston rockets": "HOU", "indiana pacers": "IND",
    "los angeles clippers": "LAC", "los angeles lakers": "LAL", "memphis grizzlies": "MEM", "miami heat": "MIA",
    "milwaukee bucks": "MIL", "minnesota timberwolves": "MIN", "new orleans pelicans": "NOP", "new york knicks": "NYK",
    "oklahoma city thunder": "OKC", "orlando magic": "ORL", "philadelphia 76ers": "PHI", "phoenix suns": "PHX",
    "portland trail blazers": "POR", "sacramento kings": "SAC", "san antonio spurs": "SAS", "toronto raptors": "TOR",
    "utah jazz": "UTA", "washington wizards": "WAS"
}

def preprocess_query(query):
    # Remove stopwords like "during", "in", "the"
    stopwords = ["during", "in", "the"]
    for word in stopwords:
        query = re.sub(rf'\b{word}\b', '', query)
    query = query.strip()
    return query

def correct_typos(query):
    # Correct common typos for "over" and "under"
    typo_corrections = {
        "ovr": "over",
        "ovre": "over",
        "uder": "under",
        "undr": "under",
        "undre": "under",
        "steels": "steals",
        "stls": "steals",
        "asts": "assists",
        "boards": "rebounds",
        "pts": "points",
        "reg" : "regular"
    }
    for typo, correction in typo_corrections.items():
        query = re.sub(rf'\b{typo}\b', correction, query)
    return query

def fuzzy_match_stat_cat(query, stat_cats):
    matched_stats = []
    remaining_query = query

    # Handle multi-word phrases first
    for stat in stat_cats:
        if stat in remaining_query:
            matched_stats.append(stat)
            remaining_query = remaining_query.replace(stat, '').strip()

    # Handle single words by fuzzy matching
    words = remaining_query.split()
    for word in words:
        if len(word) > 2:  # Exclude very short words from fuzzy matching
            match, score = process.extractOne(word, stat_cats)
            if score > 85 and match not in matched_stats:  # Increase threshold and avoid duplicates
                matched_stats.append(match)
                remaining_query = remaining_query.replace(word, '').strip()

    # Combine all matched stat categories into one string
    stat_cat = ' '.join(matched_stats) if matched_stats else None

    return stat_cat, remaining_query

def identify_query_components(query):
    query = preprocess_query(query)
    query = correct_typos(query)

    # Initialize components
    year = season = over_under = stat_cat = line = name = team = opponent_player = None

    # Define patterns
    year_pattern = r"\b(19|20)\d{2}\b"
    season_pattern = r"\b(playoffs?|regular season|season|regular|post|post season)\b"
    over_under_pattern = r"\b(over|under)\b"
    line_pattern = r"\b\d+(\.\d+)?\b"
    team_pattern = r"\bvs\b\s+([A-Za-z\s]+)"

    stat_cat_list = [
        "points", "rebounds", "assists", "blocks", "steals",
        "triple double", "free throw", "double double",
        "points assists", "points rebounds", "points rebounds assists",
        "assists rebounds", "three pointer"
    ]

    # Extract components
    year_match = re.search(year_pattern, query)
    if year_match:
        year = year_match.group(0)
        query = re.sub(year_pattern, '', query, 1)  # Remove year from query

    season_match = re.search(season_pattern, query)
    if season_match:
        season = season_match.group(0)
        query = re.sub(season_pattern, '', query, 1)  # Remove season from query

    over_under_match = re.search(over_under_pattern, query)
    if over_under_match:
        over_under = over_under_match.group(0)
        query = re.sub(over_under_pattern, '', query, 1)  # Remove over/under from query

    line_match = re.search(line_pattern, query)
    if line_match:
        line = line_match.group(0)
        query = re.sub(line_pattern, '', query, 1)  # Remove line from query

    team_match = re.search(team_pattern, query)
    if team_match:
        possible_team = team_match.group(1).strip().lower()
        if possible_team in nba_teams:
            team = possible_team
            query = re.sub(team_pattern, '', query, 1)  # Remove team from query
        else:
            opponent_player = possible_team
            query = re.sub(team_pattern, '', query, 1)  # Remove opponent player from query

    stat_cat, query = fuzzy_match_stat_cat(query, stat_cat_list)
    
    # The remaining query is considered the player's name
    name = query.strip()

    # Ensure no extra words are left in the player's name
    name = ' '.join([word for word in name.split() if word.lower() not in stat_cat_list and word.lower() not in ["double", "triple"]])

    return year, season, over_under, stat_cat, line, name, team, opponent_player

# Example usage
queries = [
    "zach edey asts over 3 points vs lebron james in the regular season 2025",
    "zach edey asts over 3 points vs boston celtics in the regular season 2025",
]

for query in queries:
    year, season, over_under, stat_cat, line, name, team, opponent_player = identify_query_components(query)
    print(f"Year: {year}, Season: {season}, Over/Under: {over_under}, Stat Cat: {stat_cat}, Line: {line}, Name: {name}, Team: {team}, Opponent Player: {opponent_player}")
