from flask import Flask, request, render_template, session, redirect, url_for
import pandas as pd
from fuzzywuzzy import fuzz, process
import requests

import re
from fuzzywuzzy import process


app = Flask(__name__)
app.secret_key = 'your_secret_key'


@app.route('/')
def home():
    
    return render_template('site.html')

@app.route('/stat_search', methods=['POST'])
def stat_search1():
    query = request.form['query']
    tokens = query.split()
    game_logs_html = None
    url_path = "_".join(tokens)
    

    year, season, over_under, stat_cat, line, name = identify_query_components(query)
    last_name = name.split()[-1]
    print(f"Year: {year}, Season: {season}, Over/Under: {over_under}, Stat Cat: {stat_cat}, Line: {line}, Name: {name}")

    split = regularOrPlayoffs(season)
    cat_index, closest_ou_key, propt_num, closest_stat_key = getVariables(stat_cat, over_under, line)




    if split == "regular":
        player_url = regularURL(year, name, last_name)
        result_message, game_logs_html, last5_result, last5_df, last10_result, last10_df, last15_result, last15_df = tableScrape(player_url, cat_index, closest_ou_key, propt_num, name, closest_stat_key, year)
        
        return render_template(
        'result.html',
        path=url_path,
        result_message=result_message,
        game_logs_html=game_logs_html,
        last5_result=last5_result,
        last5_df=last5_df,
        last10_result=last10_result,
        last10_df=last10_df,
        last15_result=last15_result,
        last15_df=last15_df)
    else:
        player_url = playoffURL(name, last_name)
        result_message,total_game_logs_html, first_game_log, second_game_log, third_game_log, fourth_game_log = playoffTableScrape(player_url, cat_index, closest_ou_key, propt_num, name, closest_stat_key)

        rendered_logs = {
        'total_game_logs_html' : total_game_logs_html if total_game_logs_html else None,
        'first_game_log': first_game_log if first_game_log else None,
        'second_game_log': second_game_log if second_game_log else None,
        'third_game_log': third_game_log if third_game_log else None,
        'fourth_game_log': fourth_game_log if fourth_game_log else None,
        }
        
        return render_template(
        'result.html',
        path=url_path,
        result_message=result_message,
        game_logs_html=game_logs_html,
        **rendered_logs
        )


    # Directly render the template with the results
    return render_template('result.html', path=url_path, result_message=result_message, game_logs_html=game_logs_html)

def playoffURL(name, last_name):
    url = f"https://www.basketball-reference.com/players/{last_name[0]}/"
    response_p = requests.get(url)
    tables = pd.read_html(response_p.content)[0]
    file_path = f"{last_name[0]}_players.txt"
    tables.to_csv(file_path, sep='\t', index=False)
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    playoff_player_names = set()
    for line in lines:
        line = line.strip()
        player_nme = line.split()
        full_name = player_nme[0] + " " + player_nme[1]
        playoff_player_names.add(full_name)

    closest_playoff_name, _ = process.extractOne(name, playoff_player_names, scorer=fuzz.token_sort_ratio)
    playoff_first_name, playoff_last_name = closest_playoff_name.split()
    playoff_url_playername = playoff_last_name[:5] + playoff_first_name[:2] + "01"
    career_playoff_url = f"https://www.basketball-reference.com/players/{last_name[0]}/{playoff_url_playername}/gamelog-playoffs"

    return career_playoff_url

def regularOrPlayoffs(season):
    playoff_dict = {"regular", "Postseason", "Playoffs"}
    closest_split, _ = process.extractOne(season, playoff_dict, scorer=fuzz.token_sort_ratio)
    return closest_split

def regularURL(year, name, last_name):
    url = f"https://www.basketball-reference.com/leagues/NBA_{year}_per_minute.html"
    response = requests.get(url)
    tables = pd.read_html(response.content)[0]
    file_path = f'{year}_players.txt'
    tables.to_csv(file_path, sep='\t', index=False)
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    player_names = set()
    for line in lines:
        line = line.strip()
        player_nme = line.split()
        full_name = player_nme[1] + " " + player_nme[2]
        player_names.add(full_name)

    closest_name, _ = process.extractOne(name, player_names, scorer=fuzz.token_sort_ratio)
    firstname, lastname = closest_name.split()
    url_playername = lastname[:5] + firstname[:2] + "01"
    player_link = f"https://www.basketball-reference.com/players/w/{url_playername}/gamelog/{year}"
    return player_link

