import json
import os
import pathlib
import re

from django.utils.text import slugify

from convo import *


class ConvoReader:
    inbox_path = "messages/inbox/"
    file_name_pattern = r"(message_\d{1}.json)"
    group_thread_type = "RegularGroup"
    text_msg_type = "Generic"

    # Uses result of json normalisation, which combines names where nested
    # TODO: do the same thing for fields outside of messages list in json?
    # TODO: identify dictionaries in fields below and flatten where relevant
    facebook_field_names = {
        "sender_name": "sender_name",
        "timestamp_ms": "timestamp",
        "content": "text",
        "reactions": "reactions_dict",
        "type": "major_type",
        "is_unsent": "is_unsent",
        "photos": "photos",
        "share.link": "share_link",
        "sticker.uri": "sticker_path",
        "call_duration": "call_duration",
        "videos": "videos",
        "share.share_text": "share_text",
        "files": "files",
        "audio_files": "audio_files",
        "missed": "missed_call",
        "gifs": "gifs"
    }

    def __init__(self, root_path: str, user_name: str):

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
        self.empty_convo_count = 0

    def generate_output(self, output_path: str, individual_convo=None):

        # Identify all conversations in directory
        convo_list = os.listdir(self.file_path)

        if individual_convo is not None:
            convo_list = [self.find_individual_convo_path(individual_convo, convo_list)]

        # Extract each conversation
        for convo_path in convo_list:
            print(f"{convo_path}: ", end='')
            curr_convo = self.extract_convo(self.file_path + convo_path)

            # Temporary solution to allow testing. GUI/output will be their own module(s)
            if curr_convo is not None:
                self.user.convos[curr_convo.convo_name] = curr_convo
                curr_output = output_path + "/" + slugify(curr_convo.convo_name)
                pathlib.Path(curr_output).mkdir(parents=True, exist_ok=True)

                try:
                    with open(curr_output + "/desc.txt", "w", encoding="utf8") as file_obj:
                        file_obj.write(str(curr_convo))

                except IOError as err:
                    self.output_file_fail_count += 1
                    print(f"Could not output to: {curr_output}")
                    print(err)

                curr_convo.create_timeline_hist().savefig(curr_output + "/Timeline_Hist.jpeg")
                curr_convo.create_msg_time_hist().savefig(curr_output + "/Time_Freq_Hist.jpeg")

                print("Complete")

            else:
                print("Failed")

        # Output is temporary, counters will need to be provided to output/UI though
        if self.open_file_fail_count > 0:
            print(f"{self.open_file_fail_count} file(s) could not be opened")

        if self.output_file_fail_count > 0:
            print(f"{self.output_file_fail_count} file(s) could not be written to")

        if self.empty_convo_count > 0:
            # TODO: opportunity for statistic around number of FB friends actually spoken to
            print(f"{self.empty_convo_count} conversations were empty")

    def extract_convo(self, file_path) -> Union[Convo, None]:

        # Identify all json files corresponding to conversation
        json_list = os.listdir(file_path)
        json_list = [x for x in json_list if re.match(self.file_name_pattern, x)]

        # Add file path
        json_list = [file_path + "/" + x for x in json_list]

        # Setup conversation Dataframe, loop through each JSON file and append new rows
        raw_msgs_df = pd.DataFrame(columns=ConvoReader.facebook_field_names.keys())

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
            raw_msgs_df = raw_msgs_df.append(input_df)

        msgs_df = self.clean_msg_data(raw_msgs_df)

        # Get all speakers from messages (includes people who have been removed from the conversation)
        convo_persons = list(raw_msgs_df['sender_name'].unique())

        # Remove conversations where only one person has sent a message (conversations are initalised with one msg)
        if len(convo_persons) < 2:
            self.empty_convo_count += 1
            return None

        # Check speakers for existing persons and create new persons where necessary
        curr_speakers = self.user.get_or_create_persons(convo_persons)

        is_group = raw_json["thread_type"] == self.group_thread_type
        is_active = raw_json["is_still_participant"]

        return Convo(raw_json["title"], curr_speakers, is_active, is_group, msgs_df)

    def extract_convo_from_name(self, individual_name: str) -> Union[Convo, None]:
        # Wrapper method for extract_convo when running in isolation and filepath is unknown
        convo_list = os.listdir(self.file_path)
        convo_filepath = self.find_individual_convo_path(individual_name, convo_list)

        return self.extract_convo(self.file_path + "/" + convo_filepath)

    # TODO: Consider stripping out (static) cleaning methods into separate module/class?
    @staticmethod
    def encode_react(reactions_list):
        # Empty values are read as floats, return an empty dictionary so that the apply(series) handles appropriately
        if type(reactions_list) != list: return {}

        # Create dict with actors names as keys in order to split out each persons
        # reactions into columns to make counting etc easier for group chats
        output_dict = {}
        for ii, val in enumerate(reactions_list):
            person_key = val['actor'].replace(" ", "_").lower() + "_reactions"
            emoji = val["reaction"].encode('latin1').decode('utf-8')
            output_dict[person_key] = emoji

        return output_dict

    def clean_msg_data(self, msgs_df):

        msgs_df.rename(columns=ConvoReader.facebook_field_names, inplace=True)

        # Convert timestamp, reindex and use to sort
        msgs_df["timestamp"] = msgs_df["timestamp"].apply(lambda x: datetime.fromtimestamp(x // 1000))
        msgs_df = msgs_df.set_index("timestamp").sort_index()

        # Sort out reaction encoding and split out into a column for each speaker's reaction
        msgs_df["reactions_dict"] = msgs_df["reactions_dict"].apply(lambda x: self.encode_react(x))
        msgs_df = pd.concat([msgs_df, msgs_df["reactions_dict"].apply(pd.Series)], axis=1)

        # Extract video and photo counts (don't need nested uris)
        media_cols = ["photos", "videos", "audio_files", "files"]
        for col in media_cols:
            msgs_df[col] = msgs_df[col].apply(lambda x: len(x) if type(x) == list else 0)

        return msgs_df

    @staticmethod
    def find_individual_convo_path(individual_name: str, convo_list: List[str]) -> str:
        # Finds filepath associated with conversation as Facebook adds alphanumeric junk at the end of the folder name
        # Priorities 1-1 conversations over group-chats where unclear

        # Clean name
        cleaned_convo_input = individual_name.lower().replace(" ", "")

        # Check if identified conversation exists
        ## Find folders which start with their name (group chats can contain all names in alpha order)
        regex_str = re.compile(cleaned_convo_input + "_.+")
        matches = list(filter(lambda x: regex_str.match(x), convo_list))

        if len(matches) == 0:
            raise FileNotFoundError("Specified conversation: " + individual_name + " does not exist")
        else:
            ## Find shortest folder name (to find convo with just them)
            fb_convo_str = min(matches, key=len)

        return fb_convo_str
