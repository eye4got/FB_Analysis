from typing import *

import pandas as pd
from django.utils.text import slugify
from tabulate import tabulate


class Person:

    def __init__(self, name: str):
        self.name = name

class Convo:
    count_cols = {
        "sender_name": "Messages",
        "text_len": "Character Count",
        "photos": "Photos",
        "call_duration": "Successful Calls",
        "missed_call": "Missed Calls",
        "videos": "Videos",
        "gifs": "GIFs",
        "files": "Files",
        "share_link": "Links",
        "sticker_path": "Stickers",
        "audio_files": "Voice Memos"
    }

    def __init__(self, name: str, speakers: Dict[str, Person], is_active: bool, is_group: bool,
                 messages_df: pd.DataFrame):
        self.convo_name = name
        self.cleaned_name = slugify(name)  # For file paths and similar restricted character sets
        self.speakers = speakers
        self.start_time = messages_df.index[0]
        self.is_active = is_active
        self.is_group = is_group
        self.msg_count = messages_df.shape[0]
        self.msgs_df = messages_df

        # Add categorical hour of day column
        self.msgs_df["hour_of_day"] = self.msgs_df.index.map(lambda x: x.hour)

        # Create character counts for each message
        self.msgs_df["text_len"] = self.msgs_df["text"].apply(lambda x: len(x) if type(x) == str else 0)

    def __str__(self) -> str:
        output = f"""Conversation Name: {self.convo_name}\n
                     Participants: {", ".join(self.speakers.keys())}\n\n"""

        subset_cols = ["sender_name", "text_len", "photos", "share_link", "sticker_path", "call_duration", "videos",
                       "files", "audio_files", "missed_call", "gifs"]
        reaction_cols = [x for x in self.msgs_df.columns if "_reaction" in x]
        subset_cols.extend(reaction_cols)

        # Media Columns have counts of elements per message, need to sum these instead of counting
        agg_method = {}
        media_cols = ["photos", "videos", "audio_files", "files", "text_len"]
        for col in subset_cols:
            agg_method[col] = ["count"] if col not in media_cols else ["sum"]

        # Apply aggregation methods determined by above dict
        counts_df = self.msgs_df[subset_cols].groupby("sender_name").agg(agg_method)

        counts_df["call_duration"] -= counts_df["missed_call"]  # Remove calls with 0 duration

        # Collapse multi-index columns, rename using class field dictionary and prettified reaction cols
        cleaned_reaction_cols = [x.replace("_", " ").title() for x in reaction_cols]
        renamed_count_cols = {**Convo.count_cols, **dict(zip(reaction_cols, cleaned_reaction_cols))}

        counts_df.columns = counts_df.columns.get_level_values(0)
        counts_df.rename(columns=renamed_count_cols, inplace=True)

        output += tabulate(counts_df, headers=counts_df.columns)

        return output

    def get_char_counts_by_hour(self) -> pd.DataFrame:
        """
        :return: A data frame containing the msg counts for each speaker (columns) for each hour of the day (rows)
        """

        # Find the msg counts for each sender, for each hour. Rename columns and fill in the blanks
        hours_series = self.msgs_df.groupby(["sender_name", "hour_of_day"]).size().unstack(fill_value=0)
        hours_series.columns = [str(x) + ":00" for x in hours_series.columns]
        hours_series = hours_series.reindex([str(x) + ":00" for x in range(24)], axis=1, fill_value=0)
        hours_series.sort_index()

        return hours_series.T
