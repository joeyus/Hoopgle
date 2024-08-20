from flask import Flask, request, redirect, url_for, render_template
import pandas as pd
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import requests

def tableScrape(player_url, cat_index, closest_ou_key, propt_num, name, closest_stat_key, year):
    response = requests.get(player_url)
    response.text
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

    # Display the DataFrame

    # Print to a file named table_scrape.txt with the index included
    with open('table_scrape.txt', 'w') as f:
        f.write(df.head().to_string(index=True))  # Write to the file with index

        # Initialize an empty DataFrame to store the results
    temp_df = pd.DataFrame(columns=df.columns)

    # List to accumulate rows as DataFrames
    rows_list = []

    # Iterate over each row of the DataFrame
    for index, row in df.iterrows():
        try:
            if closest_ou_key == "over":
                if isinstance(cat_index, int):
                    if int(row[cat_index]) > propt_num:
                        rows_list.append(row)
                elif isinstance(cat_index, list) and len(cat_index) == 2:
                    temp1 = row[cat_index[0]]
                    temp2 = row[cat_index[1]]
                    if int(temp1) + int(temp2) > propt_num:
                        rows_list.append(row)
            else:
                if isinstance(cat_index, int):
                    if int(row[cat_index]) < propt_num:
                        rows_list.append(row)
                elif isinstance(cat_index, list) and len(cat_index) == 2:
                    temp1 = row[cat_index[0]]
                    temp2 = row[cat_index[1]]
                    if int(temp1) + int(temp2) < propt_num:
                        rows_list.append(row)
        except ValueError:
            continue

    # Convert the list of Series (rows) to a DataFrame
    temp_df = pd.concat([pd.DataFrame([row], columns=df.columns) for row in rows_list], ignore_index=True)
    print(temp_df)

    # Calculate inactive games
    inactive_games = df['G'].apply(lambda x: len(str(x)) > 2).sum()

    # Calculate active games
    active_games = (len(df) - (len(df) // 20) - inactive_games)
    
    # Calculate the percentage
    percentage = (len(temp_df) / active_games) * 100
    format_percentage = "{:.2f}".format(percentage)
    
    # Display the final result
    result_message = f"{name} has covered the {closest_ou_key} {propt_num} {closest_stat_key} line in {year} in {len(temp_df)}/{active_games} ({format_percentage}%) games."
    print(result_message)

    return result_message, temp_df


    
    '''
    
    temp_array = set()
    for i in range(len(data_arrays)):
        try:
            if closest_ou_key == "over":
                if isinstance(cat_index, int):
                    if int(data_arrays[i][cat_index]) > propt_num:
                        temp_array.add(tuple(data_arrays[i]))
                elif isinstance(cat_index, list) and len(cat_index) == 2:
                    temp1 = data_arrays[i][cat_index[0]] 
                    temp2 = data_arrays[i][cat_index[1]]
                    if int(temp1) + int(temp2) > propt_num:
                        temp_array.add(tuple(data_arrays[i]))
            else:
                if isinstance(cat_index, int):
                    if int(data_arrays[i][cat_index]) < propt_num:
                        temp_array.add(tuple(data_arrays[i]))
                elif isinstance(cat_index, list) and len(cat_index) == 2:
                    temp1 = data_arrays[i][cat_index[0]]
                    temp2 = data_arrays[i][cat_index[1]]
                    if int(temp1) + int(temp2) < propt_num:
                        temp_array.add(tuple(data_arrays[i]))
        except ValueError:
            continue
        
    inactive_games = 0
    for i in range(len(data_arrays)):
        if len(data_arrays[i][1]) > 2:
            inactive_games += 1

    active_games = (len(data_arrays) - (len(data_arrays) // 20) - inactive_games)
    percentage = (len(temp_array) / active_games) * 100
    format_percentage = "{:.2f}".format(percentage)
    
    result_message = f"{name} has covered the {closest_ou_key} {propt_num} {closest_stat_key} line in {year} in {len(temp_array)}/{active_games} ({format_percentage}%) games."
    
    game_data = "\n".join([str(row) for row in temp_array])
    
    return result_message, game_data

'''
player_url = 'https://www.basketball-reference.com/players/j/jamesle01/gamelog/2024'
tableScrape(player_url, -3, 'over', 30, 'lebron james', 'points', 2024)