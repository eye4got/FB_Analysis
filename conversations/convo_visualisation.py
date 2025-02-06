import datetime
import logging
import warnings
from typing import *

import bar_chart_race as bcr
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from mplcursors import cursor


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


def create_bcr_top_convo_animation(agg_msg_count_df: pd.DataFrame, top_n: int, frame_length: int, output_path: str,
                                   format_desc: str):
    logging.info("Starting Racing Bar Chart Rendering")

    # FIXME: Gross warnings filter to suppress UserWarnings for Missing Glyphs in font
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        bcr.bar_chart_race(
            df=agg_msg_count_df,
            filename=output_path,
            orientation='h',
            sort='desc',
            n_bars=top_n,
            fixed_order=False,
            fixed_max=True,
            interpolate_period=True,
            label_bars=True,
            bar_size=.95,
            period_label={'x': .99, 'y': .25, 'ha': 'right', 'va': 'center'},
            period_fmt='%B %d, %Y',
            period_summary_func=lambda v, r: {'x': .99, 'y': .18,
                                              's': f'Total char in period: {v.nlargest(top_n).sum():,.0f} \n'
                                                   f'Concentration of char in top 10: {v.nlargest(top_n).sum() / v.sum():.1%}',
                                              'ha': 'right', 'size': 8}, #, 'family': 'Courier New'
            perpendicular_bar_func='median',
            figsize=(8, 4),
            dpi=144,
            cmap='gist_ncar',
            title=f'Avg Characters Exchanged on FB Messenger {format_desc}',
            title_size='12',
            bar_label_size=7,
            tick_label_size=7,
            scale='linear',
            fig=None,
            bar_kwargs={'alpha': .7},
            filter_column_colors=True,
            period_length=frame_length
        )
    logging.info("Finished Rendering")


def create_sentiment_dist_comparison(user_df: pd.DataFrame, receiver_df: pd.DataFrame, convo_name: str, user_name: str,
                                     fields: List[str]) -> plt.Figure:
    # Check that fields have been provided and they exist within the dataframe
    extra_fields = set(fields).difference(set(user_df.columns)).union(set(fields).difference(set(receiver_df.columns)))
    if len(fields) == 0:
        raise ValueError("Cannot generate sentiment distributions without selecting fields to score sentiment by")

    if len(extra_fields) > 0:
        raise ValueError(
            f"fields variable must only contain columns in the dataframe, the following were not found: {extra_fields}")

    fig, axs = plt.subplots(len(fields), 2, sharey='all', sharex='all', figsize=(16, 10))
    # Flatten axes to allow 1d indexing in case of 1d or 2d subplot struture (only one field submitted)
    fltn_axes = axs.flatten()

    fltn_axes[0].set_title("User Messaging Behaviour", fontfamily='serif', loc='center', fontsize='medium')
    fltn_axes[1].set_title("Other Speakers Messaging Behaviour", fontfamily='serif', loc='center', fontsize='medium')

    for ii, field in enumerate(fields):
        user_axes = fltn_axes[2 * ii]
        sns.kdeplot(user_df, x=field, hue="user_cat", common_norm=False, ax=user_axes)
        user_axes.legend(labels=[user_name, "Population"], title="")
        user_axes.set_xlabel(f"{field} tone score [0-1]")

        receiver_axes = fltn_axes[2 * ii + 1]
        sns.kdeplot(receiver_df, x=field, hue="receiver_cat", common_norm=False, ax=receiver_axes)
        receiver_axes.legend(labels=[convo_name, "Population"], title="")
        receiver_axes.set_xlabel(f"{field} tone score [0-1]")

    fig.tight_layout()
    plt.close()

    return fig


def create_sentiment_quadrant_graph(means_df: pd.DataFrame, title: str):
    sns.set_context("notebook", font_scale=2, rc={"lines.markersize": 10})
    fig = plt.figure()
    plot = sns.scatterplot(means_df, x='pos', y='neg', hue="name_gender", )
    plot.set_title(title)
    plot.set_xlabel("Positive Sentiment [0-1]")
    plot.set_ylabel("Negative Sentiment [0-1]")
    # FIXME: Difficult to read the small font but I have wasted too much time trying to make it bigger
    cursor(hover=True).connect("add", lambda sel: sel.annotation.set_text(means_df['name'].iloc[sel.index]))
    fig.set_size_inches(16, 8)

    sns.reset_defaults()

    return fig
