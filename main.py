import sys
import argparse
import sqlite3
import datetime

from sqlite3 import Error
from argparse import ArgumentTypeError
from src.utils import *
from src.data_manager import *
from src.database_manager import *


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
        res = read_data(parsed_args, connection, cursor)
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
    parser_ins = subparser.add_parser(ProgramModes.INSERT.value, help="Acquire new games or activities to the database from command-line or .csv/.json files")
    parser_ins.add_argument("-t", "--type", dest="insert_choice", metavar="TYPE", choices=["game", "bucket"], help="Data type to insert between ['game' | 'bucket']", required=True)
    exclusive_group = parser_ins.add_mutually_exclusive_group(required=True)
    exclusive_group.add_argument("-f", "--file", dest="insert_filepath", metavar="FILE", help="File to read from or directory containing source files")
    exclusive_group.add_argument("-m", "--manual", dest="insert_manual_flag", action="store_true", help="Indicates that the data will be given by the user")

    # Print options
    parser_print = subparser.add_parser(ProgramModes.PRINT.value, help="Print the game or activity lists. By default, it prints the list of game and relative total playtime.")
    parser_print.add_argument("-d", "--date", dest="date_print_default", metavar="DATE", nargs="+", action=DateProcessor, type=parse_date, help="Start and eventual end dates for computing total playtime")
    parser_print.add_argument("-m", dest="print_monthly", action="store_true", help="Print the informations as a total computed month by month")
    parser_print.add_argument("-t", "--total", dest="print_total", action="store_true", help="Print total playtime for all games present in the database")
    parser_print.add_argument("-v", "--show-moreinfo", dest="print_verbose", action="store_true", help="Print more informations about the game list")

    try:
        res = vars(parser.parse_args(params))        
        print(res)

    except ArgumentTypeError as e:
        print("usage: GameTracker print [-h] [-d DATE [DATE ...]]")
        print("error: " + str(e))
        print("Closing the program...")
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