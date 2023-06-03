import datetime
import logging
import os
import warnings
from typing import *

import bar_chart_race as bcr
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


def create_bcr_top_convo_animation(agg_msg_count_df: pd.DataFrame, top_n: int, output_path: str, format_desc: str):
    logging.info("Starting Racing Bar Chart Rendering")

    # FIXME: Gross warnings filter to suppress UserWarnings for Missing Glyphs in font
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        bcr.bar_chart_race(
            df=agg_msg_count_df,
            filename=os.path.join(output_path, 'fb_top_messages_history.mp4'),
            orientation='h',
            sort='desc',
            n_bars=top_n,
            fixed_order=False,
            fixed_max=True,
            interpolate_period=False,
            label_bars=True,
            bar_size=.95,
            period_label={'x': .99, 'y': .25, 'ha': 'right', 'va': 'center'},
            period_fmt='%B %d, %Y',
            period_summary_func=lambda v, r: {'x': .99, 'y': .18,
                                              's': f'Total char in period: {v.nlargest(top_n).sum():,.0f} \n'
                                                   f'Concentration of char in top 10: {v.nlargest(top_n).sum() / v.sum():.1%}',
                                              'ha': 'right', 'size': 8, 'family': 'Courier New'},
            perpendicular_bar_func='median',
            figsize=(7, 4),
            dpi=144,
            cmap='dark12',
            title=f'Average Characters Sent/Received on FB Messenger {format_desc}',
            title_size='',
            bar_label_size=7,
            tick_label_size=7,
            scale='linear',
            fig=None,
            bar_kwargs={'alpha': .7},
            filter_column_colors=False
        )
    logging.debug("Finished Rendering")
