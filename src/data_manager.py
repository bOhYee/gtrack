import csv
import json
import os
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from operator import itemgetter
from tabulate import tabulate, SEPARATING_LINE
from .utils import *
from .database_manager import *


# Interpretation layer for the INSERT mode
def read_data(parsed_args, connection, cursor):

    err = None

    if parsed_args["insert_manual_flag"] == 1:
        print("Manual insertion of a game chosen")
    else:
        # Check if user indicated a simple file or a directory of source files
        is_dir = os.path.isdir(parsed_args["insert_filepath"])
        is_path = os.path.isfile(parsed_args["insert_filepath"])

        if is_dir == 1:
            input_files = os.listdir(parsed_args["insert_filepath"])

            for file_name in input_files:
                # Game
                if parsed_args["insert_choice"] == "game" and file_name.lower().endswith(".csv"):
                    file = parsed_args["insert_filepath"] + str(file_name)
                    print("READING: " + file)
                    read_game_data_csv(file, connection, cursor)
                    print("")

                # Activity
                elif parsed_args["insert_choice"] == "bucket" and file_name.lower().endswith(".json"):
                    file = parsed_args["insert_filepath"] + str(file_name)
                    print("READING: " + file)
                    read_bucket_data_json(file, connection, cursor)
                    print("")
            
            print("Insertion complete!")

        elif is_path == 1:
            # Game
            if parsed_args["insert_choice"] == "game" and parsed_args["insert_filepath"].lower().endswith(".csv"):
                print("READING: " + parsed_args["insert_filepath"])
                read_game_data_csv(parsed_args["insert_filepath"], connection, cursor)
                print("Insertion complete!")

            # Activity
            elif parsed_args["insert_choice"] == "bucket" and parsed_args["insert_filepath"].lower().endswith(".json"):
                print("READING: " + parsed_args["insert_filepath"])
                read_bucket_data_json(parsed_args["insert_filepath"], connection, cursor)
                print("Insertion complete!")

            # Error
            else:
                err = "Error: the indicated file cannot be used for adding/updating new " + parsed_args["insert_choice"] + "s!"    

        else:
            err = "Error: the indicated path is not correct!"

    return err


# Read the list of games from a .csv file and add them to the sql database
def read_game_data_csv(path, connection, cursor):

    counter = 0                 # Counter to skip first line
    disc_counter = 0            # Discarded line counter
    input_file = open(path)     # Input file stream

    for line in csv.DictReader(input_file, FIELDNAMES):

        # Skip first line
        if counter == 0:
            counter += 1
            continue
        
        name = ""
        exe_name = ""
        status = ""
        flag_mult = 0
        flag_plat = 0

        # Value conditioning
        name = line["display_name"].strip() if line["display_name"].strip() != "" else None
        status = line["status"].strip() if line["status"].strip() != "" else None
        exe_name = line["executable_name"].strip().lower() if line["executable_name"].strip() != "" else None

        if line["multiplayer"].strip() == "":
            flag_mult = None

        elif line["multiplayer"].strip().upper() == "Y":
            flag_mult = 1
        
        if line["plat"].strip() == "":
            flag_plat = None

        elif line["plat"].strip().upper()  == "Y":
            flag_plat = 1

        # When some of the values are incorrect or empty, print a WARNING message
        # Not a fatal error, can skip to the follow-up ones
        if (name is None) or (status is None) or (exe_name is None) or (flag_mult is None) or (flag_plat is None):
            print("WARNING: line " + str(counter+1) + " contains some unexpected values! It will be discarded.")
            disc_counter += 1
            counter += 1
            continue

        # Check if entry already exist, based on the executable name, since it theoretically cannot change
        # In case it exists, UPDATE the row, otherwise INSERT a new row
        u_data = (name, status, flag_mult, flag_plat, exe_name)
        u_query = """ UPDATE Game
                    SET display_name = ?, status = ?, is_multiplayer = ?, has_platinum = ?
                    WHERE executable_name = ? """
        
        i_data = (name, exe_name, status, flag_mult, flag_plat)
        i_query = """ INSERT INTO Game (display_name, executable_name, status, is_multiplayer, has_platinum)
                    VALUES (?, ?, ?, ?, ?) """
                
        cursor.execute(u_query, u_data)
        if cursor.rowcount < 1:
            cursor.execute(i_query, i_data)

        counter += 1

    # When everything has been correctly parsed, commit
    connection.commit()

    if disc_counter > 0:
        print("WARNING: " + str(disc_counter) + " lines have been discarded for unexpected values encountered! Please check the input file.")
            

