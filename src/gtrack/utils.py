import argparse
import platformdirs
import pyparsing as pp
from enum import Enum

# Paths for the application (platform-dependent)
CONFIG_PATH = platformdirs.user_config_dir("gtrack", ensure_exists=True)    # Configuration file
DB_PATH = platformdirs.user_data_dir("gtrack", ensure_exists=True)          # Database default (CONFIGURABLE)

# Time thresholds (in SECONDS)
SAVE_ACT_THRESHOLD = 3 * 60                     # Used to filter relevant activities (CONFIGURABLE)
DIFF_ACT_THRESHOLD = 30 * 60                    # Used to identify different gaming sessions (CONFIGURABLE)

# Font sizes for plots
BAR_FONT_SIZE = 16
TITLE_FONT_SIZE = 16
LABEL_FONT_SIZE = 14

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

        if "plot" in parser.prog and "mhot" in namespace.plot_choice:
            if len(values) < 2:
                msg = 'argument requires both start and end dates for this specific plot.'
                raise argparse.ArgumentTypeError(msg)
            
            if len(values) > 2:
                msg = 'argument requires a maximum of 2 dates.'
                raise argparse.ArgumentTypeError(msg)
            
        else:
            if not 1 <= len(values) <= 2:
                msg = 'argument requires between {nmin} and {nmax} dates.'.format(f=self.dest,nmin=1,nmax=2)
                raise argparse.ArgumentTypeError(msg)

        if len(values) == 2 and values[0] > values[1]:
            msg = 'time interval bounds not well defined. Starting date {sdate} is greater than ending date {edate}.'.format(sdate=values[0], edate=values[1])
            raise argparse.ArgumentTypeError(msg)

        setattr(namespace, self.dest, values)


# For argparse usage
# Used for correctly parsing the simpler type of filter boolean expression for highlighting bars on PoT
class SimpleFilterProcessor(argparse.Action):

    def __call__(self, parser, namespace, values, option_string=None):

        # Variables are filter IDs, numbers
        number = pp.Word(pp.nums)  
        boolean_operator = pp.oneOf("NOT", caseless=True)

        # Define expression grammar using infixNotation
        boolean_expr = pp.infixNotation(
            number,
            [
                ("NOT", 1, pp.opAssoc.RIGHT),
            ],
        )

        try: 
            parsedList = boolean_expr.parse_string(values.upper(), parse_all=True).as_list()
        except pp.ParseException as pe:
            msg = "filter argument incorrect: '" + str(pe) + "'"
            raise argparse.ArgumentTypeError(msg)

        setattr(namespace, self.dest, parsedList)


# For argparse usage
# Used for correctly parsing the filter boolean expression
class FilterProcessor(argparse.Action):

    def __call__(self, parser, namespace, values, option_string=None):

        # Variables are filter IDs, numbers
        number = pp.Word(pp.nums)  
        boolean_operator = pp.oneOf("AND OR NOT", caseless=True)

        # Define expression grammar using infixNotation
        boolean_expr = pp.infixNotation(
            number,
            [
                ("NOT", 1, pp.opAssoc.RIGHT),  
                ("AND", 2, pp.opAssoc.LEFT),  
                ("OR", 2, pp.opAssoc.LEFT),   
            ],
        )

        try: 
            parsedList = boolean_expr.parse_string(values.upper(), parse_all=True).as_list()
        except pp.ParseException as pe:
            msg = "filter argument incorrect: '" + str(pe) + "'"
            raise argparse.ArgumentTypeError(msg)

        setattr(namespace, self.dest, parsedList)


# Converts the filter boolean expression into the correct WHERE statements for the query
def filter_recursive(operand):
    query_final = ""
    query_left = ""
    query_right = ""
    temp_operand = []
    operator = ""

    # Single operand case
    if len(operand) == 1:
        query_final = """Game.id IN (SELECT Game.id 
                                     FROM Game, HasFlag
                                     WHERE Game.id == HasFlag.game_id AND 
                                           HasFlag.flag_id == """ + str(operand) + " AND HasFlag.value == 1) "
    
    # NOT case
    elif len(operand) == 2:
        # NOT followed by a number like: ['NOT', operand]
        if len(operand[1]) == 1:
            query_final = """Game.id IN (SELECT Game.id 
                                         FROM Game, HasFlag
                                         WHERE Game.id == HasFlag.game_id AND 
                                               HasFlag.flag_id == """ + str(operand[1]) + " AND HasFlag.value == 0) "

        # NOT followed by a NOT like: ['NOT', ['NOT', operand]]
        elif len(operand[1]) == 2:
            query_final = filter_recursive(operand[1][1])

        # NOT followed by a structure of LEFT OPERAND RIGHT
        # Need to use De Morgan's law to properly manage the NOT structure
        # Example: ['NOT', [operand, 'AND', operand]]
        else:
            operator = "OR" if operand[1][1] == "AND" else "AND"
            temp_operand.append(['NOT', operand[1][0]])
            temp_operand.append(operator)
            temp_operand.append(['NOT', operand[1][2]])

            query_left = filter_recursive(temp_operand[0])
            query_right = filter_recursive(temp_operand[2])
            query_final = "(" + query_left + " " + str(temp_operand[1]) + " " + query_right + ")"

    # left+op+right general case
    elif len(operand) == 3:
        query_left = filter_recursive(operand[0])
        query_right = filter_recursive(operand[2])
        query_final = "(" + query_left + " " + str(operand[1]) + " " + query_right + ")"

    # Chain of left+op+right case
    else:
        for i in range(len(operand)):
            if i == 1:
               query_left = filter_recursive(operand[i-1])
               query_right = filter_recursive(operand[i+1])
               query_final = "(" + query_left + " " + str(operand[i]) + " " + query_right + ")"
            
            elif i % 2 == 1:
                query_right = filter_recursive(operand[i+1])
                query_final = "(" + query_final + " " + str(operand[i]) + " " + query_right + ")"

    return query_final