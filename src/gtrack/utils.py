import argparse
import platformdirs
from enum import Enum

# Paths for the application (platform-dependent)
CONFIG_PATH = platformdirs.user_config_dir("gtrack", ensure_exists=True)    # Configuration file
DB_PATH = platformdirs.user_data_dir("gtrack", ensure_exists=True)          # Database default (CONFIGURABLE)

# Time thresholds (in SECONDS)
SAVE_ACT_THRESHOLD = 3 * 60                     # Used to filter relevant activities (CONFIGURABLE)
DIFF_ACT_THRESHOLD = 30 * 60                    # Used to identify different gaming sessions (CONFIGURABLE)

# Field names of the CSV file for the game table
FIELDNAMES = ("display_name", "executable_name")

# Program modalities
# Each one is associated to a different type of execution
class ProgramModes(Enum):
    INSERT  = "add"          # Insert new data inside the tables from a .csv/.json file or from CLI
    FILTER  = "filter"       # Configure the game filters/flags
    PLOT    = "plot"         # Plot data depending on user needs
    PRINT   = "print"        # Print filtered data from the tables
    REMOVE  = "rm"           # Remove unwanted processes from the database
    SCAN    = "scan"         # Scan the paths contained in the .ini file to add new data


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