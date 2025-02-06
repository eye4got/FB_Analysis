import json
import logging
import os
import pathlib
import pickle
import re
import shutil
import time
import warnings
import zipfile
from typing import *

import nomquamgender as nqg
import numpy as np
import pandas as pd

from conversations.convo import Convo
from conversations.user import User


# FIXME: establish abstract pattern and then build specific implementations for FB, IG, Whatsapp etc, instead of gross
# hardcoded pattern. However, that is extensive extra work for minimal benefit for now (given limited interest in Whatsapp)


class ConvoReader:
    cache_file_name = "user_pickle.p"
    fb_inbox_path = os.path.join("your_facebook_activity", "messages", "inbox")
    ig_inbox_path = os.path.join("your_instagram_activity", "messages", "inbox")
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

    facebook_field_types = {
        "sender_name": pd.Series(dtype='str'),
        "timestamp_ms": pd.Series(dtype='int64'),
        "content": pd.Series(dtype='str'),
        "reactions": pd.Series(dtype='object'),
        "type": pd.Series(dtype='str'),
        "is_unsent": pd.Series(dtype='str'),
        "photos": pd.Series(dtype='str'),
        "share.link": pd.Series(dtype='str'),
        "sticker.uri": pd.Series(dtype='str'),
        "call_duration": pd.Series(dtype='float64'),
        "videos": pd.Series(dtype='str'),
        "share.share_text": pd.Series(dtype='str'),
        "files": pd.Series(dtype='str'),
        "missed": pd.Series(dtype='bool'),
        "audio_files": pd.Series(dtype='str'),
        "gifs": pd.Series(dtype='str')
    }

    if set(facebook_field_names.keys()) != set(facebook_field_types.keys()):
        raise ValueError(
            "Safety Check Failed: All keys in the field types must be keys in the field names (consistent input pattern)")

    # Model to guess most common binarized gender associated with name, produces 0-1 output to roughly indicate confidence
    nqg_model = nqg.NBGC()
    pgf_cutoff = 0.15


    # FIXME: Adjust so it's not OS specific
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
    def read_convos(user_name: str, fb_path: str = None, ig_path: str = None, ig_fb_matches: pd.DataFrame = None,
                    individual_convo: str = None) -> User:

        """
        :param user_name:   Name of person whose data is being analysed
        :param root_path:   Path to folder of zipped or unzipped folders FB has provided (assumes unzipped have same name their zipped counterpart)
        :param individual_convo:    Optional argument to specify a specific person or groupchat's name
        :return: a User object, containing all the conversations

        Reads all conversations located in the object's filepath
        """

        if (not fb_path and not ig_path) or (ig_path and not os.path.exists(ig_path)) or (fb_path and not os.path.exists(fb_path)):
            raise ValueError("You must provide a valid data extract path for at least Facebook OR Instagram")

        curr_user = User(user_name, fb_path, ig_path)
        convo_list = []
        
        # ConvoReader.unzip_and_merge_files(fb_path)

        # Identify all conversations in directories (needed even to retrieve individual conversations, to search for FB file names)
        if curr_user.has_fb:
            local_fb_inbox_path = os.path.join(fb_path, ConvoReader.fb_inbox_path)
            convo_list.extend([os.path.join(local_fb_inbox_path, x) for x in os.listdir(local_fb_inbox_path)])

        if curr_user.has_ig and curr_user.has_fb:
            if ig_fb_matches is None:
                ig_fb_matches = ConvoReader.generate_fb_ig_convo_matches(fb_path, ig_path)

            # Remove rows with no matches
            ig_fb_matches = ig_fb_matches[ig_fb_matches['ig_path'].notna() & ig_fb_matches['fb_path'].notna()]

            # Create dictionary to enable easy name standardisation across platforms
            curr_user.ig_2_fb_names = {key: val for key, val in zip(ig_fb_matches['ig_name'].values, ig_fb_matches['fb_name'].values)}

        empty_convo_count = 0

        if curr_user.has_ig:
            local_ig_inbox_path = os.path.join(ig_path, ConvoReader.ig_inbox_path)
            
            # Only add paths for IG accounts that we have identified are not linked to Facebook accounts
            all_ig_paths = set(os.listdir(local_ig_inbox_path))
            linked_ig_paths = set(ig_fb_matches['ig_path'][ig_fb_matches['fb_path'].notna()])
            unlinked_ig_paths = all_ig_paths.difference(linked_ig_paths)
            convo_list.extend([os.path.join(local_ig_inbox_path, x) for x in unlinked_ig_paths])

        if individual_convo is not None:
            convo_list = [ConvoReader.find_individual_convo_path(individual_convo, convo_list)]

        # Extract each conversation
        logging.info("Extracting conversations:")
        for ii, convo_path in enumerate(convo_list):

            # Print out progress every 50 conversations
            if ii % 50 == 0:
                logging.info(f"\t\t{ii} / {len(convo_list)}")

            linked_ig_path = None
            if local_fb_inbox_path in convo_path and curr_user.has_ig:
                linked_ig_col = ig_fb_matches['ig_path'][ig_fb_matches['fb_path'] == os.path.basename(convo_path)]

                if linked_ig_col.shape[0] > 1:
                    raise ValueError(f"Multiple Instagram paths matched to Facebook path: {convo_path}")

                elif linked_ig_col.shape[0] == 1:
                    linked_ig_path = os.path.join(local_ig_inbox_path, linked_ig_col.iloc[0])

            curr_convo = ConvoReader.extract_single_convo(curr_user, convo_path, linked_ig_path)

            if curr_convo is not None:
                curr_user.convos[curr_convo.convo_name] = curr_convo

            else:
                empty_convo_count += 1

        logging.info(f"{empty_convo_count} conversations were empty")

        curr_user.build_sma_df()
        curr_user.get_or_create_affect_df()

        return curr_user

    @staticmethod
    def extract_jsons(file_path, field_types) -> (pd.DataFrame, bool, str, List[str]):

        # Identify all json files corresponding to conversation and add file path
        json_list = [os.path.join(file_path, x) for x in os.listdir(file_path) if
                     re.match(ConvoReader.file_name_pattern, x)]

        # Setup conversation Dataframe (to guarantee all cols exist, loop through each JSON file and append new rows
        raw_msgs_df_list = [pd.DataFrame(field_types, index=[])]

        for path in json_list:
            # Load json as string as its nesting doesn't allow direct normalisation
            try:
                with open(path) as file_obj:
                    raw_json_file_str = file_obj.read()
                    raw_json = json.loads(raw_json_file_str)

            except FileNotFoundError as err:
                print(f"File: {path} not found")
                print(err)
                return None

            # Add json normalised data to list, for performant appending once all have been collected
            raw_msgs_df_list.append(pd.json_normalize(raw_json["messages"]))

        # Ignore FutureWarning that empty df types will affect result, I explicitly want that to happen as I have set them
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw_msgs_df = pd.concat(raw_msgs_df_list)

        is_active = raw_json["is_still_participant"]
        title = raw_json["title"].encode("latin1").decode("utf-8")
        participants = [x['name'].encode("latin1").decode("utf-8") for x in raw_json["participants"]]

        # Ugly multiple return to avoid extra file I/O. Take values from last JSON as they are all consistent
        return raw_msgs_df, is_active, title, participants

    @staticmethod
    def extract_single_convo(curr_user: User, fb_path: str = None, ig_path: str = None) -> Union[Convo, None]:

        """
        Identifies all JSON files associated with a single conversation and initialises a Convo object
        :param curr_user: the current User object instance, which is being added to
        :param file_path: the path to the conversation within the Raw Data extract
        :return: a "nullable-like" Convo, in case the Convo cannot be initialised properly
        """

        msgs_df = pd.DataFrame()
        is_active = None
        title = ''
        fb_speakers = {}

        if fb_path:
            raw_fb_msgs_df, is_active, title, raw_speakers = ConvoReader.extract_jsons(fb_path,
                                                                                       ConvoReader.facebook_field_types)
            msgs_df = ConvoReader.clean_facebook_msg_data(raw_fb_msgs_df)
            msgs_df['source'] = 'Facebook'
            fb_speakers = set(msgs_df["sender_name"].unique().tolist() + raw_speakers)

        if ig_path:
            # TODO: establish Instagram field types/names (separate function may be required
            # Is active and is still participant logic doesn't really make sense (separation on one platform?)
            raw_ig_msgs_df, ig_active, ig_title, raw_speakers = ConvoReader.extract_jsons(ig_path,
                                                                                          ConvoReader.facebook_field_types)
            is_active = is_active if is_active else ig_active
            title = title if title else ig_title
            # TODO: add separate IG cleaning function
            ig_msgs_df = ConvoReader.clean_facebook_msg_data(raw_ig_msgs_df)
            ig_msgs_df['source'] = 'Instagram'

            ig_speakers = set(ig_msgs_df["sender_name"].unique().tolist() + raw_speakers)

            # Preferentially take FB sender name in two person conversations where IG name doesn't match
            # FIXME: Currently assumes user's FB and IG accounts are linked (and therefore share sender names)
            if fb_path and len(ig_speakers) == 2 and len(fb_speakers) == 2 and ig_speakers != fb_speakers:
                fb_name = list(fb_speakers.difference(ig_speakers))[0]
                ig_name = list(ig_speakers.difference(fb_speakers))[0]
                ig_msgs_df['sender_name'] = ig_msgs_df['sender_name'].replace(ig_name, fb_name)

            msgs_df = pd.concat([msgs_df, ig_msgs_df])

        convo_persons = list(msgs_df["sender_name"].unique())

        # Keep track of conversations with people who have deleted their account if there are more than the initial
        # number of messages (using proxy names), otherwise remove
        # If multiple unknown people are in the same conversation, they will likely be combined. There is little we can do
        if '' in convo_persons:
            if msgs_df.shape[0] > 2:
                for idx, val in enumerate(convo_persons):
                    if val == '':
                        curr_user.unknown_people += 1
                        new_label = f"Unknown Person #{curr_user.unknown_people}"
                        convo_persons[idx] = new_label

                        # Change their sender name, so that it aligns with speakers list
                        msgs_df['sender_name'] = msgs_df['sender_name'].replace('', new_label)
            else:
                convo_persons = [x for x in convo_persons if x != '']

        # Remove conversations where only one person has sent a message (conversations are initialised with one msg)
        if msgs_df.shape[0] <= 1:
            return None

        is_group = len(msgs_df['sender_name'].unique()) > 2

        if title == '':
            curr_user.unknown_convos += 1
            title = ', '.join([x for x in convo_persons if x != curr_user.name])

        convo = Convo(title, convo_persons, is_active, is_group, msgs_df)
        convo._pgf = ConvoReader.nqg_model.get_pgf(convo.convo_name)[0]
        if convo._pgf < ConvoReader.pgf_cutoff:
            convo.name_gender = 'Male'
        elif convo._pgf > (1 - ConvoReader.pgf_cutoff):
            convo.name_gender = 'Female'

        return convo

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
    def clean_facebook_msg_data(msgs_df: pd.DataFrame) -> pd.DataFrame:

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

        # Decode fields with potential utf-8 characters
        cleaned_df["sender_name"] = cleaned_df["sender_name"].astype(str).apply(
            lambda x: x.encode("latin1").decode("utf-8"))
        cleaned_df["text"] = cleaned_df["text"].astype(str).apply(lambda x: x.encode("latin1").decode("utf-8"))

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
            cleaned_df[col] = cleaned_df[col].apply(lambda x: len(x) if type(x) is list else 0)

        # Extract call data
        cleaned_df['missed_call'] = np.logical_and(cleaned_df['call_duration'].notna(),
                                                   cleaned_df['call_duration'] == 0)
        cleaned_df['call'] = np.logical_and(cleaned_df['call_duration'].notna(),
                                                       cleaned_df['call_duration'] > 0)

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
    def build_cache(fb_path: str, cache_root: str, user_name: str, ig_path: str = None,
                    ig_fb_matches: pd.DataFrame = None):

        cached_data = None
        full_cache_path = os.path.join(cache_root, ConvoReader.cache_file_name)
        logging.info("Building Cache")

        try:
            # Import Convos
            cached_data = ConvoReader.read_convos(user_name, fb_path, ig_path=ig_path, ig_fb_matches=ig_fb_matches)

            # Check if cache directory exists, if not create it
            pathlib.Path(cache_root).mkdir(parents=True, exist_ok=True)

            # Cache user object
            with open(full_cache_path, "wb") as file_obj:
                pickle.dump(cached_data, file_obj)

        except IOError as err:
            logging.info("Cache Build Failed")
            logging.info(err)

        else:
            logging.info("Cache Built")

        return cached_data

    @staticmethod
    def load_or_create_cache(fb_path: str, cache_root: str, user_name: str, ig_path: str = None,
                             ig_fb_match_df: pd.DataFrame = None):

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
            cached_data = ConvoReader.build_cache(fb_path, cache_root, user_name, ig_path, ig_fb_match_df)

        return cached_data

    @staticmethod
    def generate_fb_ig_convo_matches(fb_file_path: str, ig_file_path: str) -> pd.DataFrame:

        fb_inbox_path = os.path.join(fb_file_path, ConvoReader.fb_inbox_path)
        ig_inbox_path = os.path.join(ig_file_path, ConvoReader.ig_inbox_path)

        # Identify all conversations in directory
        fb_convo_df = pd.DataFrame({"fb_path": os.listdir(fb_inbox_path)})
        fb_convo_df['fb_name'] = fb_convo_df['fb_path'].str.replace(r'_\d+', '', regex=True)

        ig_convo_df = pd.DataFrame({"ig_path": os.listdir(ig_inbox_path)})
        ig_convo_df['ig_name'] = ig_convo_df['ig_path'].str.replace(r'_\d+', '', regex=True)

        return fb_convo_df.merge(ig_convo_df, left_on='fb_name', right_on='ig_name', how='outer')
