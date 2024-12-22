from datetime import datetime
from gtrack import utils
import plotly.graph_objects as go

def plot_data(parsed_args, plot_options, connection, cursor):
    plot_type = parsed_args["plot_choice"]
    plot_color = parsed_args["color_filter_plot"]
    plot_query = ""
    plot_query_args = ""
    color_data = None

    # Create the query for the different plots
    if plot_type == "pot":
        plot_query = """SELECT Game.id, Game.display_name, SUM(Activity.playtime) as playtime
                        FROM Game, Activity
                        WHERE Game.id == Activity.game_id """
    
        date_filter_query, plot_query_args = plot_date_filtering(parsed_args)
        plot_query += date_filter_query
        plot_query += "GROUP BY Game.id "
        plot_query = plot_flag_filtering(parsed_args, plot_query)

        # Ascendent order since the plot places the first item at the bottom
        plot_query += "ORDER BY playtime ASC "  

        # Recover the IDs of the games that needs to be highlighted due to the chosen flag
        if plot_color:
            plot_color_query = """SELECT Game.id 
                                  FROM Game
                                  WHERE """ + utils.filter_recursive(plot_color[0]) + """
                                  GROUP BY Game.id """

    elif plot_type == "mhot":
        plot_query = """WITH RECURSIVE dates(date) AS (
                            VALUES(?)
                            UNION ALL
                            SELECT date(date, '+1 day')
                            FROM dates
                            WHERE date < ?
                        ) """
        
        if parsed_args["filter_plot"]:
            filter_plot = parsed_args["filter_plot"]
            plot_subquery = """SELECT Activity.game_id, Activity.date, Activity.playtime
                               FROM Activity INNER JOIN (SELECT Game.id
                                                         FROM Game
                                                         WHERE """ + utils.filter_recursive(filter_plot[0]) + ") AS SUB ON Activity.game_id == SUB.id "
            

            plot_query += "SELECT dates.date, IFNULL(SUM(ACT_SUB.playtime), 0) "
            plot_query += "FROM dates LEFT JOIN (" + plot_subquery + ") AS ACT_SUB ON (dates.date == strftime('%Y-%m-%d', ACT_SUB.date)) "
            plot_query += "GROUP BY dates.date "

        else:
            plot_query += """SELECT dates.date, IFNULL(SUM(Activity.playtime), 0) 
                             FROM dates LEFT JOIN Activity ON (dates.date == strftime('%Y-%m-%d', Activity.date))
                             GROUP BY dates.date """
        
        plot_query_args = plot_period_filtering(parsed_args, connection, cursor)

    # Execute the query
    if plot_query_args: 
        cursor.execute(plot_query, plot_query_args)
    else:
        cursor.execute(plot_query)

    data = cursor.fetchall()
    if plot_color:
        cursor.execute(plot_color_query)
        color_data = cursor.fetchall()

    # Plot the retrieved data
    if plot_type == "pot":
        plot_games_wplaytime(data, color_data, plot_options["PoT"])
    elif plot_type == "mhot":
        plot_mean_over_time(data, plot_options["MHoT"])


# Manages dates filter and flag usage
# Structure similar to that used within the print methods
def plot_date_filtering(args):
    flag_total = args["plot_total"]
    dates = args["date_plot_default"]
    date_filter_query = ""

    # If total is requested, date filter is not needed 
    if not flag_total:
        date_filter_query += "AND date(Activity.date, 'localtime') >= ? "

        # Date can also be unspecified
        if dates:
            if len(dates) == 2:
                date_filter_query += "AND date(Activity.date, 'localtime') <= ? "
                query_args = (dates[0], dates[1],)

            else:
                query_args = (dates[0],)

        else:
            start_year = datetime.strftime(datetime(datetime.now().year, 1, 1), "%Y-%m-%d")
            query_args = (start_year,)

    return [date_filter_query, query_args]


# Manages date filter when two dates are required 
def plot_period_filtering(args, connection, cursor):
    flag_total = args["plot_total"]
    dates = args["date_plot_default"]
    period_query = ""
    query_args = ()

    if not flag_total:
        if dates:
            query_args = (dates[0], dates[1],)
        else:
            start_year = datetime.strftime(datetime(datetime.now().year, 1, 1), "%Y-%m-%d")
            end_year = datetime.strftime(datetime(datetime.now().year, 12, 31), "%Y-%m-%d")
            query_args = (start_year, end_year)
    
    else: 
        # Need to recover the information about the overall stored period of time
        period_query = """SELECT MIN(strftime('%Y-%m-%d', Activity.date)) as start_date, MAX(strftime('%Y-%m-%d', Activity.date)) as end_date
                          FROM Activity """
        
        cursor.execute(period_query)
        dates = cursor.fetchall()
        query_args = dates[0]

    return query_args