# Read the list of activities from the buckets produced by ActivityWatch and add them to the sql database
def read_bucket_data_json(path, connection, cursor):

    act_event_counter = 0
    disc_counter = 0
    activities = []
    a_ins = {}
    prev_end_time = 0
    datetime_event_format = "%Y-%m-%dT%H:%M:%S.%f%z"
    datetime_event_nomicro_format = "%Y-%m-%dT%H:%M:%S%z"
    different_activities_threshold = timedelta(seconds=DIFF_ACT_THRESHOLD)

    file = open(path, "r", encoding="UTF-8")
    data = json.load(file)

    # Obtain game names
    s_query = "SELECT id, executable_name FROM Game"
    cursor.execute(s_query)
    games = cursor.fetchall()

    # Useless to process the JSON file if no game has been inserted beforehand
    if not games:
        print("WARNING: no game has been found!\nAborting JSON processing...")
        return

    # Cycle between different buckets
    for bucket in data["buckets"]:

        # Extract the content of the bucket
        bucket_content = data["buckets"][bucket]["events"]
        
        # Cycle through the events
        for event in bucket_content:
            
            try:
                result = is_event_relevant(event["data"]["app"], games)

            except KeyError as ke:
                # When "app" or "title" do not exist, probably, it is because the .json is linked to the afk watcher
                print("WARNING: application's data is not present in the source file provided!\nAborting JSON parsing...")
                return

            if result != 0 and event["duration"] > 0:
                # Sometime the microseconds disappear
                try:
                    event_dt = datetime.strptime(event["timestamp"], datetime_event_format)
                except ValueError as date_err:
                    event_dt = datetime.strptime(event["timestamp"], datetime_event_nomicro_format)

                a = {
                    "game_id": result,
                    "datetime": event_dt,
                    "playtime": float(event["duration"])
                }

                activities.append(a)
                
    # Sort for better compute different activities
    activities = sorted(activities, key=itemgetter("game_id", "datetime"))
    for i in range(len(activities)):

        event = activities[i]

        # Need to duplicate the event when starting the cycle
        if i == 0 or not a_ins:
            a_ins = dict(event)

        # Check if the event is different from the previous one or if there is too much time
        # discrepancy between the two start times. Store the past one and start collecting
        # information on the new data
        elif a_ins["game_id"] != event["game_id"] or ((event["datetime"] - prev_end_time) > different_activities_threshold):
            disc_counter += insert_activity(a_ins["game_id"], a_ins["datetime"], a_ins["playtime"], cursor) * act_event_counter
            act_event_counter = 0
            a_ins = dict(event)

        else:
            a_ins["playtime"] += event["playtime"]

        act_event_counter += 1
        prev_end_time = event["datetime"] + timedelta(0, event["playtime"])

        # Last element has to be saved no matter what it is
        if i == len(activities) - 1:
            disc_counter += insert_activity(a_ins["game_id"], a_ins["datetime"], a_ins["playtime"], cursor) * act_event_counter
            act_event_counter = 0

    if disc_counter > 0:
        print("WARNING: " + str(disc_counter) + " out of " + str(len(activities)) + " events have been discarded for being duplicates...")

    # When everything goes well, commit the changes
    connection.commit()


# Check if the event is related to a game
# Returns 0 if not relevant, otherwise returns the game id
def is_event_relevant(event_name, game_list):

    event_name = event_name.strip().lower()
    if event_name == "":
        return 0
    
    for game in game_list:
        if event_name == game[1]:
            return game[0]
        
    return 0


