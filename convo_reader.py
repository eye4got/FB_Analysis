import json
import os
import pathlib
import re
from operator import attrgetter
from types import SimpleNamespace

from django.utils.text import slugify

from convo import *


class ConvoReader:
    inbox_path = "messages/inbox/"
    file_name_pattern = r"(message_\d{1}.json)"
    group_thread_type = "RegularGroup"
    text_msg_type = "Generic"

    def __init__(self, root_path: str, output_path: str, user_name: str, individual_convo=None):

        if root_path[-1] != "/":
            root_path += "/"

        # TODO: explicit file path validation vs try/catch blocks in main.py? for main path
        # TODO: Implement logging using appropriate packages?

        self.file_path = root_path + self.inbox_path
        self.convos: Dict[str, Convo] = dict()
        self.persons: Dict[str, Person] = dict()
        self.user = User(user_name, root_path)

        self.open_file_fail_count = 0
        self.output_file_fail_count = 0

        # TODO: switch to relative filepath (Why didn't I initially?)
        self.output_with_root = root_path + "/" + output_path + "/"

        # Identify all conversations in directory
        convo_list = os.listdir(self.file_path)

        if individual_convo is not None:
            # Clean name
            cleaned_convo_input = individual_convo.lower().replace(" ", "")

            # Check if identified conversation exists
            ## Find folders which start with their name (groupchats can contain all names in alpha order)
            regex_str = re.compile(cleaned_convo_input + "_.+")
            matches = list(filter(lambda x: regex_str.match(x), convo_list))

            if len(matches) == 0:
                raise FileNotFoundError("Specified conversation: " + individual_convo + " does not exist")
            else:
                ## Find shortest folder name (to find convo with just them)
                fb_convo_str = min(matches, key=len)
                convo_list = [fb_convo_str]

        # Extract each conversation
        for convo_path in convo_list:
            curr_convo = self.extract_convo(self.file_path + convo_path)
            self.user.convos[curr_convo.convo_name] = curr_convo

            # Temporary solution to allow testing. GUI/output will be their own module(s)
            if curr_convo is not None:
                curr_convo.msg_count = sum([x.msg_count for x in curr_convo.convo_sides.values()])

                curr_output = self.output_with_root + "/" + slugify(curr_convo.convo_name)
                pathlib.Path(curr_output).mkdir(parents=True, exist_ok=True)

                try:
                    with open(curr_output + "/desc.txt", "w", encoding="utf8") as file_obj:
                        file_obj.write(str(curr_convo))

                except IOError as err:
                    self.output_file_fail_count += 1
                    print(f"Could not output to: {curr_output}")
                    print(err)

                # TODO: add handling of too many speakers (show top 5? cancel graph?)
                curr_convo.create_msg_time_hist().savefig(curr_output + "/Time_Freq_Hist.jpeg")

                print(f"Complete: {curr_output}")

        # Output is temporary, counters will need to be provided to output/UI though
        if self.open_file_fail_count > 0:
            print(f"{self.open_file_fail_count} file(s) could not be opened")

        if self.output_file_fail_count > 0:
            print(f"{self.output_file_fail_count} file(s) could not be written to")

    def get_or_create_convo_side(self, curr_convo: Convo, person_name: str) -> ConvoSide:

        if not person_name in curr_convo.convo_sides:
            if person_name in self.persons:
                chosen_person = self.persons[person_name]
            else:
                chosen_person = Person(person_name)
                self.persons[person_name] = chosen_person

            curr_convo.participants[person_name] = chosen_person
            curr_convo.convo_sides[person_name] = ConvoSide(chosen_person)

        return curr_convo.convo_sides[person_name]

    def setup_convo(self, file_path: str) -> Union[Convo, None]:

        # Load json as string
        try:
            with open(file_path, encoding="utf8") as file_obj:
                raw_json_str = file_obj.read()
        except FileNotFoundError as err:
            self.open_file_fail_count += 1
            print(f"File: {file_path} not found")
            print(err)
            return None

        # Convert JSON to dictionary
        raw_convo = json.loads(raw_json_str)

        # Get all participants from json object into list
        convo_persons = [x["name"] for x in raw_convo["participants"]]

        # Check participants for existing persons and create new persons where
        # necessary
        curr_participants = self.user.get_or_create_persons(convo_persons)

        # TODO: verify there are no other thread types
        is_group = raw_convo["thread_type"] == self.group_thread_type
        is_active = raw_convo["is_still_participant"]

        return Convo(raw_convo["title"], curr_participants, is_active, is_group)

    def extract_json_files(self, json_list) -> List[SimpleNamespace]:

        message_list = []

        # Extract all messages into single linked-list for sorting as
        # number/order is unknown
        for json_path in json_list:
            # Load json as string
            try:
                with open(json_path, encoding="utf8") as file_obj:
                    raw_json_str = file_obj.read()
            except FileNotFoundError as err:
                self.open_file_fail_count += 1
                print(f"File: {json_path} not found")
                print(err)

            # Convert JSON to list of messages
            curr_json = json.loads(raw_json_str)["messages"]
            processed_messages = [SimpleNamespace(**x) for x in curr_json]

            message_list.extend(processed_messages)

        return message_list

    @staticmethod
    def get_msg_time(msg) -> datetime:
        return datetime.fromtimestamp(msg.timestamp_ms // 1000)

    def extract_convo(self, file_path) -> Union[Convo, None]:

        # Identify all json files corresponding to conversation
        json_list = os.listdir(file_path)
        json_list = [x for x in json_list if re.match(self.file_name_pattern, x)]

        # Add file path
        json_list = [file_path + "/" + x for x in json_list]

        # Setup conversation using first file (e.g. extract participants)
        curr_convo = self.setup_convo(json_list[0])

        if curr_convo is None:
            return None

        # Get sorted list of messages
        messages_list = self.extract_json_files(json_list)
        sorted(messages_list, key=attrgetter("timestamp_ms"))

        # Get first conversation side (unique combination of person and conversation
        first_sender = messages_list[0].sender_name
        curr_convo_side = self.get_or_create_convo_side(curr_convo, first_sender)

        # Initialise counters
        curr_block_msg_count = 0
        curr_block_char_count = 0
        curr_block_start_time = self.get_msg_time(messages_list[0])

        # Extract first person to send a message
        curr_convo.convo_starter = curr_convo_side.person

        for msg in messages_list:
            if msg.sender_name != curr_convo_side.get_name():
                # Update summary statistics
                curr_convo_side.msg_count += curr_block_msg_count
                curr_convo_side.char_count += curr_block_char_count
                curr_convo_side.add_block_msg_count(curr_block_start_time, curr_block_msg_count)

                # Reset counters TODO: create separate function for counter reset? (e.g. create ConvoBlock class)
                curr_convo_side = self.get_or_create_convo_side(curr_convo, msg.sender_name)
                curr_block_msg_count = 0
                curr_block_char_count = 0
                curr_block_start_time = self.get_msg_time(msg)

            curr_block_msg_count += 1

            # Add character counts where applicable
            if msg.type == self.text_msg_type and hasattr(msg, "content"):
                curr_block_char_count += len(msg.content)

            # Increment hour of the day when message was sent
            curr_convo_side.msg_time_freq[curr_block_start_time.hour - 1] += 1

        del messages_list

        return curr_convo
