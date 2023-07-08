import json
import logging
import os
import pathlib
import pickle
import re
import shutil
import time
import zipfile
from typing import *

import numpy as np
import pandas as pd

from conversations.convo import Convo
from conversations.user import User


class ConvoReader:
    cache_file_name = "user_pickle.p"
    inbox_path = os.path.join("messages", "inbox")
    file_name_pattern = r"(message_\d{1}.json)"

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
        "missed": "missed_call",
        "audio_files": "audio_files",
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

        # Unzip files
        zipped_files_wo_unzip = [x for x in all_files if
                                 zipfile.is_zipfile(os.path.join(file_path, x)) and os.path.splitext(x)[
                                     0] not in all_files]

        logging.info(f'Found {len(zipped_files_wo_unzip)} files to unzip')

        for zipped_file in zipped_files_wo_unzip:
            logging.info(f'\t unzipping {zipped_file}')
            new_dir_location = os.path.join(file_path, os.path.splitext(zipped_file)[0])
            os.mkdir(new_dir_location)

            try:
                with zipfile.ZipFile(os.path.join(file_path, zipped_file), mode="r") as archive:
                    archive.extractall(new_dir_location)
            except zipfile.BadZipfile as err:
                logging.info(f'Failed to extract {zipped_file}')
                logging.info(err)

        # TODO: Merge directories (currently only one actually has messages in it, however, rest contain files)
        os.listdir(file_path)

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
        ConvoReader.unzip_and_merge_files(root_path)
        file_path = os.path.join(root_path, ConvoReader.inbox_path)
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
        # FIXME: This mask sometimes massively overcounts missed calls
        msgs_df['missed_call'] = np.logical_and(msgs_df['call_duration'].notna(), msgs_df['call_duration'] == 0)
        convo_persons = list(msgs_df["sender_name"].unique())

        # Keep track of conversations with people who have deleted their account if there are more than the initial
        # number of messages (using proxy names), otherwise remove
        if '' in convo_persons:
            if msgs_df.shape[0] > 2:
                for idx, val in enumerate(convo_persons):
                    if val == '':
                        curr_user.unknown_people += 1
                        convo_persons[idx] = f"Unknown Person #{curr_user.unknown_people}"
            else:
                convo_persons = [x for x in convo_persons if x != '']

        # Remove conversations where only one person has sent a message (conversations are initialised with one msg)
        if len(convo_persons) < 2:
            return None

        # Check speakers for existing persons and create new persons where necessary
        curr_speakers = curr_user.get_or_create_persons(convo_persons)

        is_group = len(msgs_df['sender_name'].unique()) > 2
        is_active = raw_json["is_still_participant"]
        title = raw_json["title"].encode("latin1").decode("utf-8")

        if title == '':
            curr_user.unknown_convos += 1
            title = ', '.join([x for x in curr_speakers if x != curr_user.name])

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

        renamed_msgs_df = msgs_df.rename(columns=ConvoReader.facebook_field_names)

        # Convert timestamp, reindex and use to sort
        # FIXME: Fix janky hack to convert all timestamps from UTC to local zone, or at least provide an override
        # Unfortunately Facebook gives us insufficient information to infer the tz of the sender for each message
        renamed_msgs_df["timestamp"] = pd.to_datetime(renamed_msgs_df["timestamp"], unit="ms", utc=True)
        cleaned_df = renamed_msgs_df.set_index("timestamp").sort_index().tz_convert(time.strftime("%z"))

        # Decode Sender Names (As this doesn't appear to happen as part of general re-encoding)
        cleaned_df["sender_name"] = cleaned_df["sender_name"].apply(lambda x: x.encode("latin1").decode("utf-8"))

        # Clean reaction encoding FIXME: poor way to split out str into dict, however performance is not terrible
        cleaned_df["reactions_dict"] = cleaned_df["reactions_dict"].apply(
            lambda x: ConvoReader.restructure_reactions(x))

        # Split out reactions into individual columns
        reactions_df = pd.DataFrame(cleaned_df['reactions_dict'].values.tolist(), index=cleaned_df.index)
        cleaned_df = pd.concat([cleaned_df, reactions_df], axis=1)
        cleaned_df.drop("reactions_dict", axis='columns', inplace=True)

        # Extract video and photo counts (don't need nested uris)
        media_cols = ["photos", "videos", "audio_files", "files"]
        for col in media_cols:
            cleaned_df[[col]] = cleaned_df[[col]].apply(lambda x: len(x) if type(x) is list else 0)

        # Extract call data

        return cleaned_df

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
    def build_cache(root_path: str, cache_root: str, user_name: str):

        cached_data = None
        full_cache_path = os.path.join(cache_root, ConvoReader.cache_file_name)
        logging.info("Building Cache")

        try:
            # Import Convos
            cached_data = ConvoReader.read_convos(user_name, root_path)

            # Check if cache directory exists, if not create it
            pathlib.Path(cache_root).mkdir(parents=True, exist_ok=True)

            # Cache user object
            with open(full_cache_path, "wb") as file_obj:
                pickle.dump(cached_data, file_obj)

        except IOError:
            logging.info("Cache Build Failed")

        else:
            logging.info("Cache Built")

        return cached_data

    @staticmethod
    def load_or_create_cache(root_path: str, cache_root: str, user_name: str):

        cached_data = None
        full_cache_path = os.path.join(cache_root, ConvoReader.cache_file_name)

        if os.path.exists(full_cache_path):
            try:
                with open(full_cache_path, "rb") as file_obj:
                    cached_data = pickle.load(file_obj)

            except IOError:
                print("The Cache Output Filepath exists but could not be opened. It will be rebuilt")
                # Delete the previous filepath, triggering a rebuild of the cache
                shutil.rmtree(cache_root)

            else:
                print("Cache: Found")
                # TODO: Add Cache Integrity Check

        if not os.path.exists(full_cache_path):
            cached_data = ConvoReader.build_cache(root_path, cache_root, user_name)

        return cached_data
