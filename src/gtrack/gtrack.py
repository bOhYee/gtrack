import sys
import argparse
import datetime
import sqlite3
import configparser

from pathlib import Path
from gtrack import utils
from gtrack.insert_manager import insert_data, scan_data
from gtrack.print_manager import print_data

# Main program
def main():
    res = None
    dbpath = None

    # Read config file to know the DB location
    dbpath = read_config_file()

    # Connect to the sqlite3 database and check for the existance of the tables
    # When the database is not found in the indicated directory, it is created
    try:
        connection = sqlite3.connect(dbpath[0])
        cursor = connection.cursor()

    except sqlite3.Error as e:
        print("ERROR: connection to the database could not be established due to " + str(e))
        exit(-1)

    create_tables(cursor)
    
    # Parse arguments received by the program
    parsed_args = parse_arguments(sys.argv[1:])

    if parsed_args["mode"] == utils.ProgramModes.INSERT.value:
        res = insert_data(parsed_args, connection, cursor)
        if res is not None:
            print(res)
            exit(-1)

    elif parsed_args["mode"] == utils.ProgramModes.SCAN.value:
        res = scan_data((dbpath[1], dbpath[2]), connection, cursor)
        if res is not None:
            print(res)
            exit(-1)

    elif parsed_args["mode"] == utils.ProgramModes.PRINT.value:
        print_data(parsed_args, connection, cursor)

    # Close connection
    connection.close()


# Read configuration file
def read_config_file():
    res = None
    path_data_game = None
    path_data_bucket = None
    config = configparser.ConfigParser()

    try:
        # Path where the config is supposed to be located is $HOME/.gtrack/config.ini
        config.read_file(open(Path.home() / ".gtrack" / "config.ini"))
        paths = config["Paths"]

        path_data_game = str(paths["path_data_game"]) if "path_data_game" in paths else None
        path_data_bucket = str(paths["path_data_bucket"]) if "path_data_bucket" in paths else None
        res = (str(paths["path_db"]), path_data_game, path_data_bucket)

    except OSError:
        print("ERROR: configuration file could not be found")
        exit(-1)

    except KeyError as ke:
        print("ERROR: missing key-value pair " + str(ke))
        exit(-1)

    return res


# Creates the tables 'game' and 'activity' inside the database if they aren't alread present
def create_tables(cursor):

    query_game = """ CREATE TABLE IF NOT EXISTS Game (
                        id INTEGER PRIMARY KEY,
                        display_name VARCHAR(50) NOT NULL,
                        executable_name VARCHAR(50) NOT NULL,
                        status VARCHAR(50),
                        is_multiplayer INT,
                        has_platinum INT
                    ) """
    
    query_activity = """ CREATE TABLE IF NOT EXISTS Activity (
                            game_id INT NOT NULL,
                            date DATETIME NOT NULL,
                            playtime FLOAT NOT NULL,
                            PRIMARY KEY (game_id, date)
                            FOREIGN KEY (game_id) REFERENCES game(id)
                    ) """
    
    cursor.execute(query_game)
    cursor.execute(query_activity)


