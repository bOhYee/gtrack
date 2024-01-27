import csv
import json
import os
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from dateutil.tz import tzlocal
from operator import itemgetter


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
                    read_game_data_csv(file, connection, cursor)

                # Activity
                elif parsed_args["insert_choice"] == "bucket" and file_name.lower().endswith(".json"):
                    file = parsed_args["insert_filepath"] + str(file_name)
                    read_bucket_data_json(file, connection, cursor)

        elif is_path == 1:
            # Game
            if parsed_args["insert_choice"] == "game" and parsed_args["insert_filepath"].lower().endswith(".csv"):
                read_game_data_csv(parsed_args["insert_filepath"], connection, cursor)

            # Activity
            elif parsed_args["insert_choice"] == "bucket" and parsed_args["insert_filepath"].lower().endswith(".json"):
                read_bucket_data_json(parsed_args["insert_filepath"], connection, cursor)

            # Error
            else:
                err = "Error: the indicated file cannot be used for adding/updating new " + parsed_args[
                    "insert_choice"] + "s!"

        else:
            err = "Error: the indicated path is not correct!"

    return err


# Read the list of games from a .csv file and add them to the sql database
def read_game_data_csv(path, connection, cursor):
    counter = 0  # Counter to skip first line
    disc_counter = 0  # Discarded line counter
    input_file = open(path)  # Input file stream

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
        name = line["display_name"].strip().lower() if line["display_name"].strip() != "" else None
        status = line["status"].strip() if line["status"].strip() != "" else None
        exe_name = line["executable_name"].strip() if line["executable_name"].strip() != "" else None

        if line["multiplayer"].strip() == "":
            flag_mult = None

        elif line["multiplayer"].strip().upper() == "Y":
            flag_mult = 1

        if line["plat"].strip() == "":
            flag_plat = None

        elif line["plat"].strip().upper() == "Y":
            flag_plat = 1

        # When some of the values are incorrect or empty, print a WARNING message
        # Not a fatal error, can skip to the follow-up ones
        if (name is None) or (status is None) or (exe_name is None) or (flag_mult is None) or (flag_plat is None):
            print("WARNING: line " + str(counter + 1) + " contains some unexpected values! It will be discarded.")
            disc_counter += 1
            counter += 1
            continue

        # Check if entry already exist
        # In case it exists, UPDATE the row, otherwise INSERT a new row
        u_data = (exe_name, status, flag_mult, flag_plat, name)
        u_query = """ UPDATE Game
                    SET executable_name = ?, status = ?, is_multiplayer = ?, has_platinum = ?
                    WHERE display_name = ? """

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
        print("WARNING: " + str(
            disc_counter) + " lines have been discarded for unexpected values encountered! Please check the input file.")


# Read the list of activities from the buckets produced by ActivityWatch and add them to the sql database
def read_bucket_data_json(path, connection, cursor):
    activities = {}
    datetime_event_format = "%Y-%m-%dT%H:%M:%S.%f%z"
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
            result = is_event_relevant(event["data"]["title"], games)

            if result != 0 and event["duration"] > 0:
                event_dt = datetime.strptime(event["timestamp"], datetime_event_format).astimezone(tzlocal())
                event_date = event_dt.date()

                # Recover the activities of that day
                if str(event_date) in activities:
                    date_activities = activities[str(event_date)]
                else:
                    date_activities = []

                a = {
                    "game_id": result,
                    "datetime": event_dt,
                    "playtime": float(event["duration"])
                }

                date_activities.append(a)
                activities[str(event_date)] = date_activities

    # Cycle through the pre-processed activities for inserting in DB
    for act_date in sorted(activities.keys()):

        date_activities = activities[act_date]
        date_activities = sorted(date_activities, key=itemgetter("game_id", "datetime"))

        a_ins = {}
        prev_end_time = 0

        for i in range(len(date_activities)):

            event = date_activities[i]

            # Need to duplicate the event when starting the cycle
            if i == 0 or not a_ins:
                a_ins = dict(event)

            # Check if the event is different from the previous one or if there is too much time discrepancy between the two start times
            # Store the past one and start collecting information on the new data
            elif a_ins["game_id"] != event["game_id"] or (
                    (event["datetime"] - prev_end_time) > different_activities_threshold):
                insert_activity(a_ins["game_id"], a_ins["datetime"], a_ins["playtime"], cursor)
                a_ins = dict(event)

            else:
                a_ins["playtime"] += event["playtime"]

            prev_end_time = event["datetime"] + timedelta(0, event["playtime"])

            # Last element has to be saved no matter what it is
            if i == len(date_activities) - 1:
                insert_activity(a_ins["game_id"], a_ins["datetime"], a_ins["playtime"], cursor)

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
    launch_date = datetime.now()
    print_query = ""

    # Select what data to print
    # If verbose is selected, more info taken from Game table
    if parsed_args["print_verbose"]:
        print_query += "SELECT Game.*, "
    else:
        print_query += "SELECT Game.id, Game.display_name, "

    print_query += "SUM(Activity.playtime) "
    print_query += "FROM Game, Activity "
    print_query += "WHERE Game.id == Activity.game_id "

    print(tzlocal())
    print(launch_date)
    print(print_query)

