from typing import *

import pandas as pd
from tabulate import tabulate


class Person:

    def __init__(self, name: str):
        self.name = name
        self.convoSides = []


class Convo:

    def __init__(self, name: str, participants: Dict[str, Person], is_active: bool, is_group: bool,
                 messages_df: pd.DataFrame):
        self.convo_name = name
        self.participants = participants
        self.start_time = messages_df.index[0]
        self.is_active = is_active
        self.is_group = is_group
        self.msg_count = messages_df.count()
        self.messages_df = messages_df

    def __str__(self) -> str:  # TODO: see if there are neater ways to output strings
        output = 'Conversation Name: ' + self.convo_name + '\n'
        output += 'Participants: ' + ', '.join(self.participants.keys()) + '\n\n'

        grouped_for_counts = self.messages_df.groupby("sender_name")
        # Perform separately and join as using agg for both steps duplicated columns or required too much customisation
        counts_df = grouped_for_counts.count()
        counts_df['Messages'] = grouped_for_counts.size()
        # TODO: rename and order columns (drop columns such as is_unsent)
        output += tabulate(counts_df, headers=counts_df.columns)

        return output

    # def create_msg_time_hist(self, top: int = 5) -> plt.Figure:
    # TODO: add handling of too many speakers (show top 5? cancel graph?)

    # Create hourly labels for time histogram
    # Create 2D array to match shape of series
    # sides_num = len(self.convo_sides) if len(self.convo_sides) < 5 else 5
    # hist_hours = [[str(x) + ":00" for x in range(24)] for x in range(sides_num)]
    #
    # # Convert dictionary to list and take specified 'top' number of values, sorting by total messages count
    # convo_sides_list = list(self.convo_sides.values())
    #
    # if len(convo_sides_list) > 5:
    #     convo_sides_list.sort(key=lambda x: x.msg_count, reverse=True)
    #     convo_sides_list = convo_sides_list[:top]
    #
    # series_counts = [side.msg_time_freq for side in convo_sides_list]
    #
    # histogram = plt.figure(figsize=(14, 8))
    # # FIXME: axis doesn't line up with bars (but plot won't let me increase number of labels
    # plt.hist(hist_hours, bins=24, weights=series_counts, alpha=0.5)
    # plt.legend([side.person.name for side in convo_sides_list], loc='upper left')
    #
    # return histogram

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

        # FIXME: Remove user from participants?
        selected_persons = dict()

        for person in name_list:
            if not person in self.persons:
                self.persons[person] = Person(person)
            # Extract instances of person for assignment to avoid instance
            # duplication
            selected_persons[person] = self.persons[person]

        # TODO: Overall summary stats (e.g. convo starting)

        return selected_persons
