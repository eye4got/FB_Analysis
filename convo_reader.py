import json
import os
import pathlib
import re
from datetime import *

from django.utils.text import slugify

from convo import *


class ConvoReader:
    inbox_path = "messages/inbox/"
    file_name_pattern = r"(message_\d{1}.json)"
    group_thread_type = "RegularGroup"
    text_msg_type = "Generic"

    # Uses result of json normalisation, which combines names where nested
    # FIXME: Incomplete
    # TODO: do the same thing for fields outside of messages list in json?
    facebook_field_names = {
        "sender_name": "sender_name",
        "timestamp_ms": "timestamp_ms",
        "content": "text",
    }

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

        # TODO: Why is this so deep, just take output path?
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
                curr_output = self.output_with_root + "/" + slugify(curr_convo.convo_name)
                pathlib.Path(curr_output).mkdir(parents=True, exist_ok=True)

                try:
                    with open(curr_output + "/desc.txt", "w", encoding="utf8") as file_obj:
                        file_obj.write(str(curr_convo))

                except IOError as err:
                    self.output_file_fail_count += 1
                    print(f"Could not output to: {curr_output}")
                    print(err)

                # curr_convo.create_timeline_hist().savefig(curr_output + "/Timeline_Hist.jpeg")
                # curr_convo.create_msg_time_hist().savefig(curr_output + "/Time_Freq_Hist.jpeg")

                print(f"Complete: {curr_output}")

        # Output is temporary, counters will need to be provided to output/UI though
        if self.open_file_fail_count > 0:
            print(f"{self.open_file_fail_count} file(s) could not be opened")

        if self.output_file_fail_count > 0:
            print(f"{self.output_file_fail_count} file(s) could not be written to")

    # TODO: Consider stripping out (static) cleaning methods into separate module/class?
    @staticmethod
    def encode_react(reactions_list):
        # Empty values are read as floats, return an empty dictionary so that the apply(series) handles appropriately
        if type(reactions_list) != list: return {}

        # Create dict with actors names as keys in order to split out each persons
        # reactions into columns to make counting etc easier for group chats
        output_dict = {}
        for ii, val in enumerate(reactions_list):
            person_key = val['actor'].replace(" ", "_").lower() + "_reaction"
            emoji = val["reaction"].encode('latin1').decode('utf-8')
            output_dict[person_key] = emoji

        if any(key not in ["alex_davison_reaction", "raine_bianchini_reaction"] for key in output_dict.keys()):
            print(output_dict.keys())

        return output_dict

    def clean_msg_data(self, messages_df):
        # Convert timestamp, reindex and use to sort
        messages_df["timestamp_ms"] = messages_df["timestamp_ms"].apply(lambda x: datetime.fromtimestamp(x // 1000))
        messages_df = messages_df.set_index("timestamp_ms").sort_index()

        # Sort out reaction encoding and split out into a column for each participant's reaction
        messages_df["reactions"] = messages_df["reactions"].apply(lambda x: self.encode_react(x))
        messages_df = pd.concat([messages_df, messages_df["reactions"].apply(pd.Series)], axis=1)

        return messages_df

    def extract_convo(self, file_path) -> Union[Convo, None]:

        # Identify all json files corresponding to conversation
        json_list = os.listdir(file_path)
        json_list = [x for x in json_list if re.match(self.file_name_pattern, x)]

        # Add file path
        json_list = [file_path + "/" + x for x in json_list]

        # Setup conversation
        raw_messages_df = pd.DataFrame()

        for path in json_list:
            # Load json as string as its nesting doesn't allow direct normalisation
            try:
                with open(path) as file_obj:
                    raw_json = json.load(file_obj)
            except FileNotFoundError as err:
                self.open_file_fail_count += 1
                print(f"File: {path} not found")
                print(err)
                return None

            input_df = pd.json_normalize(raw_json["messages"])
            raw_messages_df = raw_messages_df.append(input_df)

        messages_df = self.clean_msg_data(raw_messages_df)

        # Get all participants from last json object into list
        convo_persons = [x["name"] for x in raw_json["participants"]]

        # Check participants for existing persons and create new persons where necessary
        curr_participants = self.user.get_or_create_persons(convo_persons)

        # TODO: verify there are no other thread types
        is_group = raw_json["thread_type"] == self.group_thread_type
        is_active = raw_json["is_still_participant"]

        # messages_df = messages_df.rena

        return Convo(raw_json["title"], curr_participants, is_active, is_group, messages_df)
