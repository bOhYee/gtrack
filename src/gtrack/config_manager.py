import configparser
from gtrack import utils

# Read configuration file
def read_config_file():
    config = configparser.ConfigParser()

    flag_list = None
    path_db = utils.DB_PATH + "/data.db"
    path_data_game = None
    path_data_bucket = None
    bucket_options = {}
    bucket_options["save_thres"] = utils.SAVE_ACT_THRESHOLD
    bucket_options["diff_thres"] = utils.DIFF_ACT_THRESHOLD
    res = {}

    try:
        config.read_file(open(utils.CONFIG_PATH + "/config.ini"))

        if "paths" in config:
            paths = config["paths"]

            path_db = str(paths["path_db"]) if "path_db" in paths else path_db
            path_data_game = str(paths["path_data_game"]) if "path_data_game" in paths else None
            path_data_bucket = str(paths["path_data_bucket"]) if "path_data_bucket" in paths else None

        if "bucket_options" in config:
            boptions = config["bucket_options"]

            bucket_options["save_thres"] = int(boptions["save_threshold"]) if "save_threshold" in boptions else utils.SAVE_ACT_THRESHOLD
            bucket_options["diff_thres"]  = int(boptions["diff_threshold"]) if "diff_threshold" in boptions else utils.DIFF_ACT_THRESHOLD

        if "filters" in config:
            flags = config["filters"]
            flag_list = str(flags["flag_list"]) if "flag_list" in flags else None

        res["Paths"] = (path_db, path_data_game, path_data_bucket)
        res["Filters"] = (flag_list, )
        res["BucketOptions"] = bucket_options

    except OSError:
        res["Paths"] = (path_db, None, None)
        res["Filters"] = (None, )
        res["BucketOptions"] = bucket_options

    return res