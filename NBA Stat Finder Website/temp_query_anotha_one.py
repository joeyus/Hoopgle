import re
from fuzzywuzzy import process

def preprocess_query(query):
    # Remove stopwords like "during", "in", "the"
    stopwords = ["during", "in", "the"]
    for word in stopwords:
        query = re.sub(rf'\b{word}\b', '', query)
    query = query.strip()
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
        match, score = process.extractOne(word, stat_cats)
        if score > 80 and match not in matched_stats:  # Adjust threshold as needed and avoid duplicates
            matched_stats.append(match)
            remaining_query = remaining_query.replace(word, '').strip()

    # Combine all matched stat categories into one string
    stat_cat = ' '.join(matched_stats) if matched_stats else None

    return stat_cat, remaining_query

def identify_query_components(query):
    query = preprocess_query(query)

    # Initialize components
    year = season = over_under = stat_cat = line = name = None

    # Define patterns
    year_pattern = r"\b(19|20)\d{2}\b"
    season_pattern = r"\b(playoffs?|regular season|season)\b"
    over_under_pattern = r"\b(over|under)\b"
    line_pattern = r"\b\d+(\.\d+)?\b"

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

    stat_cat, query = fuzzy_match_stat_cat(query, stat_cat_list)
    
    # The remaining query is considered the player's name
    name = query.strip()

    # Ensure no extra words are left in the player's name
    name = ' '.join([word for word in name.split() if word.lower() not in stat_cat_list and word.lower() not in ["double", "triple"]])

    return year, season, over_under, stat_cat, line, name

# Example usage
queries = [
    "points over 10 lebron james playoffs 2024",
    "deaaron fox double triple regular season 2024",
    "al horford triple double playoffs 2010",
    "jayson tatum under 10 rebounds regular season 2023"
]

for query in queries:
    year, season, over_under, stat_cat, line, name = identify_query_components(query)
    print(f"Year: {year}, Season: {season}, Over/Under: {over_under}, Stat Cat: {stat_cat}, Line: {line}, Name: {name}")
