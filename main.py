import sys
import argparse
import sqlite3
import datetime

from sqlite3 import Error
from argparse import ArgumentTypeError
from src.utils import *
from src.insert_manager import *
from src.print_manager import *


# Main program
def main():

    # Connect to the sqlite3 database and check for the existance of the tables
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

    except Error as e:
        print("Error received while establishing the connection: " + str(e))
        exit(-1)

    create_tables(cursor)
    
    # Parse arguments received by the program
    parsed_args = parse_arguments(sys.argv[1:])

    res = None
    if parsed_args["mode"] == ProgramModes.INSERT.value:
        res = insert_data(parsed_args, connection, cursor)
        if res is not None:
            print(res)
            exit(-1)

    elif parsed_args["mode"] == ProgramModes.PRINT.value:
        print_data(parsed_args, connection, cursor)

    # Close connection
    connection.close()


# Parses the arguments received by the program
def parse_arguments(params):

    desc = "A simple python program to parse ActivityWatch data for keeping track of time spent on games."
    parser = argparse.ArgumentParser(prog="GameTracker", description=desc)
    subparser = parser.add_subparsers(dest="mode", required=True, help="'subcommand' help")

    # Insert options
    insert_usage = "GameTracker insert -t TYPE [-h] (-f FILE  [--create-template | --no-header] | -m)"
    parser_ins = subparser.add_parser(ProgramModes.INSERT.value, usage=insert_usage, help="Acquire new games or activities to the database from command-line or .csv/.json files")
    exclusive_group = parser_ins.add_mutually_exclusive_group(required=True)
    parser_ins.add_argument("--create-template", dest="template_flag", action="store_true", help="Create a template for custom insertion of the selected TYPE")
    exclusive_group.add_argument("-f", "--file", dest="insert_filepath", metavar="FILE", help="File to read from or directory containing source files")
    exclusive_group.add_argument("-m", "--manual", dest="insert_manual_flag", action="store_true", help="Indicates that the data will be given by the user")
    parser_ins.add_argument("--no-header", dest="header_flag", action="store_true", help="Indicates that the .csv file doesn't have any header")
    parser_ins.add_argument("-t", "--type", dest="insert_choice", metavar="TYPE", choices=["game", "bucket"], help="Data type to insert between ['game' | 'bucket']", required=True)

    # Print options
    print_usage = "GameTracker print [-h] [-v] [-t | [[-d SDATE [EDATE]] [-dd] [-mm]] [-gid [GID ...] | -gname GNAME]"
    parser_print = subparser.add_parser(ProgramModes.PRINT.value, usage=print_usage, help="Print the game or activity lists. By default, it prints the list of game and relative total playtime.")
    exclusive_print_group_01 = parser_print.add_mutually_exclusive_group()
    exclusive_print_group_02 = parser_print.add_mutually_exclusive_group()

    parser_print.add_argument("-d", "--date", dest="date_print_default", metavar="DATE", nargs="+", action=DateProcessor, type=parse_date, help="Start and eventual end dates for computing total playtime")
    exclusive_print_group_01.add_argument("-dd", "--daily", dest="print_daily", action="store_true", help="Print the information as a total computed day by day")
    exclusive_print_group_02.add_argument("-gid", dest="id_print", metavar="GID", nargs="+", help="Print the information related to the specified game IDs")
    exclusive_print_group_02.add_argument("-gname", dest="name_print", metavar="GNAME", help="Print the information related to the specified game name")
    exclusive_print_group_01.add_argument("-mm", "--monthly", dest="print_monthly", action="store_true", help="Print the information as a total computed month by month")
    parser_print.add_argument("-t", "--total", dest="print_total", action="store_true", help="Print total playtime for all games present in the database")
    parser_print.add_argument("-v", "--verbose", dest="print_verbose", action="store_true", help="Print more information about the game list")

    try:
        res = vars(parser.parse_args(params))
        if res["mode"] == "insert" and res["insert_manual_flag"] and (res["template_flag"] or res["header_flag"]):
            print("usage: " + insert_usage)
            print("error: GameTracker print: error: argument --no-header/--create-template: not allowed with argument -m/--manual")
            exit(-1)

        if res["mode"] == "insert" and res["insert_filepath"] and res["template_flag"] and res["header_flag"]:
            print("usage: " + insert_usage)
            print("error: GameTracker print: error: argument --create-template: not allowed with argument --no-header")
            exit(-1)

        if res["mode"] == "print" and res["print_total"] and (res["date_print_default"] or res["print_daily"] or res["print_monthly"]):
            print("usage: " + print_usage)
            print("error: GameTracker print: error: argument -t/--total: not allowed with argument -d/--date or -dd/--daily or -mm/--monthly")
            exit(-1)

    except ArgumentTypeError as e:
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