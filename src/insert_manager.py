import csv
import json
import os
from json import JSONDecodeError
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from operator import itemgetter

from .utils import *
from .database_manager import *


# Interpretation layer for the INSERT mode
def insert_data(parsed_args, connection, cursor):
    err = None

    if parsed_args["insert_manual_flag"] == 1:
        insert_from_cli()

    elif parsed_args["insert_filepath"] and parsed_args["template_flag"] == 1:
        err = create_template_file(parsed_args)

    else:
        err = insert_from_file(parsed_args, connection, cursor)

    return err


# Retrieve data to add to the Game table from CLI instead of a file
def insert_from_cli():
    print("Manual insertion to be implemented!")


# Determine which method has to be launched for reading file
# Additional controls for eventual errors during execution
def insert_from_file(parsed_args, connection, cursor):
    err = None
    
    # Check if user indicated a simple file or a directory of source files
    is_dir = os.path.isdir(parsed_args["insert_filepath"])
    is_path = os.path.isfile(parsed_args["insert_filepath"])
    
    # Obtain game names
    s_query = "SELECT id, executable_name FROM Game"
    cursor.execute(s_query)
    games = cursor.fetchall()

    # Useless to process the JSON file if no game has been inserted beforehand
    if parsed_args["insert_choice"] == "bucket" and not games:
        err = "ERROR: no game has been found! Buckets will not be processed..."
        return err

    if is_dir == 1:
        input_files = os.listdir(parsed_args["insert_filepath"])

        for file_name in input_files:
            # Game
            if parsed_args["insert_choice"] == "game" and file_name.lower().endswith(".csv"):
                file = parsed_args["insert_filepath"] + str(file_name)
                open_data_file(file, 0, parsed_args["header_flag"], None, connection, cursor)

            # Activity
            elif parsed_args["insert_choice"] == "bucket" and file_name.lower().endswith(".json"):
                file = parsed_args["insert_filepath"] + str(file_name)
                open_data_file(file, 1, None, games, connection, cursor)

        print("Insertion complete!")

    elif is_path == 1:
        # Game
        if parsed_args["insert_choice"] == "game" and parsed_args["insert_filepath"].lower().endswith(".csv"):
            open_data_file(parsed_args["insert_filepath"], 0, parsed_args["header_flag"], None, connection, cursor)

        # Activity
        elif parsed_args["insert_choice"] == "bucket" and parsed_args["insert_filepath"].lower().endswith(".json"):
            open_data_file(parsed_args["insert_filepath"], 1, None, games, connection, cursor)

        # Error
        else:
            err = "ERROR: the indicated file cannot be used for adding/updating " + parsed_args["insert_choice"] + "s!"

    else:
        err = "ERROR: the indicated path is not correct!"

    return err


# Checks for possible errors while opening the file and launches the correct module
def open_data_file(file_name, file_type, header_flag, game_list, connection, cursor):
    try:
        input_file = open(file_name)
    except OSError:
        print("ERROR: file " + file_name + " couldn't be opened/read!")
        return 1

    print("Reading: " + file_name)
    with input_file:
        if file_type == 0:
            read_game_data_csv(input_file, header_flag, connection, cursor)
        else:
            read_bucket_data_json(input_file, game_list, connection, cursor)

    return 0


# Read the list of games from a .csv file and add them to the sql database
def read_game_data_csv(input_stream, header_flag, connection, cursor):
    counter = 0  # Counter to skip first line
    disc_counter = 0  # Discarded line counter

    for line in csv.DictReader(input_stream, FIELDNAMES):
        # Skip first line when the header of the .csv file is present
        if not header_flag and counter == 0:
            counter += 1
            continue

        name = None
        exe_name = None
        status = ""
        flag_mult = 0
        flag_plat = 0

        # Value conditioning:
        # Mandatory
        if line["display_name"]:
            name = line["display_name"].strip() if line["display_name"].strip() != "" else None

        if line["executable_name"]:
            exe_name = line["executable_name"].strip().lower() if line["executable_name"].strip() != "" else None

        # Optional
        if line["status"]:
            status = line["status"].strip() if line["status"].strip() != "" else ""

        if not line["multiplayer"] or line["multiplayer"].strip() == "":
            flag_mult = 0
        elif line["multiplayer"].strip().upper() == "Y":
            flag_mult = 1

        if not line["plat"] or line["plat"].strip() == "":
            flag_plat = 0
        elif line["plat"].strip().upper() == "Y":
            flag_plat = 1

        # When some of the values are incorrect or empty, print a WARNING message
        # Not a fatal error, can skip to the follow-up ones
        if (name is None) or (exe_name is None):
            print("WARNING: line " + str(counter + 1) + " contains some unexpected values! It will be discarded.")
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
        print("\nWARNING: " + str(disc_counter) + " lines have been discarded for unexpected values encountered! Please check the input file.")