# Manages flag filtering to restric plot to specific games
def plot_flag_filtering(args, query):
    filter_flag = args["filter_plot"]
    filter_query = ""

    if filter_flag:
        filter_query = """SELECT Game.id, Game.display_name, SUB.playtime 
                          FROM Game INNER JOIN (""" + query + """) as SUB ON Game.id == SUB.id 
                                    INNER JOIN HasFlag ON Game.id == HasFlag.game_id """

        filter_query += "WHERE " + utils.filter_recursive(filter_flag[0]) + " "
        filter_query += "GROUP BY Game.id "
        query = filter_query

    return query


# Plots the list of games, sorted by decreasing playtime, with their respective amount of played hours
def plot_games_wplaytime(data, color_data, options):
    x_data = []
    y_data = []
    marker_colors = []
    annotations = []

    xtitle_font_size = options["xtitle"]
    ytitle_font_size = options["ytitle"]
    xlabel_font_size = options["xlabel"]
    ylabel_font_size = options["ylabel"]
    bar_font_size = options["bar"]

    # Need to:
    # - extract Xs and Ys from the recovered data
    # - determine the bar color if a filter was specfied
    # - convert the playtime value to HH only
    annotations = []
    for i in range(len(data)):  
        if color_data:
            to_color = False
            for l in color_data:
                if data[i][0] == l[0]:
                    to_color = True
                    break
        
            if to_color:
                marker_colors.append("#EBCB8B")
            else:
                marker_colors.append("#BF616A")

        else:
            marker_colors.append("#BF616A")

        x_data.append(round(data[i][2] / 3600, 2))
        y_data.append(data[i][1])
        annotations.append(dict(xref='paper', yref='y',
            x=0.135, y=data[i][1],
            xanchor='right',
            text=str(data[i][1]),
            font=dict(family='Arial', size=14, color="#ECEFF4"),
            showarrow=False, align='right'))
                
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x_data, y=y_data, 
        orientation='h', 
        hoverinfo='none',
        text=x_data,
        textposition="outside",
        textfont=dict(size=bar_font_size, color="#ECEFF4"),
        marker=dict(color=marker_colors, line=dict(color=marker_colors))
    ))

    fig.update_layout(
        xaxis=dict(
            title=dict(text="Playtime (hours)", font=dict(size=xtitle_font_size, color="#ECEFF4")), 
            color="#ECEFF4",
            gridcolor="#4C566A",
            linecolor="#ECEFF4",
            linewidth=2, 
            domain=[0.14, 1], 
            tickfont=dict(size=xlabel_font_size)
        ), 
        yaxis=dict(
            title=dict(text="Games", standoff=275, font=dict(size=ytitle_font_size, color="#ECEFF4")), 
            color="#ECEFF4",
            gridcolor="#4C566A",
            linecolor="#ECEFF4",
            linewidth=2, 
            showticklabels=False,
            tickfont=dict(size=ylabel_font_size)
        ),
        margin=dict(t=40),
        paper_bgcolor="#2E3440",
        plot_bgcolor="#434C5E",
        annotations=annotations
    )

    fig.show()


# Plots the hours of playtime over a specific period of time
def plot_mean_over_time(data, options):
    x_data = []
    y_data = []

    # Need to extract Xs and Ys from the recovered data
    # Playtime also needs to be converted in a HH value
    for i in range(len(data)):
        x_data.append(data[i][0])
        y_data.append(round(((data[i][1]) / 3600), 2))

    ytitle_font_size = options["ytitle"]
    xlabel_font_size = options["xlabel"]
    ylabel_font_size = options["ylabel"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_data, y=y_data,
        mode="lines",
        name="lines",
        marker=dict(color="#BF616A"),
        hovertemplate="%{x|%d %B %Y}, %{y:.2f}<extra></extra>"
    ))

    fig.update_layout(
        xaxis=dict(
            rangeslider=dict(visible=True),
            tickfont=dict(size=xlabel_font_size),
            tickformatstops = [
                dict(dtickrange=[None, 604800000], value="%e %B"),
                dict(dtickrange=[604800000, 2419200000], value="%e %B"),
                dict(dtickrange=["M1", "M12"], value="%B %Y"),
                dict(dtickrange=["M12", None], value="%Y Y")
            ],
            color="#ECEFF4",
            gridcolor="#626B7D",
            linecolor="#ECEFF4",         
            linewidth=2,
        ),
        yaxis=dict(
            title=dict(text="Hours", standoff=40, font=dict(color="#ECEFF4", size=ytitle_font_size)),
            tickfont=dict(size=ylabel_font_size),
            color="#ECEFF4",
            gridcolor="#626B7D",
            linecolor="#ECEFF4",
            linewidth=2,
            ticksuffix=" ",
        ),
        paper_bgcolor="#2E3440",
        plot_bgcolor="#434C5E",
        margin=dict(l=120, r=120)
    )

    fig.show()