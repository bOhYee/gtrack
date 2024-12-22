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

    pot_options = {}
    pot_options["bar"] = utils.BAR_FONT_SIZE
    pot_options["xtitle"] = utils.LABEL_FONT_SIZE
    pot_options["xlabel"] = utils.TITLE_FONT_SIZE
    pot_options["ytitle"] = utils.LABEL_FONT_SIZE
    pot_options["ylabel"] = utils.TITLE_FONT_SIZE
    mean_over_time_options = {}
    mean_over_time_options["xlabel"] = utils.TITLE_FONT_SIZE
    mean_over_time_options["ytitle"] = utils.LABEL_FONT_SIZE
    mean_over_time_options["ylabel"] = utils.TITLE_FONT_SIZE

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

        if "plot:PoT" in config:
            poptions = config["plot:PoT"]

            pot_options["xtitle"] = int(poptions["xtitle_font_size"]) if "xtitle_font_size" in poptions else utils.TITLE_FONT_SIZE
            pot_options["xlabel"] = int(poptions["xlabel_font_size"]) if "xlabel_font_size" in poptions else utils.LABEL_FONT_SIZE
            pot_options["ytitle"] = int(poptions["ytitle_font_size"]) if "ytitle_font_size" in poptions else utils.TITLE_FONT_SIZE
            pot_options["ylabel"] = int(poptions["ylabel_font_size"]) if "ylabel_font_size" in poptions else utils.LABEL_FONT_SIZE
            pot_options["bar"]    = int(poptions["bartext_font_size"]) if "bartext_font_size" in poptions else utils.BAR_FONT_SIZE

        if "plot:MHoT" in config:
            mhotoptions = config["plot:MHoT"]

            mean_over_time_options["xlabel"] = int(mhotoptions["xlabel_font_size"]) if "xlabel_font_size" in mhotoptions else utils.LABEL_FONT_SIZE
            mean_over_time_options["ytitle"] = int(mhotoptions["ytitle_font_size"]) if "ytitle_font_size" in mhotoptions else utils.TITLE_FONT_SIZE
            mean_over_time_options["ylabel"] = int(mhotoptions["ylabel_font_size"]) if "ylabel_font_size" in mhotoptions else utils.LABEL_FONT_SIZE

        res["Paths"] = (path_db, path_data_game, path_data_bucket)
        res["Filters"] = (flag_list, )
        res["BucketOptions"] = bucket_options
        res["PoT"] = pot_options
        res["MHoT"] = mean_over_time_options

    except OSError:
        res["Paths"] = (path_db, None, None)
        res["Filters"] = (None, )
        res["BucketOptions"] = bucket_options
        res["PoT"] = pot_options
        res["MHoT"] = mean_over_time_options

    return res