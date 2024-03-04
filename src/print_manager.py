from datetime import datetime
from tabulate import tabulate

from .utils import *
from .database_manager import *


# Interpretation layer for the PRINT mode
def print_data(parsed_args, connection, cursor):
    group_dates = parsed_args["print_daily"] or parsed_args["print_monthly"]
    query, args, headers = print_query_definition(args=parsed_args)

    if args:
        cursor.execute(query, args)
    else:
        cursor.execute(query)

    info = cursor.fetchall()
    print_data_cli(headers=headers, rows=info, group_dates=group_dates)


def print_query_definition(args):
    flag_verbose = args["print_verbose"]
    flag_daily = args["print_daily"]
    flag_monthly = args["print_monthly"]
    flag_total = args["print_total"]
    dates = args["date_print_default"]
    gids = args["id_print"]
    gname = args["name_print"]

    temp_conditions = ""
    print_query = ""
    query_args = None
    headers = ["game_id", "game_name"]

    # SELECT
    # If verbose is selected, more info taken from Game table
    if flag_verbose:
        print_query += "SELECT Game.*, "
        headers += ["game_exe", "game_status", "game_mult", "game_plat"]
    else:
        print_query += "SELECT Game.id, Game.display_name, "

    # If daily is selected, the day has to be printed
    if flag_daily:
        print_query += "strftime('%Y-%m-%d', Activity.date) as rel_day, SUM(Activity.playtime) as total_playtime "
        headers += ["day"]
    # If monthly is selected, the month has to be printed
    elif flag_monthly:
        print_query += "strftime('%Y-%m', Activity.date) as rel_month, SUM(Activity.playtime) as total_playtime "
        headers += ["month"]
    else:
        print_query += "SUM(Activity.playtime) as total_playtime "

    headers += ["playtime (HH:MM:SS)"]
    print_query += "FROM Game, Activity "

    # WHERE
    print_query += "WHERE Game.id == Activity.game_id "

    # If total is requested, date filter is not needed
    if not flag_total:
        print_query += "AND date(Activity.date, 'localtime') >= ? "

        # Date can also be unspecified
        if dates:
            if len(dates) == 2:
                print_query += "AND date(Activity.date, 'localtime') <= ? "
                query_args = (dates[0], dates[1],)

            else:
                query_args = (dates[0],)

        else:
            start_year = datetime.strftime(datetime(datetime.now().year, 1, 1), "%Y-%m-%d")
            query_args = (start_year,)

    # Manage game IDs
    if gids:
        for i in range(len(gids)):
            temp_conditions += "Game.id == " + str(gids[i]) + " "

            if i < len(gids) - 1:
                temp_conditions += "OR "

        print_query += "AND (" + temp_conditions + ") "

    # Manage game name search
    if gname:
        print_query += "AND Game.display_name LIKE '%" + gname + "%' "

    # GROUP BY
    # game_id is unique, should be enough for differentiating games
    print_query += "GROUP BY Game.id "

    if flag_daily:
        print_query += ", rel_day "
    elif flag_monthly:
        print_query += ", rel_month "

    # ORDER BY
    print_query += "ORDER BY "

    if flag_daily:
        print_query += "rel_day DESC, "
    elif flag_monthly:
        print_query += "rel_month DESC, "

    print_query += "total_playtime DESC"
    return [print_query, query_args, headers]


def print_data_cli(headers, rows, group_dates):
    ins_barriers = 0
    barriers = []

    # Convert playtimes into HH:MM form
    for i in range(len(rows)):
        # print(rows[i])
        tmp_tuple = list(rows[i])

        min, sec = divmod(tmp_tuple[-1], 60)
        h, min = divmod(min, 60)
        tmp_tuple[-1] = "{hours:02d}:{minutes:02d}:{seconds:02d}".format(hours=int(h), minutes=int(min),
                                                                         seconds=int(sec))
        rows[i] = tmp_tuple

        if group_dates and i < (len(rows) - 1) and rows[i][-2] != rows[i + 1][-2]:
            barriers.append(i + 1)

    # Add barriers
    for i in range(len(barriers)):
        rows.insert(barriers[i] + ins_barriers, ("",))
        ins_barriers += 1

    # Print information table
    print(tabulate(rows, headers=headers, tablefmt="fancy_outline"))
