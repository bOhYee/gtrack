import csv
import calendar
from datetime import datetime
from datetime import timedelta
FIELDNAMES = ("name", "status", "start_date", "end_date", "hours", "minutes", "plat")


def read_data_csv(fileName):
    flag_sdate = 0                  # Start date present
    counter = 0                     # Counter to skip first line
    game_list = []                  # Output list
    input_file = open(fileName)     # Input file stream
    format = "%d-%m-%Y"

    for line in csv.DictReader(input_file, FIELDNAMES):
        # Skip first line
        if counter == 0:
            counter += 1
            continue

        # Skip empty lines
        if line["name"] == "-" or not line["name"]:
            continue

        # Remove empty spaces before and after string for list search
        line["name"] = line["name"].strip()

        # Default value in case either end_date o start_date are missing
        flag_sdate = 0
        line["days"] = 0

        # Active game
        if line["status"] == "A":
            line["end_date"] = datetime.strftime(datetime.today(), format)

        # Convert start date
        if line["start_date"] != "-" and line["start_date"]:
            line["start_date"] = datetime.strptime(line["start_date"], format)
            flag_sdate = 1

        # Convert end date
        if line["end_date"] != "-" and line["end_date"]:
            line["end_date"] = datetime.strptime(line["end_date"], format)

            # Compute days between start and end dates
            if flag_sdate == 1:
                line["days"] = (line["end_date"] - line["start_date"]).days

        # Convert into a list of tuples
        line["dates"] = [(line["start_date"], line["end_date"])]
        del line["start_date"]
        del line["end_date"]

        # Round hours and minutes values
        if line["hours"] != "-":
            line["hours"] = round(float(line["hours"]), 2)
            line["minutes"] = round(float(line["minutes"]), 2)

        # If the game is already in the list
        index = is_present(line, game_list)
        if index != -1:
            game_list[index]["dates"].append(line["dates"][0])
            game_list[index]["hours"] += line["hours"]
            game_list[index]["minutes"] += line["minutes"]
            game_list[index]["days"] += line["days"]

            if game_list[index]["plat"] == "Y" or line["plat"] == "Y":
                game_list[index]["plat"] = "Y"
            else:
                game_list[index]["plat"] = "N"

        else:
            game_list.append(line)

    return game_list


def is_present(curr, data_list):

    # Search if the game was already inserted
    for index, game in enumerate(data_list):
        if curr["name"] == game["name"]:
            return index

    return -1


def total_time_played(data_list):

    total_time = 0      # Total time played

    for element in data_list:
        if element["hours"] != "-" and element["hours"]:
            total_time += float(element["hours"])

    return total_time


def playtime_per_day(data_list):

    playtime = [0] * (365 + calendar.isleap(datetime.now().year))

    for game in data_list:
        # No game time could be computed (missing information)
        if game["days"] == 0:
            continue

        # Playtime per day (not accurate though)
        time_per_day = round(game["hours"] / game["days"], 2)

        for interval in game["dates"]:
            start = interval[0]
            end = interval[1]
            if start == "-":
                continue

            # Compute how much playtime per day
            index = start.timetuple().tm_yday
            while start != end:
                playtime[index] = round(playtime[index] + time_per_day, 2)
                start += timedelta(days=1)
                index += 1

    return playtime