# Read the list of activities from the buckets produced by ActivityWatch and add them to the sql database
def read_bucket_data_json(input_stream, games, connection, cursor):
    act_event_counter = 0
    uthres_counter = 0
    dup_counter = 0
    activities = []
    a_ins = {}
    prev_end_time = 0
    datetime_event_format = "%Y-%m-%dT%H:%M:%S.%f%z"
    datetime_event_nomicro_format = "%Y-%m-%dT%H:%M:%S%z"
    different_activities_threshold = timedelta(seconds=DIFF_ACT_THRESHOLD)

    try: 
        data = json.load(input_stream)
    except JSONDecodeError as je:
        print("ERROR: json file could not be decoded due to:" + str(je))
        return

    try:
        # Cycle between different buckets
        for bucket in data["buckets"]:

            # Extract the content of the bucket
            bucket_content = data["buckets"][bucket]["events"]

            # Cycle through the events
            for event in bucket_content:
                result = is_event_relevant(event["data"]["app"], games)

                if event["duration"] and result != 0 and event["duration"] > 0:
                    # Sometimes the microseconds disappear
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

    except TypeError as te:
        print("ERROR: some key dictionary couldn't be found inside the provided json file! Aborting file processing...")
        return

    except KeyError as ke:
        print("ERROR: key " + str(ke) + " couldn't be found inside the provided json file! Aborting file processing...")
        return

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
            ins_res = insert_activity(a_ins["game_id"], a_ins["datetime"], a_ins["playtime"], cursor)
            if ins_res == 1:
                uthres_counter += act_event_counter
            elif ins_res == 2:
                dup_counter += act_event_counter

            act_event_counter = 0
            a_ins = dict(event)

        else:
            a_ins["playtime"] += event["playtime"]

        act_event_counter += 1
        prev_end_time = event["datetime"] + timedelta(0, event["playtime"])

        # Last element has to be saved no matter what it is
        if i == len(activities) - 1:
            ins_res = insert_activity(a_ins["game_id"], a_ins["datetime"], a_ins["playtime"], cursor)
            if ins_res == 1:
                uthres_counter += act_event_counter
            elif ins_res == 2:
                dup_counter += act_event_counter

            act_event_counter = 0

    if uthres_counter > 0:
        print("WARNING: " + str(uthres_counter) + " out of " + str(len(activities)) + " events have been discarded for being low time activities...")

    if dup_counter > 0:
        print("WARNING: " + str(dup_counter) + " out of " + str(len(activities)) + " events have been discarded for being duplicates...")

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


# Function that performs checks before creating template files
def create_template_file(parsed_args):
    err = None
    selected_type = 0  # Selected TYPE: 1-game; 2-bucket
    
    # Check if user indicated a simple file or a directory of source files
    is_path = os.path.isfile(parsed_args["insert_filepath"])
    file_basename = os.path.basename(parsed_args["insert_filepath"])
    selected_type = 1 if parsed_args["insert_choice"] == "game" else 2

    if not((file_basename.endswith(".csv") and selected_type == 1) or (file_basename.endswith(".json") and selected_type == 2)):
        err = "ERROR: the indicated path is not correct! Please provide a path to a csv or json file to save the template data."

    elif is_path == 1:
        print("WARNING: the indicated file already exists.")
        cli_answer = input("Do you want to overwrite it? (y/n) ").lower()
        
        if not(cli_answer == "y"):
            print("Closing program...")
        else:
            err = open_template_file(parsed_args["insert_filepath"], selected_type)

    else:
        err = open_template_file(parsed_args["insert_filepath"], selected_type)

    return err


# Creation of the template file last check on file opening
def open_template_file(file_name, sel_type):
    err = None

    try:
        with open(file_name, "w", encoding="UTF-8") as template:
            if sel_type == 1:
                create_game_template(template)
            else:
                create_bucket_template(template)
    
    except PermissionError as pe:
        err = "ERROR: not authorized to write the template file on the indicated path!"
    
    except OSError as oe:
        err = "ERROR: could not open file due to: " + str(oe)

    return err


# Creation of the csv template
# Two example lines are provided to better understand field values
def create_game_template(file_name):

    fields = list(FIELDNAMES)    
    rows = [{fields[0]: "Lethal company", fields[1]: "Lethal Company.exe", fields[2]: "A", fields[3]: "Y", fields[4]: "N"},
            {fields[0]: "Rocket League", fields[1]: "RocketLeague.exe", fields[2]: "F", fields[3]: "Y", fields[4]: "Y"}]

    writer = csv.DictWriter(file_name, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return


# Creation of the json template
# Two example lines are provided to better understand field values
def create_bucket_template(file_name):

    # Definition of two examples to put inside the template
    event_a = {
        "duration": 10.009, 
        "timestamp": "2022-12-18T14:28:29.802000+00:00",
        "data": {
            "app": "RocketLeague.exe", 
            "title": "Rocket League"
        }
    }

    event_b = {
        "duration": 10.009, 
        "timestamp": "2022-12-18T14:28:29.802000+00:00",
        "data": {
            "app": "RocketLeague.exe", 
            "title": "Rocket League"
        }
    }

    events = [event_a, event_b]
    watcher = {"events": events}
    buckets = {"buckets": {"aw-watcher-window-#1": watcher}}
    json_obj = json.dumps(buckets, indent=4)

    file_name.write(json_obj)
    return