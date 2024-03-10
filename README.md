# gtrack - Game tracker
The goal is to filter and organize game's information, provided by the [ActivityWatch](https://github.com/ActivityWatch/activitywatch) time tracker, through an easy-to-use CLI application. After receiving the game's information, the print process allows to quickly obtain playtime's data for specific applications on specific time intervals.

All of the data provided to the program will be stored on a **SQLite** database, stored locally. A network connection is not required to run the program.

## Usage
The program reads the required information from **game list** and **bucket** files. The list of games has to be specified through a .csv file and has to contain properties of the application such as the name used for display and plotting and the executable name to link it to the tracking information. The full list of columns can be retrieved through the `--create-template` option. The buckets are files used to retrieve time data about processes. They are .json file that can be directly obtained through ActivityWatch or can be crafted for custom insertions. The `--create-template` option can be used to create a .json structure to aid in manually adding time data.

To provide the program with a new list of processes to track or with a new bucket, the `insert` command can be used:
```
# To add a list of applications to the database
$ gtrack insert -t game -f /path/to/the/list

# To add a new bucket with tracking information to the database
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

## To-Do
The program still misses some key features and requires some constraints to be satisfied in order to work properly. They will, hopefully, be resolved in time. The full list is:
- [ ] in the same location where the program will be executed, a `data` folder is required to store the database;
- [ ] configuration files for indicating DB or data locations automatically;
- [ ] once a game is inserted, no method is available to remove it other than deleting the database itself and recreating it;
- [ ] additional print options for filtering based on some flag/detail;
- [ ] plotting functions.
