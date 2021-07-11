from datetime import *
from typing import *

import matplotlib.pyplot as plt
import numpy as np


class Person:

    def __init__(self, name: str):
        self.name = name
        self.convoSides = []


class ConvoSide:

    def __init__(self, person: Person):
        self.person = person
        self.msg_count = 0
        # self.blockCount = 0
        self.char_count = 0
        # self.imgCount = 0
        # self.emojis = dict()
        # self.reacts = dict()
        # self.vocab = dict()
        # self.charBlockFreq = np.zeros(8)
        # self.replyTimeFreq = np.zeros(8)
        self.msg_time_freq = np.zeros(24)
        # self.dailyMsgCount = []
        # self.dailyCharCount = []
        # self.reactPercent = [] # Only based on active days, as a proportion
        # of all messages received
        self.multi_msg_counts: List[Tuple[datetime, int]] = []

    def get_name(self) -> str:
        return self.person.name

    def add_block_msg_count(self, time_stamp: datetime, count: int):
        if count < 1:
            raise ValueError("You cannot have a non-positive number of messages")

        self.multi_msg_counts.append((time_stamp, count))

    def __str__(self):
        output = "\t Side: " + self.get_name() + "\n"
        output += "Msg Count: " + str(self.msg_count) + "\n"
        output += "Char Count: " + str(self.char_count) + "\n"
        output += "Msg Times Frequency: " + str(self.msg_time_freq) + "\n"
        return output


class Convo:

    def __init__(self, name: str, participants: Dict[str, Person], is_active: bool, is_group: bool):
        self.convo_name = name
        self.participants = participants
        self.start_time = None
        self.is_active = is_active
        self.is_group = is_group
        self.convo_starter = None
        self.convo_sides = dict()
        self.msg_count = 0

        # Create a new ConvoSide for each participant
        for person in participants.values():
            self.convo_sides[person.name] = ConvoSide(person)

    def __str__(self) -> str:  # TODO: see if there are neater ways to output strings
        output = 'Conversation Name: ' + self.convo_name + '\n'
        output += 'Participants: ' + ", ".join(self.participants.keys()) + '\n\n'
        for side in self.convo_sides.values():
            output += str(side) + "\n"
        return output

    def create_msg_time_hist(self) -> plt.Figure:

        # Create hourly labels for time histogram
        # Create 2D array to match shape of series
        hist_hours = [[str(x) + ":00" for x in range(24)] for x in range(len(self.convo_sides))]

        ordered_sides = self.convo_sides.keys()
        series_counts = [self.convo_sides[side].msg_time_freq for side in ordered_sides]

        histogram = plt.figure(figsize=(14, 8))
        plt.hist(hist_hours, bins=24, weights=series_counts, alpha=0.5)
        plt.legend(ordered_sides, loc='upper left')

        return histogram


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

        return selected_persons
