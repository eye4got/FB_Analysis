from typing import *

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tabulate import tabulate


class Person:

    def __init__(self, name: str):
        self.name = name
        self.convoSides = []


class Convo:
    count_cols = {
        "sender_name": "Messages",
        "photos": "Photos",
        "share_link": "Links",
        "sticker_path": "Stickers",
        "call_duration": "Successful Calls",
        "videos": "Videos",
        "audio_files": "Voice Memos",
        "gifs": "GIFs",
    }

    def __init__(self, name: str, speakers: Dict[str, Person], is_active: bool, is_group: bool,
                 messages_df: pd.DataFrame):
        self.convo_name = name
        self.speakers = speakers
        self.start_time = messages_df.index[0]
        self.is_active = is_active
        self.is_group = is_group
        self.msg_count = messages_df.count()
        self.msgs_df = messages_df
        self.top_speakers = None

        # For group chats with >X speakers, identify the X highest contributors for high-level visualisations
        # TODO: re-evaluate whether the number should be so hardcoded?
        if len(speakers) > 5:
            grouped_counts = self.msgs_df.groupby("sender_name").size()
            # Take index (sender_name) of top X speakers
            speaker_keys = grouped_counts.sort_values(ascending=False).head(5).index.values
            self.top_speakers = {key: self.speakers[key] for key in speaker_keys}

        # Add categorical hour of day column
        self.msgs_df['hour_of_day'] = self.msgs_df.index.map(lambda x: x.hour)

    def __str__(self) -> str:  # TODO: see if there are neater ways to output strings
        output = 'Conversation Name: ' + self.convo_name + '\n'
        output += 'Participants: ' + ', '.join(self.speakers.keys()) + '\n\n'

        subset_cols = ["sender_name", "photos", "share_link", "sticker_path", "call_duration", "videos",
                       "files", "audio_files", "missed_call", "gifs"]
        reaction_cols = [x for x in self.msgs_df.columns if "_reaction" in x]
        subset_cols.extend(reaction_cols)

        # Media Columns have counts of elements per message, need to sum these instead of counting
        media_cols = ["photos", "videos", "audio_files", "files"]
        agg_method = {}
        for col in subset_cols:
            agg_method[col] = ["count"] if col not in media_cols else ["sum"]

        # Apply aggregation methods determined by above dict
        counts_df = self.msgs_df[subset_cols].groupby("sender_name").agg(agg_method)

        counts_df['call_duration'] -= counts_df['missed_call']  # Remove calls with 0 duration

        # Collapse multi-index columns, rename using class field dictionary and prettified reaction cols
        cleaned_reaction_cols = [x.replace("_", " ").title() for x in reaction_cols]
        renamed_count_cols = {**Convo.count_cols, **dict(zip(reaction_cols, cleaned_reaction_cols))}

        counts_df.columns = counts_df.columns.get_level_values(0)
        counts_df.rename(columns=renamed_count_cols, inplace=True)

        output += tabulate(counts_df, headers=counts_df.columns)

        return output

    def create_msg_time_hist(self) -> plt.Figure:

        # If there is a shortlist of speakers use that (keeps visualisation manageable), otherwise use speakers
        speaker_subset = self.top_speakers if self.top_speakers is not None else self.speakers
        subset_msgs_df = self.msgs_df[self.msgs_df['sender_name'].isin(speaker_subset.keys())]

        # Find the msg counts for each sender, for each hour. Rename columns and fill in the blanks
        hours_series = subset_msgs_df.groupby(['sender_name', 'hour_of_day']).size().unstack(fill_value=0)
        hours_series.columns = [str(x) + ":00" for x in hours_series.columns]
        hours_series = hours_series.reindex([str(x) + ":00" for x in range(24)], axis=1, fill_value=0)
        hours_series.sort_index()

        # Create hourly labels for time histogram, 2D array to match shape of series
        hist_hours = [hours_series.columns for x in range(len(speaker_subset))]

        # Use np.arrange and -0.5 to create bins centred on labels
        histogram = plt.figure(figsize=(14, 8))
        plt.hist(hist_hours, bins=np.arange(25) - 0.5, weights=hours_series.T, alpha=0.5)
        plt.legend(sorted([side.name for side in speaker_subset.values()]), loc='upper left')
        plt.title("Histogram of Frequencies of Messages by Sender and Hour of the Day for " + self.convo_name)
        plt.show()

        return histogram

    # def create_timeline_hist(self) -> plt.Figure:
    #     convo_sides_list = list(self.convo_sides.values())
    #
    #     histogram = plt.figure(figsize=(14, 8))
    #     msg_times = [side.multi_msg_counts for side in convo_sides_list]
    #     plt.hist([side.multi_msg_counts for side in convo_sides_list])
    #     plt.legend([side.person.name for side in convo_sides_list], loc='upper left')
    #
    #     return histogram


class User:

    def __init__(self, name: str, root_path: str):
        self.name = name
        self.root_path = root_path
        self.convos = dict()
        self.persons = dict()

    def get_or_create_persons(self, name_list: List[str]) -> Dict[str, Person]:

        # FIXME: Remove user from speakers?
        selected_persons = dict()

        for person in name_list:
            if not person in self.persons:
                self.persons[person] = Person(person)
            # Extract instances of person for assignment to avoid instance
            # duplication
            selected_persons[person] = self.persons[person]

        # TODO: Overall summary stats (e.g. convo starting)

        return selected_persons
