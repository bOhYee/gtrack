import matplotlib as plt


def pie_graph(data):

    # Data to show
    labels = ["Hours played", "Total year's hours"]
    total_time_hours = round(total_time_played(data), 2)
    this_year_hours = (365 + calendar.isleap(datetime.now().year)) * 24

    # Pie chart configuration
    plt.style.use('_mpl-gallery-nogrid')
    x = [total_time_hours, this_year_hours - total_time_hours]
    colors = plt.get_cmap('Oranges')(np.linspace(0.2, 0.7, len(x)))

    fig = plt.figure(figsize=(5, 4))
    wedges, texts, autotexts = plt.pie(x, colors=colors, autopct="%1.2f%%", textprops={"fontsize" : 12}, wedgeprops={"linewidth" : 1, "edgecolor": "white"})
    plt.title('Total playtime')
    plt.legend(wedges, labels, loc="lower left")

    plt.axis('equal')
    plt.tight_layout()
    plt.show()


def playtime_graph(playtime_info):

    # Data to show
    date_range = []
    curr_date = datetime(datetime.now().year, 1, 1)
    for i in range(365 + calendar.isleap(datetime.now().year)):
        date_range.append(curr_date)
        curr_date = curr_date + timedelta(days=1)

    # Chart configuration
    plt.style.use("_mpl-gallery")
    fig = plt.figure(figsize=(7, 4))

    plt.plot(date_range, playtime_info)
    plt.gca().xaxis.set_major_locator(plt.matplotlib.dates.MonthLocator())
    plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b'))

    # Add labels and title
    plt.xlabel('Month')
    plt.ylabel('Hours')
    plt.title('Playtime over the year')

    plt.tight_layout()
    plt.show()