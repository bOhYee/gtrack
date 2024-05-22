# gtrack - Game tracker
The purpose of this application is to provide a simple-to-use CLI interface to easily access and visualize videogame's playtime information tracked by [ActivityWatch](https://github.com/ActivityWatch/activitywatch). After defining which games have to be tracked and processing the bucket files of interest, the print process allows to quickly recover the time spent on specific applications and on specific time intervals.

>[!IMPORTANT]
>All of the data provided to the program will be stored on a SQLite database, stored **locally**. A network connection is not required to run the program.

## Installation
To launch the program Python3 is required. You can download the latest version [here](https://www.python.org/downloads/), if you're using Windows, or through the package manager of your distribution. After the installation process is completed, or if you already have it on your system, you need to install the dependencies indicated in the [requirements.txt](./requirements.txt) file.

Currently, an installation method is not provided. To make use of the application, clone the repository and execute the gtrack module using the python3 command:
```
$ git clone https://github.com/bOhYee/gtrack.git 
$ cd gtrack/src
$ python3 -m gtrack.gtrack <command> <options>
```

Before launching the program though, a configuration file has to be created and positioned inside a `.gtrack` folder in the home directory of the user (`$HOME/.gtrack/config.ini` or `%userprofile%/.gtrack/config.ini`). This is used to specify the location of the .db file, thus avoiding an additional, mandatory, argument at every launch of the program. Additional options can be provided to improve the efficacy of the `scan` operation. An example of the configuration file's content can be:
```
[Paths]
path_db = /path/to/the/database/file
path_data_game = /path/to/the/game/list/folder # optional: Folder where a .csv containing game information can be found for a quick insertion
path_data_bucket = /path/to/the/bucket/folder  # optional: Folder where buckets are stored for quick parsing their information

[Filters]
flag_list = flag_one, flag_two, ...            # optional: List of flag to further filter games during a print operation
```

## Usage
Before the program can process the bucket files, it requires a **list of games** to be defined, in order to filter the processes to be considered between the ones present inside the buckets themselves. The list can be defined manually, through the proposed guided procedure, or can be specified through a .csv file. The only requirement that every .csv needs to satisfy is the presence of two values on each row: the first to indicate the name to be used to display the application and a second one to provide the executable name to identify the related process. A ready-to-use file can be created via the `--create-template` option.

The **buckets** are .json files produced by [ActivityWatch](https://github.com/ActivityWatch/activitywatch) which contain time-related information on application usage. These are parsed to retrieve only the data on requested processes. In case custom data have to be taken into account, the `--create-template` can be used to create a .json structure to manually craft the bucket.

### Examples

To manually provide the program with a new list of processes to track or with a new bucket, the `add` command can be used:
```
# To add a list of applications to the database
$ python3 -m gtrack.gtrack add -t game -f /path/to/the/list

# To add a new bucket with tracking information to the database
$ python3 -m gtrack.gtrack add -t bucket -f /path/to/the/bucket
```

To automatically insert/update information inside the database, the `scan` command can be used, which reads the optional folders indicated inside the configuration file:
```
# To scan the files contained in the configuration file's folders
$ python3 -m gtrack.gtrack scan
```

To print playtime's information, the `print` command can be used:
```
# To print the total playtime for the current year of each process
$ python3 -m gtrack.gtrack print

# To print information about the tracked games
$ python3 -m gtrack.gtrack print -v

# To print the total playtime of a single process for a specific time interval
$ python3 -m gtrack.gtrack print -gid GAME_ID -d START_DATE [END_DATE]
```

## To-Do
- [ ] More flexible use of filters (AND/OR-TRUE/FALSE);
- [ ] Add plot creation for generating statistics.
