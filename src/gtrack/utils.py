import argparse
from enum import Enum

# Database default location path
DB_PATH = "../data/project.db"

# Time threshold for saving an activity inside the DB
SAVE_ACT_THRESHOLD = 3 * 60

# Time threshold for identifying different gaming sessions
# Value is in SECONDS for better scalability
DIFF_ACT_THRESHOLD = 30 * 60

# Field names of the CSV file for the game table
FIELDNAMES = ("display_name", "executable_name", "status", "multiplayer", "plat")


# Program modalities
# Each one is associated to a different type of execution
class ProgramModes(Enum):
    INSERT  = "insert"       # Insert new data inside the tables from a .csv/.json file or from CLI
    SCAN    = "scan"         # Scan the paths contained in the .ini file to add new data
    PRINT   = "print"        # Print filtered data from the tables
    PLOT    = "plot"         # Plot data depending on user needs


# For argparse usage
# Used for correctly interpreting how many dates have been written by user
class DateProcessor(argparse.Action):

    def __call__(self, parser, namespace, values, option_string=None):

        if not 1 <= len(values) <= 2:
            msg = 'argument requires between {nmin} and {nmax} dates.'.format(f=self.dest,nmin=1,nmax=2)
            raise argparse.ArgumentTypeError(msg)
        
        if len(values) == 2 and values[0] > values[1]:
            msg = 'time interval bounds not well defined. Starting date {sdate} is greater than ending date {edate}.'.format(sdate=values[0], edate=values[1])
            raise argparse.ArgumentTypeError(msg)

        setattr(namespace, self.dest, values)