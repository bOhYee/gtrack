from datetime import datetime
from tabulate import tabulate
from gtrack import utils


# Interpretation layer for the PRINT mode
def print_data(parsed_args, connection, cursor):
    flag_list = []
    group_dates = parsed_args["print_daily"] or parsed_args["print_monthly"]

    # Headers for the flag columns
    if parsed_args["print_verbose"]:
        query = "SELECT name FROM Flag ORDER BY id ASC"
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            flag_list += [row[0]]

    query, args, headers = print_query_definition(args=parsed_args, flist=flag_list)
    if args:
        cursor.execute(query, args)
    else:
        cursor.execute(query)

    info = cursor.fetchall()
    print_data_cli(headers=headers, rows=info, flag_verbose=parsed_args["print_verbose"], group_dates=group_dates)


# Query defintion for recovering data from the DB
def print_query_definition(args, flist):
    flag_verbose = args["print_verbose"]
    flag_daily = args["print_daily"]
    flag_monthly = args["print_monthly"]
    flag_total = args["print_total"]
    dates = args["date_print_default"]
    filter_flag = args["filter_print"]
    gids = args["id_print"]
    gname = args["name_print"]

    temp_conditions = ""
    print_query = ""
    print_subquery = ""
    query_args = None
    headers = ["game_id", "game_name"]

    ### SELECT ###
    print_query += "SELECT Game.id, Game.display_name, "

    # If daily is selected, the day has to be printed
    if flag_daily:
        print_query += "strftime('%Y-%m-%d', Activity.date) as rel_day, "
        headers += ["day"]
    # If monthly is selected, the month has to be printed
    elif flag_monthly:
        print_query += "strftime('%Y-%m', Activity.date) as rel_month, "
        headers += ["month"]

    print_query += "SUM(Activity.playtime) as total_playtime "
    headers += ["playtime (HH:MM:SS)"]

    ### FROM ###
    print_query += "FROM Game, Activity "

    ### WHERE ###
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

    # If verbose is selected, GID and GNAME have to be managed on the join
    if not flag_verbose:
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

    # GROUP BY ###
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

    # VERBOSE or FILTERS: use the defined query as a subquery and create the outer query
    if flag_verbose or filter_flag:
        print_subquery = print_query
        print_sq_filters = ""
        print_date = ""

        if flag_verbose:
            headers = ["game_id", "game_name", "game_exe"] + flist + ["playtime"]
            if filter_flag:
                print_sq_filters = """SELECT HasFlag.game_id 
                                      FROM HasFlag 
                                      WHERE """
                
                for i in range(len(filter_flag)):
                    fid = filter_flag[i]
                    print_sq_filters += "(HasFlag.flag_id == " + str(fid) + " AND HasFlag.value == 1) "
                    if i < len(filter_flag) - 1:
                        print_query += "OR "

                print_query = """SELECT Game.*, HasFlag.value, SUB.total_playtime 
                                 FROM Game LEFT JOIN (""" + print_subquery + """) as SUB ON Game.id == SUB.id 
                                           INNER JOIN (""" + print_sq_filters + """) as SUBFILTERS ON Game.id == SUBFILTERS.game_id
                                           INNER JOIN HasFlag ON SUBFILTERS.game_id == HasFlag.game_id """
                
            else:
                print_query = """SELECT Game.*, HasFlag.value, SUB.total_playtime 
                                 FROM Game LEFT JOIN (""" + print_subquery + """) as SUB ON Game.id == SUB.id 
                                           INNER JOIN HasFlag ON Game.id == HasFlag.game_id """

            # Manage game IDs
            if gids:
                for i in range(len(gids)):
                    temp_conditions += "Game.id == " + str(gids[i]) + " "

                    if i < len(gids) - 1:
                        temp_conditions += "OR "

                print_query += "WHERE (" + temp_conditions + ") "

            # Manage game name search
            if gname:
                print_query += "WHERE Game.display_name LIKE '%" + gname + "%' "

            print_query += """GROUP BY Game.id, HasFlag.flag_id
                              ORDER BY Game.id ASC, HasFlag.flag_id ASC"""

        elif filter_flag:
            # Date information have to be reported on the outer query too
            if flag_daily:
                print_date = ", SUB.rel_day "
                
            elif flag_monthly:
                print_date = ", SUB.rel_month "

            print_query = """SELECT Game.id, Game.display_name""" + print_date + """, SUB.total_playtime 
                             FROM Game INNER JOIN (""" + print_subquery + """) as SUB ON Game.id == SUB.id 
                                       INNER JOIN HasFlag ON Game.id == HasFlag.game_id """
            
            print_query += "WHERE "
            for i in range(len(filter_flag)):
                fid = filter_flag[i]
                print_query += "(HasFlag.flag_id == " + str(fid) + " AND HasFlag.value == 1) "
                if i < len(filter_flag) - 1:
                    print_query += "OR "    

            # Manage game IDs
            if gids:
                temp_conditions = ""
                for i in range(len(gids)):
                    temp_conditions += "Game.id == " + str(gids[i]) + " "

                    if i < len(gids) - 1:
                        temp_conditions += "OR "

                print_query += "AND (" + temp_conditions + ") "

            # Manage game name search
            if gname:
                print_query += "AND Game.display_name LIKE '%" + gname + "%' "
            
            print_query += "GROUP BY Game.id "
            if flag_daily or flag_monthly:
                print_query += print_date
            
            print_query += "ORDER BY "
            if flag_daily or flag_monthly:
                print_query += print_date[2:] + "DESC, "

            print_query += "total_playtime DESC"
    
    return [print_query, query_args, headers]


# Table printing on CLI
def print_data_cli(headers, rows, flag_verbose, group_dates):
    ins_barriers = 0
    barriers = []
    print_rows = []

    # Convert duplicate rows due to flags into columns
    if flag_verbose:
        ogid = 0
        flags = []
        new_row = None

        for i in range(len(rows)):
            row = rows[i]

            # Starting game id
            if ogid == 0:
                ogid = row[0]

            # New game detected, save the previous one's values together with its flags
            if ogid != row[0]:
                print_rows.append(new_row)
                ogid = row[0]
                flags = []

            flags += ["X"] if row[3] == 1 else [""]
            new_row = tuple([row[0], row[1], row[2]] + flags + [row[len(row) - 1]])

            # Last cycle
            if i == len(rows) - 1:
                print_rows.append(new_row)               
    else:
        print_rows = rows

    # Convert playtimes into HH:MM form
    for i in range(len(print_rows)):
        tmp_tuple = list(print_rows[i])
        if tmp_tuple[-1] is None:
            continue

        min, sec = divmod(tmp_tuple[-1], 60)
        h, min = divmod(min, 60)
        tmp_tuple[-1] = "{hours:02d}:{minutes:02d}:{seconds:02d}".format(hours=int(h), minutes=int(min), seconds=int(sec))
        print_rows[i] = tmp_tuple

        if group_dates and i < (len(rows) - 1) and print_rows[i][-2] != print_rows[i + 1][-2]:
            barriers.append(i + 1)

    # Add barriers
    for i in range(len(barriers)):
        rows.insert(barriers[i] + ins_barriers, ("",))
        ins_barriers += 1

    # Print information table
    print(tabulate(print_rows, headers=headers, tablefmt="fancy_outline"))