def tableScrape(player_url, cat_index, closest_ou_key, propt_num, name, closest_stat_key, year):
    response = requests.get(player_url)
    tables = pd.read_html(response.content)[7]
    pd.set_option('display.max_rows', None)

    # Convert the DataFrame to a list of lists
    data_arrays = tables.values.tolist()

    # Use the original column headers from the DataFrame
    columns = tables.columns.tolist()

    # Include the first row (which contains the headers in your original setup) as data
    data = data_arrays  # No need to exclude the first row


    # Create a new DataFrame with the column headers and all data including the first row
    df = pd.DataFrame(data, columns=columns)

    # Initialize an empty list to store the rows that match the condition
    rows_list = []

    # Iterate over each row of the DataFrame
    for index, row in df.iterrows():
        try:
            if closest_ou_key == "over":
                if isinstance(cat_index, int) and int(row[cat_index]) > propt_num:
                    rows_list.append(row)
                elif isinstance(cat_index, list) and len(cat_index) == 2:
                    temp1 = row[cat_index[0]]
                    temp2 = row[cat_index[1]]
                    if int(temp1) + int(temp2) > propt_num:
                        rows_list.append(row)
            else:
                if isinstance(cat_index, int) and int(row[cat_index]) < propt_num:
                    rows_list.append(row)
                elif isinstance(cat_index, list) and len(cat_index) == 2:
                    temp1 = row[cat_index[0]]
                    temp2 = row[cat_index[1]]
                    if int(temp1) + int(temp2) < propt_num:
                        rows_list.append(row)
        except ValueError:
            continue

    # Convert the list of Series (rows) to a DataFrame
    temp_df = pd.DataFrame(rows_list, columns=df.columns)

    # Calculate inactive games
    inactive_games = df['G'].apply(lambda x: len(str(x)) > 2).sum()

    # Calculate active games
    active_games = len(df) - (len(df) // 20) - inactive_games

    # Calculate the percentage
    percentage = (len(temp_df) / active_games) * 100
    format_percentage = "{:.2f}".format(percentage)

    # Display the final result
    result_message = f"{name} has covered the {closest_ou_key} {propt_num} {closest_stat_key} line in {year} in {len(temp_df)}/{active_games} ({format_percentage}%) games."

    game_logs_html = temp_df.to_html(classes='game-logs-table', index=False)

    #testing of last 5 percentages
    last5_result, last5_df =last5_percentage(df, closest_ou_key, closest_stat_key, propt_num, cat_index, name)
 
    last10_result, last10_df =last10_percentage(df, closest_ou_key, closest_stat_key, propt_num, cat_index, name)

    last15_result, last15_df =last15_percentage(df, closest_ou_key, closest_stat_key, propt_num, cat_index, name )


    # Return the result message and temp_df for further processing if needed
    return result_message, game_logs_html, last5_result, last5_df, last10_result, last10_df, last15_result, last15_df

def getVariables(stat_cat, over_under, line):
    stat_dict = {
        "points": -3, "buckets": -3, "rebounds": -9, "boards": -9,
        "assists": -8, "dimes": -8, "PR": [-3, -9], "points rebounds": [-3, -9],
        "PA": [-3, -8], "points assists": [-3, -8], "pra": [-3, -9, -8], "points rebounds assists": [-3, -9, -8],
        "triple double": 0, "double double": 0, "blocks": -6, "steals": -7, "AR": [-9, -8], "assists rebounds": [-9, -8]
    }
    closest_stat = process.extractOne(stat_cat, stat_dict.keys(), scorer=fuzz.token_sort_ratio)
    closest_stat_key = closest_stat[0]
    cat_index = stat_dict.get(closest_stat_key)

    over_under_dict = {"over", "under"}
    closest_ou = process.extractOne(over_under, over_under_dict, scorer=fuzz.token_sort_ratio)
    closest_ou_key = closest_ou[0]

    propt_num = int(line)
    return cat_index, closest_ou_key, propt_num, closest_stat_key

def playoffTableScrape(player_url, cat_index, closest_ou_key, propt_num, name, closest_stat_key):
    #ignore the year for now, can come back to fix 
    """
    TO DO LIST 
    - make the finder work for non single like triple double, double double, three point, free throw right now it only works for 1 word stats like points
        -needs a new system in the search query(NLP)
    - Fix the year (add the last year latest stats implement it from main)
    """
    #column finder 
    stat_dict = {
        "points": -3, "buckets": -3, "rebounds": -9, "boards": -9,
        "assists": -8, "dimes": -8, "PR": [-3, -9], "points rebounds": [-3, -9],
        "PA": [-3, -8], "points assists": [-3, -8], "pra": [-3, -9, -8], "points rebounds assists": [-3, -9, -8],
        "triple double": 0, "double double": 0, "blocks": -6, "steals": -7, "AR": [-9, -8], "assists rebounds": [-9, -8]
    }
    stat_key_finder = {"points": "PTS", "rebounds": "TRB", "blocks": "BLK", "steal" : "STL", "assists": "assists", "Freethrow" : "FT", "three pointer" : "3P"}
    stat_key = stat_key_finder.get(closest_stat_key)

    response_p = requests.get(player_url)
    tables = pd.read_html(response_p.content)[7]
    pd.set_option('display.max_rows', None)
    # Convert the DataFrame to a list of lists
    data_arrays = tables.values.tolist()
    # Use the original column headers from the DataFrame
    columns = tables.columns.tolist()

    # Include the first row (which contains the headers in your original setup) as data
    data = data_arrays  # No need to exclude the first row

    # Create a new DataFrame with the column headers and all data including the first row
    df = pd.DataFrame(data, columns=columns)

    # Initialize an empty list to store the rows that match the condition
    rows_list = []

    pd.set_option('display.max_rows', None)
    #The issue is, lebron point column is -3 to rudy gobert whereas is -4,  I need to fix this issue

    """
    Change the way the stat_cat is found with df['PTS].iloc[3]
    change this for both table scrape and playoff table scrape
    (DO ASAP)
    """
  # Iterate over each row of the DataFrame
    for index, row in df.iterrows():
        try:
            if closest_ou_key == "over":
                if isinstance(cat_index, int) and int(row[stat_key]) > propt_num:
                    rows_list.append(row)
                elif isinstance(cat_index, list) and len(cat_index) == 2:
                    temp1 = row[cat_index[0]]
                    temp2 = row[cat_index[1]]
                    if int(temp1) + int(temp2) > propt_num:
                        rows_list.append(row)
            else:
                if isinstance(cat_index, int) and int(row[stat_key]) < propt_num:
                    rows_list.append(row)
                elif isinstance(cat_index, list) and len(cat_index) == 2:
                    temp1 = row[cat_index[0]]
                    temp2 = row[cat_index[1]]
                    if int(temp1) + int(temp2) < propt_num:
                        rows_list.append(row)
        except ValueError:
            continue

    # Convert the list of Series (rows) to a DataFrame
    temp_df = pd.DataFrame(rows_list, columns=df.columns)

    # Calculate inactive games
    inactive_games = df['G'].apply(lambda x: len(str(x)) > 2).sum()

    # Calculate active games
    active_games = len(df) - (len(df) // 20) - inactive_games

    # Calculate the percentage
    percentage = (len(temp_df) / active_games) * 100
    format_percentage = "{:.2f}".format(percentage)

    # Display the final result
    result_message = f"{name} has covered the {closest_ou_key} {propt_num} {closest_stat_key} line in {len(temp_df)}/{active_games} ({format_percentage}%) playoff games."


    total_game_logs_html = temp_df.to_html(classes='game-logs-table', index=False)

    end_index, first_game_log= latest_percentage(df, closest_ou_key, closest_stat_key, cat_index, propt_num, name)

    if data_arrays[end_index -1][7].isdigit() or data_arrays[end_index -1][6].isdigit():
        end_index, second_game_log =second_latest_percentage(df, closest_ou_key,closest_stat_key, cat_index, propt_num, name, end_index)
    else:
        return end_index, total_game_logs_html,first_game_log


    if data_arrays[end_index -1][7].isdigit() or data_arrays[end_index -1][6].isdigit():
        end_index, third_game_log =third_latest_percentage(df, closest_ou_key,closest_stat_key, cat_index, propt_num, name, end_index)
    else:
        return end_index,total_game_logs_html, first_game_log, second_game_log

    if data_arrays[end_index -1][7].isdigit() or data_arrays[end_index -1][6].isdigit():
        end_index, fourth_game_log =fourth_latest_percentage(df, closest_ou_key,closest_stat_key, cat_index, propt_num, name, end_index)
    else:
        return end_index,total_game_logs_html, first_game_log, second_game_log, third_game_log


    # Return the result message and temp_df for further processing if needed
    return result_message, total_game_logs_html, first_game_log, second_game_log, third_game_log, fourth_game_log

#Query processing 
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
        if score > 80:  # Adjust threshold as needed
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
    season_pattern = r"\b(playoff|regular season|season|regular|postseason|post season)\b"
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

    return year, season, over_under, stat_cat, line, name


#Regular season functions
def last5_percentage(data_arrays, closest_ou_key, closest_stat_key, propt_num, cat_index, name):
    last5_array = []
    stat_key_finder = {"points": "PTS", "rebounds": "TRB", "blocks": "BLK", "steal" : "STL", "assists": "assists", "Freethrow" : "FT", "three pointer" : "3P"}
    stat_key = stat_key_finder.get(closest_stat_key)


    i = len(data_arrays) - 1 
    end_index = len(data_arrays) - 6 # Ensure we don't go out of bounds

    while i> end_index: 
        if str(data_arrays.loc[i, 'PTS']) == 'Inactive' or str(data_arrays.loc[i, 'PTS']) == 'PTS':
            end_index -=1
        else:
            if closest_ou_key == "over":
                if isinstance(cat_index, int):
                    if int(data_arrays.loc[i, stat_key])>propt_num:
                        last5_array.append(data_arrays.iloc[i].tolist())
                elif isinstance(cat_index, list) and len(cat_index) ==2:
                    temp1 =(data_arrays[i][cat_index[0]]) 
                    temp2 =(data_arrays[i][cat_index[1]])
                    if int(temp1)+int(temp2)>propt_num:
                        last5_array.add(tuple(data_arrays[i]))
            else:
                if isinstance(cat_index, int):
                    if (int(data_arrays.loc[i, stat_key])<propt_num) == True:
                        last5_array.append(data_arrays.iloc[i].tolist())
                elif isinstance(cat_index, list) and len(cat_index)==2:
                    temp1 =(data_arrays[i][cat_index[0]]) 
                    temp2 =(data_arrays[i][cat_index[1]])
                    if (int(temp1)+int(temp2)<propt_num) == True:
                        last5_array.add(tuple(data_arrays[i]))

        i-=1
    temp_df = pd.DataFrame(last5_array, columns=data_arrays.columns)

    percentage = (len(last5_array)/5) *100
    formatted_percentage = "{:.0f}".format(percentage)

    result_string = (f"{name} game logs where he has covered {closest_ou_key} {propt_num} {closest_stat_key}. {len(last5_array)}/5 ({formatted_percentage}%)")

    game_logs_html = temp_df.to_html(classes='game-logs-table', index=False)

    return result_string, game_logs_html



def last10_percentage(data_arrays, closest_ou_key, closest_stat_key, propt_num, cat_index,name):
    last10_array = []
    stat_key_finder = {"points": "PTS", "rebounds": "TRB", "blocks": "BLK", "steal" : "STL", "assists": "assists", "Freethrow" : "FT", "three pointer" : "3P"}
    stat_key = stat_key_finder.get(closest_stat_key)

    i = len(data_arrays) - 1
    end_index = len(data_arrays) - 11 # Ensure we don't go out of bounds

    while i> end_index: 
        if str(data_arrays.loc[i, 'PTS']) == 'Inactive' or str(data_arrays.loc[i, 'PTS']) == 'PTS' or str(data_arrays.loc[i, 'PTS']) == 'Did Not Dress':
            end_index -=1
        else:
            if closest_ou_key == "over":
                if isinstance(cat_index, int):
                    if int(data_arrays.loc[i, stat_key])>propt_num:
                        last10_array.append(data_arrays.iloc[i].tolist())
                elif isinstance(cat_index, list) and len(cat_index) ==2:
                    temp1 =(data_arrays[i][cat_index[0]]) 
                    temp2 =(data_arrays[i][cat_index[1]])
                    if int(temp1)+int(temp2)>propt_num:
                        last10_array.add(tuple(data_arrays[i]))
            else:
                if isinstance(cat_index, int):
                    if (int(data_arrays.loc[i, stat_key])<propt_num) == True:
                        last10_array.append(data_arrays.iloc[i].tolist())
                elif isinstance(cat_index, list) and len(cat_index)==2:
                    temp1 =(data_arrays[i][cat_index[0]]) 
                    temp2 =(data_arrays[i][cat_index[1]])
                    if (int(temp1)+int(temp2)<propt_num) == True:
                        last10_array.add(tuple(data_arrays[i]))

        i-=1
    temp_df = pd.DataFrame(last10_array, columns=data_arrays.columns)

    percentage = (len(last10_array)/10) *100
    formatted_percentage = "{:.0f}".format(percentage)

    result_string = (f"{name} game logs where he has covered {closest_ou_key} {propt_num} {closest_stat_key}. {len(last10_array)}/10 ({formatted_percentage}%)")



    game_logs_html = temp_df.to_html(classes='game-logs-table', index=False)
        

    return result_string, game_logs_html

def last15_percentage(data_arrays, closest_ou_key, closest_stat_key, propt_num, cat_index, name):
    last15_array = []
    stat_key_finder = {"points": "PTS", "rebounds": "TRB", "blocks": "BLK", "steal" : "STL", "assists": "assists", "Freethrow" : "FT", "three pointer" : "3P"}
    stat_key = stat_key_finder.get(closest_stat_key)

    i = len(data_arrays) - 1
    end_index = len(data_arrays) - 16 # Ensure we don't go out of bounds

    while i> end_index: 
        if str(data_arrays.loc[i, 'PTS']) == 'Inactive' or str(data_arrays.loc[i, 'PTS']) == 'PTS' or str(data_arrays.loc[i, 'PTS']) == 'Did Not Dress':
            end_index -=1
        else:
            if closest_ou_key == "over":
                if isinstance(cat_index, int):
                    if int(data_arrays.loc[i, stat_key])>propt_num:
                        last15_array.append(data_arrays.iloc[i].tolist())
                elif isinstance(cat_index, list) and len(cat_index) ==2:
                    temp1 =(data_arrays[i][cat_index[0]]) 
                    temp2 =(data_arrays[i][cat_index[1]])
                    if int(temp1)+int(temp2)>propt_num:
                        last15_array.add(tuple(data_arrays[i]))
            else:
                if isinstance(cat_index, int):
                    if (int(data_arrays.loc[i, stat_key])<propt_num) == True:
                        last15_array.append(data_arrays.iloc[i].tolist())
                elif isinstance(cat_index, list) and len(cat_index)==2:
                    temp1 =(data_arrays[i][cat_index[0]]) 
                    temp2 =(data_arrays[i][cat_index[1]])
                    if (int(temp1)+int(temp2)<propt_num) == True:
                        last15_array.add(tuple(data_arrays[i]))

        i-=1
    temp_df = pd.DataFrame(last15_array, columns=data_arrays.columns)

    percentage = (len(last15_array)/15) *100
    formatted_percentage = "{:.0f}".format(percentage)

    result_string = (f"{name} game logs where he has covered {closest_ou_key} {propt_num} {closest_stat_key}. {len(last15_array)}/15 ({formatted_percentage}%)")


    game_logs_html = temp_df.to_html(classes='game-logs-table', index=False)

    return result_string, game_logs_html


#Playoff functions 
def latest_percentage(data_arrays, closest_ou_key, closest_stat_key, cat_index, propt_num, closest_playoff_name):
    latest_array = []
    stat_key_finder = {"points": "PTS", "rebounds": "TRB", "blocks": "BLK", "steal" : "STL", "assists": "assists", "Freethrow" : "FT", "three pointer" : "3P"}
    stat_key = stat_key_finder.get(closest_stat_key)

    latest_series = int(data_arrays.iloc[-1]["G#"])

    end_index = len(data_arrays) - latest_series
    i = len(data_arrays) - 1

    while i>=end_index: 
        if len(data_arrays.iloc[i, 1]) > 2:
            end_index -=1
        else:
            if closest_ou_key == "over":
                if isinstance(cat_index, int):
                    if int(data_arrays.iloc[i, cat_index])>propt_num:
                        latest_array.append(data_arrays.iloc[i].tolist())
                elif isinstance(cat_index, list) and len(cat_index) ==2:
                    temp1 =(data_arrays[i][cat_index[0]]) 
                    temp2 =(data_arrays[i][cat_index[1]])
                    if int(temp1)+int(temp2)>propt_num:
                        latest_array.add(tuple(data_arrays[i]))
            else:
                if isinstance(cat_index, int):
                    if (int(data_arrays.iloc[i , cat_index])<propt_num) == True:
                        latest_array.append(data_arrays.iloc[i].tolist())

                elif isinstance(cat_index, list) and len(cat_index)==2:
                    temp1 =(data_arrays[i][cat_index[0]]) 
                    temp2 =(data_arrays[i][cat_index[1]])
                    if (int(temp1)+int(temp2)<propt_num) == True:
                        latest_array.add(tuple(data_arrays[i]))

        i-=1

    if data_arrays.iloc[end_index, 5] == "@":
        opp_team = data_arrays.iloc[end_index, 6]
    else:
        opp_team = data_arrays.iloc[end_index, 5]
    print("\n")
    print(f"Latest Playoff Series vs {opp_team}")
    percentage = (len(latest_array) / latest_series) * 100
    formatted_percentage = "{:.0f}".format(percentage)
    print(f"{closest_playoff_name} game logs where he has covered {closest_ou_key} {propt_num} {closest_stat_key}. {len(latest_array)}/{latest_series}({formatted_percentage}%)")
    #Should print the games where is was not covered 
    #luka doesnt work pj washington doesnt work name issue
    #dereck lively doenst work line 162 division by zero
    end_index = end_index-1
    
    temp_df = pd.DataFrame(latest_array, columns=data_arrays.columns)
    game_logs_html = temp_df.to_html(classes='game-logs-table', index=False)
    print(temp_df)
    print("printing end_index:")
    print(end_index)

    return end_index, game_logs_html

def second_latest_percentage(data_arrays, closest_ou_key,closest_stat_key, cat_index, propt_num, closest_playoff_name, end_index):
    latest_array = []
   
    latest_series = int(data_arrays.iloc[end_index-1]["G#"])
    
    i = end_index-1
    end_index =end_index - latest_series
    while i>=end_index: 
        if len(data_arrays.iloc[i, 1]) > 2:
            end_index -=1
        else:
            if closest_ou_key == "over":
                if isinstance(cat_index, int):
                    if int(data_arrays.iloc[i, cat_index])>propt_num:
                        latest_array.append(data_arrays.iloc[i].tolist())
                elif isinstance(cat_index, list) and len(cat_index) ==2:
                    temp1 =(data_arrays[i][cat_index[0]]) 
                    temp2 =(data_arrays[i][cat_index[1]])
                    if int(temp1)+int(temp2)>propt_num:
                        latest_array.add(tuple(data_arrays[i]))
            else:
                if isinstance(cat_index, int):
                    if (int(data_arrays.iloc[i, cat_index])<propt_num) == True:
                        latest_array.append(data_arrays.iloc[i].tolist())
                elif isinstance(cat_index, list) and len(cat_index)==2:
                    temp1 =(data_arrays[i][cat_index[0]]) 
                    temp2 =(data_arrays[i][cat_index[1]])
                    if (int(temp1)+int(temp2)<propt_num) == True:
                        latest_array.add(tuple(data_arrays[i]))

        i-=1
    if data_arrays.iloc[end_index, 5]== "@":
        opp_team = data_arrays.iloc[end_index, 6]
    else:
        opp_team = data_arrays.iloc[end_index, 5]
    print("\n")
    print(f"Latest Playoff Series vs {opp_team}")
    percentage = (len(latest_array) / latest_series) * 100
    formatted_percentage = "{:.0f}".format(percentage)
    print(f"{closest_playoff_name} game logs where he has covered {closest_ou_key} {propt_num} {closest_stat_key}. {len(latest_array)}/{latest_series}({formatted_percentage}%)")
    temp_df = pd.DataFrame(latest_array, columns=data_arrays.columns)
    game_logs_html = temp_df.to_html(classes='game-logs-table', index=False)
    print(temp_df)
    end_index = end_index-1
    print("printing end_index:")
    print(end_index)
    return end_index, game_logs_html

def third_latest_percentage(data_arrays, closest_ou_key, closest_stat_key, cat_index, propt_num, closest_playoff_name, end_index):
    latest_array = []
    
    latest_series = int(data_arrays.iloc[end_index-1]["G#"])
    
    i = end_index-1
    end_index =end_index - latest_series
    while i>=end_index: 
        if len(data_arrays.iloc[i, 1]) > 2:
            end_index -=1
        else:
            if closest_ou_key == "over":
                if isinstance(cat_index, int):
                    if int(data_arrays.iloc[i, cat_index])>propt_num:
                        latest_array.append(data_arrays.iloc[i].tolist())
                elif isinstance(cat_index, list) and len(cat_index) ==2:
                    temp1 =(data_arrays[i][cat_index[0]]) 
                    temp2 =(data_arrays[i][cat_index[1]])
                    if int(temp1)+int(temp2)>propt_num:
                        latest_array.add(tuple(data_arrays[i]))
            else:
                if isinstance(cat_index, int):
                    if (int(data_arrays.iloc[i, cat_index])<propt_num) == True:
                        latest_array.append(data_arrays.iloc[i].tolist())
                elif isinstance(cat_index, list) and len(cat_index)==2:
                    temp1 =(data_arrays[i][cat_index[0]]) 
                    temp2 =(data_arrays[i][cat_index[1]])
                    if (int(temp1)+int(temp2)<propt_num) == True:
                        latest_array.add(tuple(data_arrays[i]))

        i-=1
    if data_arrays.iloc[end_index, 5] == "@":
        opp_team = data_arrays.iloc[end_index, 6]
    else:
        opp_team = data_arrays.iloc[end_index, 5]
    print("\n")
    print(f"Latest Playoff Series vs {opp_team}")
    percentage = (len(latest_array) / latest_series) * 100
    formatted_percentage = "{:.0f}".format(percentage)
    print(f"{closest_playoff_name} game logs where he has covered {closest_ou_key} {propt_num} {closest_stat_key}. {len(latest_array)}/{latest_series}({formatted_percentage}%)")
    temp_df = pd.DataFrame(latest_array, columns=data_arrays.columns)
    game_logs_html = temp_df.to_html(classes='game-logs-table', index=False)
    print(temp_df)
    end_index= end_index-1
    print("printing end_index:")
    print(end_index)
    return end_index, game_logs_html

def fourth_latest_percentage(data_arrays, closest_ou_key, closest_stat_key,cat_index, propt_num, closest_playoff_name, end_index):
        latest_array = []
        
        latest_series = int(data_arrays.iloc[end_index-1]["G#"])
        
        i = end_index-1
        end_index =end_index - latest_series
        while i>=end_index: 
            if len(data_arrays.iloc[i, 1]) > 2:
                end_index -=1
            else:
                if closest_ou_key == "over":
                    if isinstance(cat_index, int):
                        if int(data_arrays.iloc[i, cat_index])>propt_num:
                            latest_array.append(data_arrays.iloc[i].tolist())
                    elif isinstance(cat_index, list) and len(cat_index) ==2:
                        temp1 =(data_arrays[i][cat_index[0]]) 
                        temp2 =(data_arrays[i][cat_index[1]])
                        if int(temp1)+int(temp2)>propt_num:
                            latest_array.add(tuple(data_arrays[i]))
                else:
                    if isinstance(cat_index, int):
                        if (int(data_arrays.iloc[i, cat_index])<propt_num) == True:
                            latest_array.append(data_arrays.iloc[i].tolist())

                    elif isinstance(cat_index, list) and len(cat_index)==2:
                        temp1 =(data_arrays[i][cat_index[0]]) 
                        temp2 =(data_arrays[i][cat_index[1]])
                        if (int(temp1)+int(temp2)<propt_num) == True:
                            latest_array.add(tuple(data_arrays[i]))
    
            i-=1
        if data_arrays.iloc[end_index, 5] == "@":
            opp_team = data_arrays.iloc[end_index, 6]
        else:
            opp_team = data_arrays.iloc[end_index, 5]
        print("\n")
        print(f"Latest Playoff Series vs {opp_team}")
        percentage = (len(latest_array) / latest_series) * 100
        formatted_percentage = "{:.0f}".format(percentage)
        print(f"{closest_playoff_name} game logs where he has covered {closest_ou_key} {propt_num} {closest_stat_key}. {len(latest_array)}/{latest_series}({formatted_percentage}%)")
        temp_df = pd.DataFrame(latest_array, columns=data_arrays.columns)
        game_logs_html = temp_df.to_html(classes='game-logs-table', index=False)
        print(temp_df)


        end_index = end_index-1
        print("printing end_index:")
        print(end_index)
        return end_index, game_logs_html

if __name__ == '__main__':
    app.run(debug=False)
