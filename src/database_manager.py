import sqlite3
from datetime import datetime as dt
from sqlite3 import Error


# Database location path
DB_PATH = "data/project.db"


# Creates the tables 'game' and 'activity' inside the database if they aren't alread present
def create_tables(cursor):

    query_game = """ CREATE TABLE IF NOT EXISTS Game (
                        id INTEGER PRIMARY KEY,
                        display_name VARCHAR(50) NOT NULL,
                        executable_name VARCHAR(50) NOT NULL,
                        status INT NOT NULL,
                        is_multiplayer INT NOT NULL,
                        has_platinum INT NOT NULL
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


# Inserts an activity, pre-elaborated from the bucket, inside the table
def insert_activity(gid, dt, playtime, cursor):

    playtime = round(playtime, 3)

    # Verify that the data doesn't exist
    search_query = """ SELECT COUNT(*)
                       FROM Activity
                       WHERE game_id = ? AND date = ? """
    
    search_data = (gid, dt)
    cursor.execute(search_query, search_data)
    if cursor.fetchone()[0] == 1:
        return 1
    
    i_data = (gid, dt, playtime)
    i_query = """ INSERT INTO Activity (game_id, date, playtime)
                  VALUES (?, ?, ?) """

    cursor.execute(i_query, i_data)
    return 0