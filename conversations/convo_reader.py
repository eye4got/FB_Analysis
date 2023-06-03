import json
import logging
import os
import pathlib
import pickle
import re
import shutil
from typing import *

import pandas as pd

from conversations.convo import Convo
from conversations.user import User


class ConvoReader:
    inbox_path = os.path.join("messages", "inbox")
    file_name_pattern = r"(message_\d{1}.json)"
    group_thread_type = "RegularGroup"
    text_msg_type = "Generic"

    # Uses result of json normalisation, which combines names where nested
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

    @staticmethod
    def unzip_and_merge_files(file_path):
        """
        Currently checks if an unzipped folder with same name as a zipped object exists and assumes that is its counterpart
        FaceBook has currently split the download into multiple similarly structures files. However, as far as I can tell
        only one actually contains messages sent and received. We are merging all these files into one regardless

        :param file_path: str which indicates where the downloaded files (and no other files) are stored
        """

        all_files = os.listdir(file_path)
        zipped_files_wo_unzip = [x for x in all_files if
                                 os.path.splitext(x)[-1] == '.zip' and os.path.splitext(x)[0] not in all_files]

        for zipped_file in zipped_files_wo_unzip:
            shutil.unpack_archive(os.path.join(file_path, zipped_file))

    @staticmethod
    def read_convos(user_name: str, root_path: str, individual_convo: str = None) -> User:

        """
        :param user_name:   Name of person whose data is being analysed
        :param root_path:   Path to folder of zipped or unzipped folders FB has provided (assumes unzipped have same name their zipped counterpart)
        :param individual_convo:    Optional argument to specify a specific person or groupchat's name
        :return: a User object, containing all the conversations

        Reads all conversations located in the object's filepath
        """

        curr_user = User(user_name, root_path)
        file_path = os.path.join(root_path, ConvoReader.inbox_path)
        ConvoReader.unzip_and_merge_files(file_path)
        empty_convo_count = 0

        # Identify all conversations in directory (needed even for individual conversations, to search for FB file names)
        convo_list = os.listdir(file_path)

        if individual_convo is not None:
            convo_list = [ConvoReader.find_individual_convo_path(individual_convo, convo_list)]

        # Extract each conversation
        for ii, convo_path in enumerate(convo_list):

            # Print out progress every 50 conversations
            if ii % 50 == 0:
                logging.info(f"\t\t{ii} / {len(convo_list)}")

            curr_convo = ConvoReader.extract_single_convo(curr_user, os.path.join(file_path, convo_path))

            if curr_convo is not None:
                curr_user.convos[curr_convo.convo_name] = curr_convo

            else:
                empty_convo_count += 1

        if empty_convo_count > 0:
            logging.info(f"\n{empty_convo_count} conversations were empty")

        curr_user.build_sma_df()

        return curr_user

    @staticmethod
    def extract_single_convo(curr_user, file_path) -> Union[Convo, None]:

        """
        Identifies all JSON files associated with a single conversation and initialises a Convo object
        :param curr_user: the current User object instance, which is being added to
        :param file_path: the path to the conversation within the Raw Data extract
        :return: a "nullable-like" Convo, in case the Convo cannot be initialised properly
        """

        # Identify all json files corresponding to conversation
        json_list = [x for x in os.listdir(file_path) if re.match(ConvoReader.file_name_pattern, x)]

        # Add file path
        full_path_json_list = [os.path.join(file_path, x) for x in json_list]

        # Setup conversation Dataframe (to guarantee all cols exist, loop through each JSON file and append new rows
        raw_msgs_df_list = [pd.DataFrame(columns=ConvoReader.facebook_field_names.keys())]

        for path in full_path_json_list:
            # Load json as string as its nesting doesn't allow direct normalisation
            try:
                with open(path) as file_obj:
                    raw_json_file_str = file_obj.read().encode("latin1").decode("utf-8")
                    raw_json = json.loads(raw_json_file_str)

            except FileNotFoundError as err:
                print(f"File: {path} not found")
                print(err)
                return None

            # Add json normalised data to list, for performant appending once all have been collected
            raw_msgs_df_list.append(pd.json_normalize(raw_json["messages"]))

        raw_msgs_df = pd.concat(raw_msgs_df_list)
        msgs_df = ConvoReader.clean_msg_data(raw_msgs_df)
        convo_persons = list(msgs_df["sender_name"].unique())

        # Remove conversations where only one person has sent a message (conversations are initialised with one msg)
        if len(convo_persons) < 2:
            return None

        # Check speakers for existing persons and create new persons where necessary
        curr_speakers = curr_user.get_or_create_persons(convo_persons)

        is_group = raw_json["thread_type"] == ConvoReader.group_thread_type
        is_active = raw_json["is_still_participant"]
        title = raw_json["title"].encode("latin1").decode("utf-8")

        return Convo(title, curr_speakers, is_active, is_group, msgs_df)

    @staticmethod
    def restructure_reactions(reactions_list):

        """
        Converts FB's reaction dictionary for each message from a list with multiple entries into one dictionary linking
        people and their reaction. Enables splitting into cols to make counting etc easier for group chats
        :param reactions_list: list of sets containing any users that reacted and their reaction
        :return: Dictionary of users and their corresponding reaction
        """

        # Empty values are read as floats, return an empty dictionary so that the apply(series) handles appropriately
        if type(reactions_list) != list: return {}

        output_dict = {}

        for ii, val in enumerate(reactions_list):
            person_key = val["actor"].replace(" ", "_").lower() + "_reactions"
            emoji = val["reaction"].encode("latin1").decode("utf-8")
            output_dict[person_key] = emoji

        return output_dict

    @staticmethod
    def clean_msg_data(msgs_df: pd.DataFrame) -> pd.DataFrame:

        """
        Renames columns to standardised names, converts types, sorts data, flattens and extracts highly nested columns.
        :param msgs_df: A dataframe of all the messages in a conversation
        :return: A dataframe of accessible and flattened messages in a conversation
        """

        msgs_df.rename(columns=ConvoReader.facebook_field_names, inplace=True)

        # Convert timestamp, reindex and use to sort
        msgs_df["timestamp"] = pd.to_datetime(msgs_df["timestamp"], unit="ms")
        msgs_df = msgs_df.set_index("timestamp").sort_index()

        # Decode Sender Names (As this doesn't appear to happen as part of general re-encoding)
        msgs_df["sender_name"] = msgs_df["sender_name"].apply(lambda x: x.encode("latin1").decode("utf-8"))

        # Clean reaction encoding FIXME: poor way to split out str into dict, however performance is not terrible
        msgs_df["reactions_dict"] = msgs_df["reactions_dict"].apply(lambda x: ConvoReader.restructure_reactions(x))

        # Split out reactions into individual columns
        reactions_df = pd.DataFrame(msgs_df['reactions_dict'].values.tolist(), index=msgs_df.index)
        msgs_df = pd.concat([msgs_df, reactions_df], axis=1)
        msgs_df.drop("reactions_dict", axis='columns', inplace=True)

        # Extract video and photo counts (don't need nested uris)
        media_cols = ["photos", "videos", "audio_files", "files"]
        for col in media_cols:
            msgs_df[[col]] = msgs_df[[col]].apply(lambda x: len(x) if type(x) is list else 0)

        return msgs_df

    @staticmethod
    def find_individual_convo_path(individual_name: str, convo_list: List[str]) -> str:
        """
        Finds filepath associated with conversation as Facebook adds alphanumeric junk at the end of the folder name.
        Prioritises 1-1 conversations over group-chats where unclear
        :param individual_name: Name of Conversation (person or groupchat), only including alphanumeric characters and dashes
        :param convo_list: List of conversations identified in raw data to search through
        :return: returns the location of the single conversation to be read in
        """

        cleaned_convo_input = individual_name.lower().replace(" ", "")

        # Check if identified conversation exists
        ## Find folders which start with their name (group chats can contain all names in alpha order)
        regex_str = re.compile(cleaned_convo_input + "_.+")
        matches = list(filter(lambda x: regex_str.match(x), convo_list))

        if len(matches) == 0:
            raise FileNotFoundError(f"Specified conversation: {individual_name} does not exist")
        else:
            ## Find the shortest folder name (to find conversations with just them)
            fb_convo_str = min(matches, key=len)

        return fb_convo_str

    @staticmethod
    def build_cache(root_path, cache_root, full_cache_path, user_name):
        cached_data = None

        print("Building Cache:")

        try:
            # Import Convos
            cached_data = ConvoReader.read_convos(user_name, root_path)

            # Check if cache directory exists, if not create it
            pathlib.Path(cache_root).mkdir(parents=True, exist_ok=True)

            # Cache user object
            with open(full_cache_path, "wb") as file_obj:
                pickle.dump(cached_data, file_obj)

        except IOError:
            print("Cache Build Failed")

        else:
            print("Cache: Built")

        return cached_data
