# gtrack - Game tracker
The goal is to filter and organize game's information, provided by the [ActivityWatch](https://github.com/ActivityWatch/activitywatch) time tracker, through an easy-to-use CLI application. After receiving the game's information, the print process allows to quickly obtain playtime's data for specific applications on specific time intervals.

All of the data provided to the program will be stored on a **SQLite** database, stored locally. A network connection is not required to run the program.

## Usage
The program reads the required information from **game list** and **bucket** files. The list of games has to be specified through a .csv file and has to contain properties of the application such as the name used for display and plotting and the executable name to link it to the tracking information. The full list of columns can be retrieved through the `--create-template` option. The buckets are files used to retrieve time data about processes. They are .json file that can be directly obtained through [ActivityWatch](https://github.com/ActivityWatch/activitywatch) or can be crafted for custom insertions. The `--create-template` option can be used to create a .json structure to aid in manually adding time data.

The location of the database is read from a configuration file, which has to be created and positioned inside the home directory of the user (`$HOME` or `%userprofile%`), thus avoiding an additional argument at every launch of the program. Two optional paths can be added to indicate the folders where game lists and buckets will be found. An example of the configuration file's content can be:
```
[Paths]
path_db = /path/to/the/database/file
path_data_game = /path/to/the/game/list/folder # optional
path_data_bucket = /path/to/the/bucket/folder  # optional
```

### Examples

To manually provide the program with a new list of processes to track or with a new bucket, the `insert` command can be used:
```
# To add a list of applications to the database
$ gtrack insert -t game -f /path/to/the/list

# To add a new bucket with tracking information to the database
$ gtrack insert -t bucket -f /path/to/the/bucket
```

To automatically search for new information to add in the folders specified inside the configuration file, the `scan` command can be used:
```
# To scan the files contained in the configuration file's folders
$ gtrack scan
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
- [ ] Add a `remove` option for games (currently, deleting and recreating the database is the only way to remove unwanted processes);
- [ ] Add more meaningful flags for games (for better filtering/plotting);
- [ ] Allow more print options;
- [ ] Plotting for statistics.