# Parses the arguments received by the program
def parse_arguments(params):

    app_name = "gtrack"
    desc = "A simple python program to parse ActivityWatch data for keeping track of time spent on games."
    parser = argparse.ArgumentParser(prog=app_name, description=desc)
    subparser = parser.add_subparsers(dest="mode", required=True, help="'subcommand' help")

    # Insert options
    insert_usage = app_name + " insert -t TYPE [-h] (-f FILE  [--create-template | --no-header] | -m)"
    parser_ins = subparser.add_parser(utils.ProgramModes.INSERT.value, usage=insert_usage, help="Provide new games or buckets to add to the database from command-line or .csv/.json files")
    exclusive_group = parser_ins.add_mutually_exclusive_group(required=True)
    parser_ins.add_argument("--create-template", dest="template_flag", action="store_true", help="Create a template for custom insertion of the selected TYPE")
    exclusive_group.add_argument("-f", "--file", dest="insert_filepath", metavar="FILE", help="File to read from or directory containing source files")
    exclusive_group.add_argument("-m", "--manual", dest="insert_manual_flag", action="store_true", help="Manual insertion of game's data")
    parser_ins.add_argument("--no-header", dest="header_flag", action="store_true", help="Don't skip any line while parsing the .csv file")
    parser_ins.add_argument("-t", "--type", dest="insert_choice", metavar="TYPE", choices=["game", "bucket"], help="Data type to insert between ['game' | 'bucket']", required=True)

    # Scan options
    parser_scan = subparser.add_parser(utils.ProgramModes.SCAN.value, help="Scan the paths indicated inside the configuration file for rapidly inserting/updating game and bucket's entries")

    # Print options
    print_usage = app_name + " print [-h] [-v] [-t | [[-d SDATE [EDATE]] [-dd] [-mm]] [-gid [GID ...] | -gname GNAME]"
    parser_print = subparser.add_parser(utils.ProgramModes.PRINT.value, usage=print_usage, help="Print time spent for provided games. By default, it prints the total playtimes for the current year")
    exclusive_print_group_01 = parser_print.add_mutually_exclusive_group()
    exclusive_print_group_02 = parser_print.add_mutually_exclusive_group()

    parser_print.add_argument("-d", "--date", dest="date_print_default", metavar="DATE", nargs="+", action=utils.DateProcessor, type=parse_date, help="Dates to constrain the computations")
    exclusive_print_group_01.add_argument("-dd", "--daily", dest="print_daily", action="store_true", help="Total time spent on each game as a total per day")
    exclusive_print_group_02.add_argument("-gid", dest="id_print", metavar="GID", nargs="+", help="Filter the information to the specified game IDs")
    exclusive_print_group_02.add_argument("-gname", dest="name_print", metavar="GNAME", help="Filter the information to the specified game name")
    exclusive_print_group_01.add_argument("-mm", "--monthly", dest="print_monthly", action="store_true", help="Total time spent on each game as a total per month")
    parser_print.add_argument("-t", "--total", dest="print_total", action="store_true", help="Total time spent on each game. No constraint can be applied when adopting this flag")
    parser_print.add_argument("-v", "--verbose", dest="print_verbose", action="store_true", help="Print additional information about each game. When adopting this flag, no total time is computed")

    try:
        res = vars(parser.parse_args(params))
        if res["mode"] == "insert" and res["insert_manual_flag"] and res["insert_choice"] == "bucket":
            print("usage: " + insert_usage)
            print("error: " + app_name + " print: error: manual search enabled only games")
            exit(-1)

        if res["mode"] == "insert" and res["insert_manual_flag"] and (res["template_flag"] or res["header_flag"]):
            print("usage: " + insert_usage)
            print("error: " + app_name + " print: error: argument --no-header/--create-template: not allowed with argument -m/--manual")
            exit(-1)

        if res["mode"] == "insert" and res["insert_filepath"] and res["template_flag"] and res["header_flag"]:
            print("usage: " + insert_usage)
            print("error: " + app_name + " print: error: argument --create-template: not allowed with argument --no-header")
            exit(-1)

        if res["mode"] == "print" and res["print_total"] and (res["date_print_default"] or res["print_daily"] or res["print_monthly"]):
            print("usage: " + print_usage)
            print("error: " + app_name + " print: error: argument -t/--total: not allowed with argument -d/--date or -dd/--daily or -mm/--monthly")
            exit(-1)

    except argparse.ArgumentTypeError as e:
        print("usage: " + print_usage)
        print("error: " + str(e))
        exit(-1)

    return res


# Parse the date argument
def parse_date(date_str):

    # Date assumed with the format 'YYYY-MM-DD'
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use 'YYYY-MM-DD'.")


if __name__ == '__main__':
    main()