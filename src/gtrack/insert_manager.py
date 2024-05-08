import csv
import json
import os
from json import JSONDecodeError
from datetime import datetime
from datetime import timedelta
from operator import itemgetter
from gtrack import utils


# Interpretation layer for the INSERT mode
def insert_data(parsed_args, connection, cursor):
    err = None

    if parsed_args["insert_manual_flag"] == 1:
        err = insert_from_cli(connection, cursor)

    elif parsed_args["insert_filepath"] and parsed_args["template_flag"] == 1:
        err = create_template_file(parsed_args)

    else:
        err = insert_from_file(parsed_args, connection, cursor)

    return err


# Retrieve data to add to the Game table from CLI instead of a file
def insert_from_cli(connection, cursor):
    err = None
    flag_mult = 0
    flag_plat = 0
    flag_list = []
    flag_values = []

    # Get the flag list to allow inserting the additional flag's values
    flag_query = """ SELECT id, name
                     FROM Flag 
                     ORDER BY id ASC """

    cursor.execute(flag_query)
    flag_list = cursor.fetchall()

    # Take data from CLI input
    print("Provide the game's information to store")
    display_name = input("Name to be displayed: ").strip()
    exec_name = input("Name of the executable: ").strip()

    for i in range(len(flag_list)):
        value = 0
        flag = flag_list[i] 

        value = input("(opt) Value for " + flag[1] + " flag (y/n): ").strip().lower()
        if len(value) == 1 and (value == "y" or value == "1"):
            flag_values.append(1)
        else:
            flag_values.append(0)

    if display_name == "" or exec_name == "":
        err = "ERROR: display name and executable name have to be defined!"
        return err

    # Check if entry already exist, based on the executable name, since it theoretically cannot change
    # In case it exists, UPDATE the row, otherwise INSERT a new row
    sel_data = (exec_name, )
    sel_query = """ SELECT COUNT(*) FROM Game WHERE executable_name = ? """

    u_data = (display_name, exec_name)
    u_query = """ UPDATE Game
                  SET display_name = ?
                  WHERE executable_name = ? """

    i_data = (display_name, exec_name)
    i_query = """ INSERT INTO Game (display_name, executable_name)
                  VALUES (?, ?) """

    cursor.execute(sel_query, sel_data)
    if cursor.fetchone()[0] > 0:
        print("WARNING: game already exists.")
        ans = input("Do you want to update the entry? (y/n) ").strip().lower()

        if ans == "y":
            cursor.execute(u_query, u_data)
    else:
        cursor.execute(i_query, i_data)

    connection.commit()

    # Retrieve the game ID and insert the flag values inside the HasFlag table
    s_data = (exec_name, )
    s_query = """ SELECT id
                  FROM Game
                  WHERE executable_name = ? """
    
    cursor.execute(s_query, s_data)
    gid = cursor.fetchall()[0][0]

    sel_query = """ SELECT COUNT(*) 
                    FROM HasFlag 
                    WHERE game_id = ? AND flag_id = ? """

    u_query = """ UPDATE HasFlag
                  SET value = ?
                  WHERE game_id = ? AND flag_id = ? """

    i_query = """INSERT INTO HasFlag (game_id, flag_id, value)
                 VALUES (?, ?, ?) """
    
    for i in range(len(flag_list)):
        sel_data = (gid, flag_list[i][0])
        u_data = (flag_values[i], gid, flag_list[i][0])
        i_data = (gid, flag_list[i][0], flag_values[i])

        cursor.execute(sel_query, sel_data)
        if cursor.fetchone()[0] > 0 and ans == "y":
            cursor.execute(u_query, u_data)  
        else:
            cursor.execute(i_query, i_data)
    
    connection.commit()
    return err

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
    counter = 0       # Counter to skip first line
    disc_counter = 0  # Discarded line counter
    flag_list = []    # Flag list 
    exe_list = []     # Executable list
    option_list = []  # Options for parsable lines

    # Get the flag list to interpret the additional options in the .csv
    flag_query = """ SELECT id
                     FROM Flag 
                     ORDER BY id ASC """

    cursor.execute(flag_query)
    flag_list = cursor.fetchall()

    # Parse the .csv and insert games
    for line in csv.DictReader(input_stream, utils.FIELDNAMES, restkey="flags"):
        # Skip first line when the header of the .csv file is present
        if not header_flag and counter == 0:
            counter += 1
            continue

        name = None
        exe_name = None
        options = []
        flag_val = 0

        # Value conditioning:
        # Mandatory
        if line["display_name"]:
            name = line["display_name"].strip() if line["display_name"].strip() != "" else None

        if line["executable_name"]:
            exe_name = line["executable_name"].strip().lower() if line["executable_name"].strip() != "" else None

        # When some of the values are incorrect or empty, print a WARNING message
        # Not a fatal error, can skip to the follow-up ones
        if (name is None) or (exe_name is None):
            print("WARNING: line " + str(counter + 1) + " contains some unexpected values! It will be discarded.")
            disc_counter += 1
            counter += 1
            continue

        # Optional
        for flag in line["flags"]:
            flag_val = 0

            if flag.strip().upper() == "Y" or flag.strip().upper() == "1":
                flag_val = 1

            options += [flag_val]  
        
        if len(flag_list) > len(options):
            print("WARNING: line " + str(counter + 1) + " does not contain values for all defined flags. The default value ('false') will be assigned.")
            while (len(flag_list) - len(options)) > 0:
                options += [0]

        # Check if entry already exist, based on the executable name, since it theoretically cannot change
        # In case it exists, UPDATE the row, otherwise INSERT a new row
        u_data = (name, exe_name)
        u_query = """ UPDATE Game
                      SET display_name = ?
                      WHERE executable_name = ? """

        i_data = (name, exe_name)
        i_query = """ INSERT INTO Game (display_name, executable_name)
                      VALUES (?, ?) """

        cursor.execute(u_query, u_data)        
        if cursor.rowcount < 1:
            cursor.execute(i_query, i_data)

        counter += 1
        exe_list.append(exe_name)
        option_list.append(options)

    # Commit the changes to the Game table
    connection.commit()

    # Insert the flags values
    if (len(exe_list) != len(option_list)):
        print("ERROR: cannot insert flag options due to some unexpected problem! Terminating program...")
        return
    
    for i in range(len(exe_list)):
        # For each game, retrieve its ID and make an insert inside the HasFlag table
        exe_name = exe_list[i]
        options = option_list[i]

        s_data = (exe_name, )
        s_query = """SELECT id
                     FROM Game
                     WHERE executable_name = ? """
        
        cursor.execute(s_query, s_data)
        gid = cursor.fetchall()[0][0]

        u_query = """ UPDATE HasFlag
                      SET value = ?
                      WHERE game_id = ? AND flag_id = ? """
    
        i_query = """INSERT INTO HasFlag (game_id, flag_id, value)
                     VALUES (?, ?, ?) """
        
        for i in range(len(flag_list)):
            u_data = (options[i], gid, flag_list[i][0])
            i_data = (gid, flag_list[i][0], options[i])

            cursor.execute(u_query, u_data)        
            if cursor.rowcount < 1:
                cursor.execute(i_query, i_data)

    # Commit the changes to the HasFlag table
    connection.commit()
    if disc_counter > 0:
        print("WARNING: " + str(disc_counter) + " lines have been discarded for unexpected values encountered! Please check the input file.")


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
    different_activities_threshold = timedelta(seconds=utils.DIFF_ACT_THRESHOLD)

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


