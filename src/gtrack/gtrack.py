import sys
import argparse
import sqlite3

from datetime import datetime
from gtrack import utils
from gtrack.config_manager import read_config_file
from gtrack.filter_manager import config_flags, scan_flags
from gtrack.insert_manager import insert_data, scan_data, remove_data
from gtrack.plot_manager import plot_data
from gtrack.print_manager import print_data

# Main program
def main():
    res = None
    dbpath = None
    filters = None
    plot_options = {}

    # Read configuration file for integrating custom properties
    configs = read_config_file()
    dbpath = configs["Paths"]
    filters = configs["Filters"]
    bucket_options = configs["BucketOptions"]
    plot_options["PoT"] = configs["PoT"]
    plot_options["MHoT"] = configs["MHoT"]

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

    if parsed_args["mode"] == utils.ProgramModes.FILTER.value:
        res = config_flags(parsed_args, connection, cursor)
        if res is not None:
            print(res)
            exit(-1)
    
    elif parsed_args["mode"] == utils.ProgramModes.INSERT.value:
        res = insert_data(parsed_args, bucket_options, connection, cursor)
        if res is not None:
            print(res)
            exit(-1)

    elif parsed_args["mode"] == utils.ProgramModes.PLOT.value:
        plot_data(parsed_args, plot_options, connection, cursor)
    
    elif parsed_args["mode"] == utils.ProgramModes.PRINT.value:
        print_data(parsed_args, connection, cursor)

    elif parsed_args["mode"] == utils.ProgramModes.REMOVE.value:
        remove_data(parsed_args["GID"], connection, cursor)

    elif parsed_args["mode"] == utils.ProgramModes.SCAN.value:
        scan_flags(filters[0], connection, cursor)
        res = scan_data((dbpath[1], dbpath[2]), bucket_options, connection, cursor)
        if res is not None:
            print(res)
            exit(-1)

    # Close connection
    connection.close()