# Interpretation layer for the PRINT mode
def print_data(parsed_args, connection, cursor):

    group_dates = parsed_args["print_daily"] or parsed_args["print_monthly"]
    query, args, headers = print_query_definition(args=parsed_args)

    if args:
        cursor.execute(query, args)
    else:
        cursor.execute(query)

    info = cursor.fetchall()
    print_data_cli(headers=headers, rows=info, group_dates=group_dates)


def print_query_definition(args):

    flag_verbose = args["print_verbose"]
    flag_daily = args["print_daily"]
    flag_monthly = args["print_monthly"]
    flag_total = args["print_total"] 
    dates = args["date_print_default"]
    gids = args["id_print"]
    gname = args["name_print"]

    temp_conditions = ""
    print_query = ""
    query_args = None
    headers = ["game_id", "game_name"]
    
    # SELECT
    # If verbose is selected, more info taken from Game table
    if flag_verbose:
        print_query += "SELECT Game.*, "
        headers += ["game_exe", "game_status", "game_mult", "game_plat"]
    else:
        print_query += "SELECT Game.id, Game.display_name, "

    # If daily is selected, the day has to be printed
    if flag_daily:
        print_query += "strftime('%Y-%m-%d', Activity.date) as rel_day, SUM(Activity.playtime) as total_playtime "
        headers += ["day"]
    # If monthly is selected, the month has to be printed
    elif flag_monthly:
        print_query += "strftime('%Y-%m', Activity.date) as rel_month, SUM(Activity.playtime) as total_playtime "
        headers += ["month"]
    else:
        print_query += "SUM(Activity.playtime) as total_playtime "
    
    headers += ["playtime (HH:MM:SS)"]
    print_query += "FROM Game, Activity "

    # WHERE
    print_query += "WHERE Game.id == Activity.game_id "

    # If total is requested, date filter is not needed
    if not flag_total:
        print_query += "AND date(Activity.date, 'localtime') >= ? "

        # Date can also be unspecified
        if dates:
            if len(dates) == 2:
                print_query += "AND date(Activity.date, 'localtime') <= ? "
                query_args = (dates[0], dates[1], )

            else:
                query_args = (dates[0], )
        
        else:
            start_year = datetime.strftime(datetime(datetime.now().year, 1, 1), "%Y-%m-%d")
            query_args = (start_year, )
    
    # Manage game IDs
    if gids:
        for i in range(len(gids)):
            temp_conditions += "Game.id == " + str(gids[i]) + " "

            if i < len(gids) - 1:
                temp_conditions += "OR "
            
        print_query += "AND (" + temp_conditions + ") "

    # Manage game name search
    if gname:
        print_query += "AND Game.display_name LIKE '%" + gname + "%' "

    # GROUP BY
    # game_id is unique, should be enough for differentiating games
    print_query += "GROUP BY Game.id "

    if flag_daily:
        print_query += ", rel_day "
    elif flag_monthly:
        print_query += ", rel_month "

    # ORDER BY
    print_query += "ORDER BY "

    if flag_daily:
        print_query += "rel_day DESC, "
    elif flag_monthly:
        print_query += "rel_month DESC, "

    print_query += "total_playtime DESC"
    return [print_query, query_args, headers]


def print_data_cli(headers, rows, group_dates):

    ins_barriers = 0
    barriers = []
    
    # Convert playtimes into HH:MM form
    for i in range(len(rows)):
        #print(rows[i])
        tmp_tuple = list(rows[i])

        min, sec = divmod(tmp_tuple[-1], 60)
        h, min = divmod(min, 60)
        tmp_tuple[-1] = "{hours:02d}:{minutes:02d}:{seconds:02d}".format(hours=int(h), minutes=int(min), seconds=int(sec))
        rows[i] = tmp_tuple

        if group_dates and i < (len(rows) - 1) and rows[i][-2] != rows[i+1][-2]:
            barriers.append(i+1)

    # Add barriers
    for i in range(len(barriers)):
        rows.insert(barriers[i] + ins_barriers, ("", ))
        ins_barriers += 1

    # Print information table
    print(tabulate(rows, headers=headers, tablefmt="fancy_outline"))

