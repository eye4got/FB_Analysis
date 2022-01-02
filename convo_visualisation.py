import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def create_msg_time_hist(hours_series: pd.DataFrame, convo_name: str) -> plt.Figure:
    if len(hours_series.shape) != 2 or hours_series.shape[0] != 24 or hours_series.shape[1] < 1:
        raise ValueError("hours series must have shape (x, 24), and x > 0")

    # Create hourly labels for time histogram, 2D array to match shape of series
    hist_hours = [[str(x) + ":00" for x in range(24)] for y in range(hours_series.shape[1])]

    # Use np.arrange and -0.5 to create bins centred on labels
    histogram = plt.figure(figsize=(14, 8))
    plt.hist(hist_hours, bins=np.arange(25) - 0.5, weights=hours_series)
    plt.legend([x for x in hours_series.columns], loc="upper left")

    plt.title("Histogram of Characters Sent by Hour of the Day and Sender for " + convo_name)
    plt.close()

    return histogram


def create_timeline_hist(self) -> plt.Figure:
    if self.top_speakers is None:
        speaker_subset = self.speakers
        subset_msgs_df = self.msgs_df
    else:
        speaker_subset = self.top_speakers
        subset_msgs_df = self.msgs_df[self.msgs_df["sender_name"].isin(speaker_subset.keys())]

    # Calculate sums of message character counts for each week for each sender
    weekly_counts = subset_msgs_df.groupby("sender_name").resample("W")["text_len"].sum()

    fig, axs = plt.subplots(len(speaker_subset.keys()), 1, figsize=(16, 8))
    fig.suptitle("Weekly Histogram of Character Counts for " + self.convo_name)

    for ii, speaker in enumerate(speaker_subset.keys()):
        bins = weekly_counts[speaker].index - timedelta(3)
        axs[ii].hist(weekly_counts[speaker].index, bins=bins, weights=weekly_counts[speaker].values, alpha=0.8)
        axs[ii].set_xlabel(speaker)
        axs[ii].grid(True)

    axs[len(speaker_subset.keys()) - 1].set_title("Time")
    fig.tight_layout()
    plt.close()

    return fig