# Creates the tables 'game' and 'activity' inside the database if they aren't alread present
def create_tables(cursor):

    query_game = """ CREATE TABLE IF NOT EXISTS Game (
                        id INTEGER PRIMARY KEY,
                        display_name VARCHAR(50) NOT NULL,
                        executable_name VARCHAR(50) NOT NULL
                ) """
    
    query_flags = """ CREATE TABLE IF NOT EXISTS Flag (
                        id INTEGER PRIMARY KEY,
                        name VARCHAR(50) NOT NULL
                ) """
    
    query_rel_flags= """ CREATE TABLE IF NOT EXISTS HasFlag (
                            game_id INT NOT NULL,
                            flag_id INT NOT NULL,
                            value INT NOT NULL,
                            PRIMARY KEY (game_id, flag_id)
                            FOREIGN KEY (game_id) REFERENCES Game(id),
                            FOREIGN KEY (flag_id) REFERENCES Flag(id)
                    ) """
    
    query_activity = """ CREATE TABLE IF NOT EXISTS Activity (
                            game_id INT NOT NULL,
                            date DATETIME NOT NULL,
                            playtime FLOAT NOT NULL,
                            PRIMARY KEY (game_id, date),
                            FOREIGN KEY (game_id) REFERENCES Game(id)
                    ) """
    
    cursor.execute(query_game)
    cursor.execute(query_flags)
    cursor.execute(query_rel_flags)
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
    parser_ins.add_argument("-t", "--type", dest="insert_choice", metavar="TYPE", type=str.lower, choices=["game", "bucket"], help="Data type to insert between ['game' | 'bucket']", required=True)

    # Filter options
    parser_config = subparser.add_parser(utils.ProgramModes.FILTER.value, help="Configure flags for filtering added games. These can only assume true/false values")
    exclusive_config_group = parser_config.add_mutually_exclusive_group(required=True)
    exclusive_config_group.add_argument("--add", dest="filter_add", metavar="FLAG_NAME", help="Add a new flag")
    exclusive_config_group.add_argument("--list", dest="filter_list", action="store_true", help="List all flags")
    exclusive_config_group.add_argument("--rm", dest="filter_rm", metavar="FLAG_ID", type=int, help="Remove a flag based on its ID")

    # Plot options
    plot_usage = app_name + " plot -t TYPE [-h] [-s PATH] [-cf FILTER_BASE_EXPR] [-f [FILTER_EXPR ...]] [-t | -d SDATE [EDATE]]"
    parser_plot = subparser.add_parser(utils.ProgramModes.PLOT.value, usage=plot_usage, help="Plot the recorded data")
    parser_plot.add_argument("-cf", "--color-by-filter", dest="color_filter_plot", type=str, metavar="FILTER_BASE_EXPR", action=utils.SimpleFilterProcessor, help="Highlight a part of the PoT graph based on the specified filter expression (only one flag ID is supported, as well as the NOT operator)")
    parser_plot.add_argument("-d", "--date", dest="date_plot_default", metavar="DATE", nargs="+", action=utils.DateProcessor, type=parse_date, help="Dates to constrain the information used by the plot")
    parser_plot.add_argument("-f", "--filter", dest="filter_plot", type=str, metavar="FILTER_EXPR", action=utils.FilterProcessor, help="Filter through the custom-defined flags for limiting the information shown by the plot using a boolean expression with the filter IDs")
    parser_plot.add_argument("-t", "--type", dest="plot_choice", metavar="TYPE", type=str.lower, choices=["pot", "mhot"], help="Type of plot to generate ['pot' (Playtime-over-Time) | 'mhot' (Mean-Hours-over-Time)]", required=True)
    parser_plot.add_argument("-tot", "--total", dest="plot_total", action="store_true", help="Plot the overall recorded information")

    # Print options
    print_usage = app_name + " print [-h] [-v] [-t | [[-d SDATE [EDATE]] [-dd] [-mm]] [-gid [GID ...] | -gname GNAME]"
    parser_print = subparser.add_parser(utils.ProgramModes.PRINT.value, usage=print_usage, help="Print time spent for provided games. By default, it prints the total playtime of every game played during the current year")
    exclusive_print_group_01 = parser_print.add_mutually_exclusive_group()
    exclusive_print_group_02 = parser_print.add_mutually_exclusive_group()

    parser_print.add_argument("-d", "--date", dest="date_print_default", metavar="DATE", nargs="+", action=utils.DateProcessor, type=parse_date, help="Dates to constrain the search period")
    exclusive_print_group_01.add_argument("-dd", "--daily", dest="print_daily", action="store_true", help="Total time spent on each game as a total per day")
    parser_print.add_argument("-f", "--filter", dest="filter_print", type=str, metavar="FILTER_EXPR", action=utils.FilterProcessor, help="Filter through the custom-defined flags using a boolean expression with filter IDs")
    exclusive_print_group_02.add_argument("-gid", dest="id_print", type=int, metavar="GID", nargs="+", help="Filter the information to the specified game IDs")
    exclusive_print_group_02.add_argument("-gname", dest="name_print", metavar="GNAME", help="Filter the information to the specified game name")
    parser_print.add_argument("--mean", dest="print_mean", action="store_true", help="Compute the mean time spent on playing with respect to the current year. Can be grouped with other filters.")
    exclusive_print_group_01.add_argument("-mm", "--monthly", dest="print_monthly", action="store_true", help="Total time spent on each game as a total per month")
    parser_print.add_argument("-s", "--sort-by", dest="print_sort", default="playtime", type=str.lower, choices=["name", "first_played", "last_played", "playtime"], help="Order the games based on the alphabetic order, play order (first or last played) or total playtime (default)")
    parser_print.add_argument("--sum", dest="print_sum", action="store_true", help="Compute the total time between all games stored inside the database for the current year. Can be grouped with other filters.")
    parser_print.add_argument("-t", "--total", dest="print_total", action="store_true", help="Total time spent on each game")
    parser_print.add_argument("-v", "--verbose", dest="print_verbose", action="store_true", help="Print additional information about each game. When adopting this flag, no total time is computed")

    # Remove options
    parser_rm = subparser.add_parser(utils.ProgramModes.REMOVE.value, help="Remove games from the database based on their ID")
    parser_rm.add_argument("GID", type=int, help="Game ID of the game to be removed")

    # Scan options
    parser_scan = subparser.add_parser(utils.ProgramModes.SCAN.value, help="Scan the paths indicated inside the configuration file for rapidly inserting/updating game and bucket's entries")

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

        if res["mode"] == "plot" and res["plot_total"] and res["date_plot_default"]:
            print("usage: " + plot_usage)
            print("error: " + app_name + " plot: error: argument -t/--total: not allowed with argument -d/--date")
            exit(-1)

        if res["mode"] == "plot" and res["plot_choice"] == "mhot" and res["color_filter_plot"]:
            print("usage: " + plot_usage)
            print("error: " + app_name + " plot: error: argument -cf/--color-by-filter: not allowed with plot type 'mhot' (Mean-Hours-over-Time)")
            exit(-1)
            
        if res["mode"] == "print" and res["print_total"] and (res["date_print_default"] or res["print_daily"] or res["print_monthly"]):
            print("usage: " + print_usage)
            print("error: " + app_name + " print: error: argument -t/--total: not allowed with argument -d/--date or -dd/--daily or -mm/--monthly")
            exit(-1)

        if res["mode"] == "print" and res["print_verbose"] and (res["print_daily"] or res["print_monthly"]):
            print("usage: " + print_usage)
            print("error: " + app_name + " print: error: argument -v/--verbose: not allowed with argument -dd/--daily or -mm/--monthly")
            exit(-1)

        if res["mode"] == "print" and res["print_verbose"] and (res["print_sum"] or res["print_mean"]):
            print("usage: " + print_usage)
            print("error: " + app_name + " print: error: argument -v/--verbose: not allowed with argument --sum or --mean")
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