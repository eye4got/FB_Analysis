from typing import *
import datetime

class Person:

    def __init__(self, name: str):
        self.name = name
        self.convoSides = []


class ConvoSide:

    def __init__(self, person: Person):

        self.person = person
        self.msg_count = 0
        #self.blockCount = 0
        self.char_count = 0
        #self.imgCount = 0
        #self.emojis = dict()
        #self.reacts = dict()
        #self.vocab = dict()
        #self.charBlockFreq = np.zeros(8)
        #self.replyTimeFreq = np.zeros(8)
        #self.dailyMsgCount = []
        #self.dailyCharCount = []
        # self.reactPercent = [] # Only based on active days, as a proportion
        # of all messages received
        self.multi_msg_counts : List[Tuple[int, datetime.datetime]] = []


    def get_name(self) -> str:
        return self.person.name

    def add_block_msg_count(self, count: int, time_stamp: datetime.datetime):

        if count >= 1:
            raise ValueError("You cannot have a non-positive number of messages")

        self.multi_msg_counts.append((count, time_stamp))


    def __str__(self):
        output = "\t Side: " + self.get_name() + "\n"
        output += "Msg Count: " + str(self.msg_count) + "\n"
        output += "Char Count: " + str(self.char_count) + "\n"
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

        # Create a new ConvoSide for each participant
        for person in participants.values():
            self.convo_sides[person.name] = ConvoSide(person)

            
    def __str__(self) -> str: # TODO: see if there are neater ways to output strings
        output = 'Conversation Name: ' + self.convo_name + '\n'
        output += 'Participants: ' + ", ".join(self.participants.keys()) + '\n\n'
        for side in self.convo_sides.values():
            output += str(side) + "\n"
        return output
       

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
