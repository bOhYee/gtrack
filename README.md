# gtrack - Game tracker
The goal is to filter and organize game's information, provided by the [ActivityWatch](https://github.com/ActivityWatch/activitywatch) time tracker, through an easy-to-use CLI application. After receiving the game's information, the print process allows to quickly obtain playtime's data for specific applications and specific time intervals.

## Usage
Every bit of information will be stored on a **SQLite** database, stored locally. No network communication will be performed by the program.

The program uses two types of file:
- a **csv** file, to recover game's information such as the name to use for display, the executable name for collecting time information through the buckets, the current status and some flags for further filtering;
- a **json** file, to recover the game's playtime data. It can be produced directly through the buckets' export process of the ActivityWatch GUI or it can be custom-made, by using a similar format.

To provide the program with a new list of processes to track or with a new bucket, the `insert` command can be used:
```
# To add a list of applications to the database
$ gtrack insert -t game -f /path/to/the/list

# To add a new bucket with tracking informations to the database
$ gtrack insert -t bucket -f /path/to/the/bucket
```

To print playtime's information, the `print` command can be used:
```
# To print the total playtime for the current year of each process
$ gtrack print

# To print information about the tracked games
$ gtrack print -v

# To print the total playtime of a single process for a specific time interval
$ gtrack print -gid GAME_ID -d START_DATE [END_DATE]
```

## Missing features
The program still misses some key features and requires some constraints to be satisfied in order to work properly:
- in the same location where the program will be executed, a `data` folder is required to store the database;
- configuration files for indicating DB or data locations automatically;
- once a game is inserted, no method is available to remove it other than deleting the database itself and recreating it.