# Inserts an activity, pre-elaborated from the bucket, inside the table
def insert_activity(gid, dt, playtime, cursor):

    playtime = round(playtime, 3)

    # Playtime should be above a certain threshold
    # In this way, meaningless events are avoided and not taken into account for the counts
    if playtime <= utils.SAVE_ACT_THRESHOLD:
        return 1

    # Verify that the data doesn't exist
    search_query = """ SELECT COUNT(*)
                       FROM Activity
                       WHERE game_id = ? AND date = ? """
    
    search_data = (gid, dt)
    cursor.execute(search_query, search_data)
    if cursor.fetchone()[0] == 1:
        return 2
    
    i_data = (gid, dt, playtime)
    i_query = """ INSERT INTO Activity (game_id, date, playtime)
                  VALUES (?, ?, ?) """

    cursor.execute(i_query, i_data)
    return 0


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

    fields = list(utils.FIELDNAMES)    
    rows = [{fields[0]: "Lethal company", fields[1]: "Lethal Company.exe"},
            {fields[0]: "Rocket League", fields[1]: "RocketLeague.exe"}]

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


# Preparation layer for the SCAN mode
def scan_data(paths, connection, cursor):
    err = None
    pargs = {}

    # No path indicated
    if paths[0] is None and paths[1] is None:
        print("The configuration file does not specify a path. The operation will be terminated.")
        return

    # Insert games first
    if paths[0] is not None and paths[0].strip() != "":
        print("Scanning game folder: " + paths[0])
        pargs["insert_filepath"] = paths[0]
        pargs["insert_choice"] = "game"
        pargs["header_flag"] = 0
        err = insert_from_file(pargs, connection, cursor)
        if err:
            return err
        
        print("")

    # Insert buckets
    if paths[1] is not None and paths[1].strip() != "":
        pargs = {}
        pargs["insert_filepath"] = paths[1]
        pargs["insert_choice"] = "bucket"
        print("Scanning bucket folder: " + paths[1])
        err = insert_from_file(pargs, connection, cursor)

    return err


# Remove operation on the database
# A game and all of its activities are removed based on its ID (GID)
def remove_data(gid, connection, cursor):

    rm_data = (gid,)
    remove_act_query = """ DELETE FROM Activity
                           WHERE game_id = ? """
    
    remove_hf_query = """DELETE FROM HasFlag
                         WHERE game_id = ? """
    
    remove_game_query = """ DELETE FROM Game
                            WHERE id = ? """
    
    cursor.execute(remove_act_query, rm_data)
    cursor.execute(remove_hf_query, rm_data)
    cursor.execute(remove_game_query, rm_data)
    connection.commit()
    return