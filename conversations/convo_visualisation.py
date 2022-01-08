import datetime
from typing import *

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# -*- coding: utf-8 -*-

def create_msg_time_hist(hours_series: pd.DataFrame, convo_name: str) -> plt.Figure:
    """
    Creates a plot which shows the frequency of msgs for each hour of the day and speaker.
    :param hours_series: A dataframe with each row as hours of the day, and each column a new speaker
    :param convo_name: A string, containing the name of the conversation
    :return: A Matplotlib figure of time of the day message frequency
    """

    if len(hours_series.shape) != 2 or hours_series.shape[0] != 24 or hours_series.shape[1] < 1:
        raise ValueError("hours series must have shape (x, 24), and x > 0")

    # Create hourly labels for time histogram, 2D array to match shape of series
    hist_hours = [[str(x) + ":00" for x in range(24)] for y in range(hours_series.shape[1])]

    # Use np.arrange and -0.5 to create bins centred on labels
    histogram = plt.figure(figsize=(14, 8))
    plt.hist(hist_hours, bins=np.arange(25) - 0.5, weights=hours_series)
    plt.legend([x for x in hours_series.columns], loc="upper left")

    plt.title(f"Histogram of Characters Sent by Hour of the Day and Sender for {convo_name}")
    plt.close()

    return histogram


def create_timeline_hist(convo_name: str, msgs_df: pd.DataFrame, speakers: List[str]) -> plt.Figure:
    """
    Creates a histogram of character counts sent by each user every 3 days for the entire history of the conversation
    :param convo_name: Name of conversation. To be included in the title
    :param msgs_df: A dataframe containing all the messages of the conversation
    :param speakers: A list of the speakers names to include in the legend
    :return:
    """

    # Calculate sums of message character counts for each week for each sender
    weekly_counts = msgs_df.groupby("sender_name").resample("W")["text_len"].sum()

    fig, axs = plt.subplots(len(speakers), 1, figsize=(16, 8))
    fig.suptitle("Weekly Histogram of Character Counts for " + convo_name)

    for ii, speaker in enumerate(speakers):
        bins = weekly_counts[speaker].index - datetime.timedelta(3)
        axs[ii].hist(weekly_counts[speaker].index, bins=bins, weights=weekly_counts[speaker].values, alpha=0.8)
        axs[ii].set_xlabel(speaker)
        axs[ii].grid(True)

    axs[len(speakers) - 1].set_title("Time")
    fig.tight_layout()
    plt.close()

    return fig
