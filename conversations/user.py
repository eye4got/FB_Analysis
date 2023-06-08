import datetime as dt
from typing import *

import pandas as pd

from conversations.convo import Convo, Person


class User:

    def __init__(self, name: str, root_path: str):
        self.name = name
        self.root_path = root_path
        self.convos: Dict[str, Convo] = dict()
        self.persons: Dict[str, Person] = dict()

        self.joined_sma_df: pd.DataFrame

    def get_convos_ranked_by_msg_count(self, n: int = 100, no_groupchats: bool = False) -> List[Tuple[str, int]]:

        """
        Counts the number of messages in conversations (excludes groupchats by default), sorts by highest counts and
        can return the top 'n'

        :param n:  Number of conversations msg counts to return. For n < 1, all results will be returned
        :param no_groupchats: Optional bool, determining whether to include groupchats
        :return: A list of tuples, structured: ('Name', Msg_Count)
        """

        if no_groupchats:
            counts = [(x.convo_name, x.msg_count) for x in self.convos.values() if x.is_group == False]
        else:
            counts = [(x.convo_name, x.msg_count) for x in self.convos.values()]

        counts = sorted(counts, key=lambda x: x[1], reverse=True)

        if n > 1:
            counts = counts[:n]

        return counts

    def get_convos_ranked_by_char_ratio(self, desc: bool, n: int = 100, no_groupchats: bool = True,
                                        min_msgs: int = 200) -> List[Tuple[str, int]]:

        """
        Calculates the character ratio: [Others Char Count] / ([Your Char Count] * [Others Speaker Count]),
        scaling your character count based on the number of people in the conversation. It sorts by either the highest,
        or lowest ratios and can return the top 'n' results. Conversations that are considered too small are removed as outliers.

        A ratio of 1 indicates a balanced conversation.
            High Char Ratio -> Your friends dominate the conversation
            Low Char Ratio -> You dominate the conversation

        :param desc: A boolean, determining whether the results should be sorted in a descending manner
        :param n: The number of conversations char ratios to return. Can be used in conjunction with desc to return the head or tail
        :param no_groupchats: Optional bool, determining whether to include groupchats
        :param min_msgs: The minimum number of messages per speaker, for the character ratio to be evaluated
        :return: A list of tuples, structured: ('Name', Char Ratio)
        """

        ratios_list: List[Tuple[str, int]] = []
        filtered_convos = [x for x in self.convos.values() if self.name in x.speakers]

        if no_groupchats:
            filtered_convos = [x for x in filtered_convos if x.is_group == True]

        for convo in self.convos.values():
            others_speaker_count = len(convo.speakers.keys()) - 1

            if self.name in convo.speakers and convo.msg_count > (min_msgs * len(convo.speakers.keys())):
                user_chars = convo.msgs_df[convo.msgs_df["sender_name"] == self.name]["text_len"].sum()
                others_char_count = convo.msgs_df["text_len"].sum() - user_chars

                ratio = others_char_count / (user_chars * others_speaker_count)
                ratios_list.append((convo.convo_name, ratio))

        ratios_list = sorted(ratios_list, key=lambda x: x[1], reverse=desc)

        if n > 1:
            ratios_list = ratios_list[:n]

        return ratios_list

    def get_or_create_persons(self, name_list: List[str]) -> Dict[str, Person]:

        """
        Retrieve the persons whose names are listed and create any that are missing. This ensures references are pointers
        to a single Person object rather than duplication between conversations
        :param name_list: A list of participants names as strings
        :return: A dictionary of the Persons, with their names as keys
        """

        selected_persons = dict()

        for person in name_list:
            if not person in self.persons:
                self.persons[person] = Person(person)
            # Extract instances of person for assignment to avoid instance duplication
            selected_persons[person] = self.persons[person]

        return selected_persons

    def build_sma_df(self, sample_period='14D', rolling_window=3, start_date: Union[dt.datetime, None] = None,
                     end_date: Union[dt.datetime, None] = None):

        offset = dt.timedelta(days=int(sample_period[:-1]))
        if start_date:
            chart_start_dt = pd.to_datetime(start_date - (offset * rolling_window) * 2)

        cols_to_combine = []
        for c_name, convo in self.convos.items():

            df = convo.msgs_df
            df['timestamp'] = df.index
            if start_date:
                df = df[df.timestamp >= chart_start_dt]

            if end_date:
                df = df[df.timestamp <= end_date]

            # Hacky time saving manoeuvre
            if df.shape[0] < 100:
                continue

            # Restriction conversation name length, so y axis labels don't get out of hand
            c_name = c_name if len(c_name) < 32 else c_name[:32] + ' ...'

            # Aggregate text counts into periods and then apply a simple moving average
            sma_df = pd.DataFrame()
            sma_df[c_name] = df.resample(sample_period, on='timestamp', label='right', origin='epoch').text_len.sum()
            if rolling_window > 1:
                sma_df[c_name] = sma_df[c_name].rolling(window=rolling_window).mean()

            if sma_df.shape[0] > 0:
                if start_date:
                    sma_df = sma_df[sma_df.index >= start_date]
                else:
                    sma_df = sma_df[sma_df.index >= sma_df.index.min() + rolling_window * offset]

                cols_to_combine.append(sma_df)

        # Concatenate and fill missing values with zeroes
        return pd.concat(cols_to_combine, axis=1).fillna(0)  # .drop_duplicates()
