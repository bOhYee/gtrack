from tabulate import tabulate


# Interpretation layer for the CONFIG command
def config_data(parsed_args, connection, cursor):
    err = None

    if parsed_args["config_list"]:
        list_flags(connection, cursor)

    elif parsed_args["config_add"]:
        err = add_flag(parsed_args["config_add"], connection, cursor)

    elif parsed_args["config_rm"]:
        remove_flag(parsed_args["config_rm"], connection, cursor)
        
    return err


# Add a new option flag in the Flag table and associates every game with it
def add_flag(flag_name, connection, cursor):
    err = None
    game_list = []
    
    # Check that the new option isn't a duplicate
    duplicates_query = "SELECT * FROM Flag WHERE name = ?"
    query_data = (flag_name, )
    cursor.execute(duplicates_query, query_data)

    if len(cursor.fetchall()) >= 1:
        err = "WARNING: flag " + str(flag_name) + " could not be added due to being already present"
    else:
        # Insert option flag
        insert_query = "INSERT INTO Flag (name) VALUES (?)"
        cursor.execute(insert_query, query_data)
        
        insert_query = "SELECT id FROM Flag WHERE name = ?"
        cursor.execute(insert_query, query_data)
        flag_id = cursor.fetchall()[0][0]
        
        # Associate to every game with a false starting value
        game_query = "SELECT id FROM Game"
        cursor.execute(game_query)
        game_list = cursor.fetchall()
        
        associate_query = "INSERT INTO HasFlag (game_id, flag_id, value) VALUES (?, ?, ?)"
        for game in game_list:
            associate_data = (game[0], flag_id, 0, )
            cursor.execute(associate_query, associate_data)            

        connection.commit()

    return err


# List all flags
def list_flags(connection, cursor):

    s_query = """SELECT * 
                 FROM Flag """
    
    cursor.execute(s_query)
    rows = cursor.fetchall()
    print(tabulate(rows, headers=["flag_id", "flag_name"], tablefmt="fancy_outline"))
    return


# Remove the specified flag from all games and the Flag table
def remove_flag(flag_id, connection, cursor):

    data = (flag_id, )
    rm_query_hf = """DELETE FROM HasFlag 
                     WHERE flag_id = ? """
    
    rm_query_flag = """DELETE FROM Flag
                       WHERE id = ? """
    
    cursor.execute(rm_query_hf, data)
    cursor.execute(rm_query_flag, data)
    connection.commit()
    return


# Scan layer for flags insertion
def scan_flags(filters, connection, cursor):

    if filters is not None:
        flag_list = filters.split(",")

        print("Scanning flag list: " + str(flag_list))
        for flag in flag_list:
            if flag.strip() != "":
                add_flag(flag.strip(), connection, cursor)

        print("Insertion complete!\n")

    return