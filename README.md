# gtrack - Game tracker
The purpose of this application is to provide a simple-to-use CLI interface to easily access and visualize videogame's playtime information tracked by [ActivityWatch](https://github.com/ActivityWatch/activitywatch). After defining which games have to be tracked and processing the bucket files of interest produced by the tracker application, the print process allows to quickly recover the time spent on specific games and on specific time intervals, while the plot process allows to graphically render those same information.

>[!IMPORTANT]
>All of the data provided to the program will be stored on a SQLite database, stored **locally**. A network connection is not required to run the program.

## Installation
To launch the program Python3 is required. You can download the latest version [here](https://www.python.org/downloads/), if you're using Windows, or through the package manager of your distribution. After the installation process is completed, or if you already have it on your system, you need to install the dependencies indicated in the [requirements.txt](./requirements.txt) file.

To make use of the application, clone the repository, enter the downloaded folder and use the `pip install .` command:
```
$ git clone https://github.com/bOhYee/gtrack.git 
$ cd gtrack
$ pip install .
```
You can now use the CLI application:
```
$ gtrack <command> <options>
```

Before launching the program though, a configuration file has to be created and positioned inside a `.gtrack` folder in the home directory of the user (`$HOME/.gtrack/config.ini` or `%userprofile%/.gtrack/config.ini`). This is used to specify the location of the SQLite database file, thus avoiding an additional, mandatory, argument at every launch of the program. Additional options can be provided to improve the efficacy of the `scan` operation. An example of the configuration file's content can be:
```
[Paths]
path_db = /path/to/the/database/file
path_data_game = /path/to/the/game/list/folder # optional: Folder where a .csv containing game information can be found for a quick insertion
path_data_bucket = /path/to/the/bucket/folder  # optional: Folder where buckets are stored for quick parsing their information

[Filters]
flag_list = flag_one, flag_two, ...            # optional: List of flag to further filter games during a print operation
```
The complete configuration file, listing all of the possible parameters to be configured, can be found [here](./config/config.ini).

## Usage
Before the program can process the bucket files, it requires a **list of games** to be defined, in order to filter the processes to be considered between the ones present inside the buckets themselves. The list can be defined manually, through the proposed guided procedure, or can be specified through a .csv file. The only requirement that every .csv needs to satisfy is the presence of two values on each row: the first to indicate the name to be used to display the application and a second one to provide the executable name to identify the related process. A ready-to-use file can be created via the `--create-template` option.

The **buckets** are .json files produced by [ActivityWatch](https://github.com/ActivityWatch/activitywatch) which contain time-related information on application usage. These are parsed to retrieve only the data on requested processes. In case custom data have to be taken into account, the `--create-template` can be used to create a .json structure to manually craft the bucket.

### Examples
To manually provide the program with a new list of processes to track or with a new bucket, the `add` command can be used:
```
# To add a list of applications to the database
$ gtrack add -t game -f /path/to/the/list

# To add a new bucket with tracking information to the database
$ gtrack add -t bucket -f /path/to/the/bucket
```

To automatically insert/update information inside the database, the `scan` command can be used, which reads the optional folders indicated inside the configuration file:
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
The print process allows for the usage of **filters** to select which entries are relevant for the current query. Filters are stored as TRUE / FALSE values within the database, allowing for boolean algebra to be used for furter restricing the shown output values. They need to be referred to using the FLAG_IDs on the relevant CLI arguments:
```
# Suppose three flags have been defined:
# - is_singleplayer (FLAG_ID: 1)
# - was_completed (FLAG_ID: 2)
# - has_platinum (FLAG_ID: 3)

# To filter the game list for applications that were both completed and got the platinum
$ gtrack print -f "2 AND 3"

# To filter the game list for applications that are multiplayer experiences
$ gtrack print -f "NOT 1"

# To filter the game list for applications that were completed but for which a platinum was not acquired
$ gtrack print -f "2 AND NOT 3"
```

Two different plots can be produced by the application, to graphically aid the visualization of the stored information: 
- `pot` (Playtime-over-Time graph): creates an **Horizontal Bar** chart which shows the titles on the y-axis and their total playtime over the x-axis;
- `mhot` (Mean-Hours-over-Time graph): creates a **Line** chart which shows the total hours spent daily on playing videogames over a range of dates.

To plot these information, the `plot` command can be used:
```
# To generate the Playtime-over-Time graph
$ gtrack plot -t pot

# To generate the Mean-Hours-over-Time graph:
$ gtrack plot -t mhot
```
