import datetime as dt
import logging
import os
import pathlib
import re
import shutil
import sys

import numpy as np
import pandas as pd
from matplotlib import use

use('TkAgg')
import matplotlib.pyplot as plt

from conversations import convo_visualisation
from conversations.convo_reader import ConvoReader

# logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(asctime)s - %(message)s')

# Silence MatplotLib INFO warnings
mlogger = logging.getLogger('matplotlib')
mlogger.setLevel(logging.WARNING)

# Make modules accessible through convenient names
sys.path.append("conversations")

# Custom Inputs, Replace with questions
fb_root_path = os.path.join("raw_data", "facebook", "fb-27_04_2024-msgs")
ig_root_path = os.path.join("raw_data", "instagram")
output_root = "output"
cache_root = "cache"
user_name = "Raine Bianchini"
min_msgs = 50

manual_match_file_path = os.path.join("raw_data", "ig_fb_mapping.csv")


# TODO: add input for timezone
# TODO: add options for create_files?
# TODO: add min messages cut off for conversations of interest and reduce wasted compute on tiny conversations
# TODO: add enagement score (including call times and add logarithmic points for high char, GIFs etc)

def save_graph_catch_errs(fig, filepath, convo_name):
    # Bad practice catchall, but program shouldn't halt because of any file I/O error
    # FIXME: Check for collisions ahead of time and add custom suffix
    try:
        fig.savefig(filepath)

    except Exception as err:
        logging.warning(f"Failed to save graph for Convo: {convo_name}, due to the following: {err}")
        

def ensure_output_dir(output_root: str, folder: str) -> str:
    output_dir = os.path.join(os.path.abspath(output_root), folder)
    
    # On windows, use file prefix to bypass 260 filepath char limit, needs to be outside os.path.join to work
    if sys.platform == 'win32':
        output_dir = r'//?/' + output_dir
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    return output_dir


# STARTUP
print("\nAnalysis of FaceBook Data by Raine Bianchini")
print("Version 0.1")

matching_df = None
if os.path.isfile(manual_match_file_path):
    matching_df = pd.read_csv(manual_match_file_path)

cached_data = ConvoReader.load_or_create_cache(fb_root_path, cache_root, user_name,
                                               ig_path=ig_root_path, ig_fb_match_df=matching_df)

choice_main = " "
if not cached_data:
    print("Aborting as cached data cannot be built")
    choice_main = "0"

# TODO: create output file if it doesn't exist?


while choice_main[0] != "0":
    print("\nFacebook Analysis Main Menu:")
    print("==============================")
    print("(1)\tList Top Conversations")
    print("(2)\tGenerate Graphs")
    print("(3)\tSearch Specific Conversation")
    print("(4)\tRebuild Cache")
    print("(0)\tQuit\n")
    choice_main = input("")

    # LIST CONVERSATIONS
    if choice_main[0] == "1":

        choice_convo_list = " "

        while choice_convo_list[0] != "0":
            print("\nConversation List Menu:")
            print("(1)\tList by Message Counts")
            print("(2)\tList by Character Ratio")
            print("(0)\tEscape to Top Menu\n")
            choice_convo_list = input("")

            if choice_convo_list[0] == "1":
                msg_counts = cached_data.get_convos_ranked_by_msg_count()

                for ii, convo in enumerate(msg_counts):
                    print(" ", ii + 1, ") ", convo[0], ": ", convo[1], sep="")

            elif choice_convo_list[0] == "2":

                print("Ratio: [Others Char Count] / ([Your Char Count] * [Others Speaker Count])")
                print("\tHigh Char Ratio -> Your friends dominate the conversation")
                print("\tLow Char Ratio -> You dominate the conversation\n")

                top_n = 20
                print(
                    f"Displaying top and bottom {top_n}, conversations which don't meet min message count are excluded")

                char_counts = cached_data.get_convos_ranked_by_char_ratio(desc=False, n=-1)
                top_char_counts = char_counts[:top_n] + char_counts[-top_n:] if len(
                    char_counts) > 2 * top_n else char_counts

                for ii, convo in enumerate(top_char_counts[:len(top_char_counts) // 2]):
                    name, count = convo
                    print(f" {ii + 1}) {name} : {count}")

                offset = max(len(char_counts) - top_n, len(top_char_counts) // 2)

                for ii, convo in enumerate(top_char_counts[len(top_char_counts) // 2:]):
                    index = ii + offset
                    name, count = convo
                    print(f" {index}) {name} : {count}")

            elif choice_convo_list[0] != "0":
                print("Incorrect command, please try again")


    # GENERATE GRAPHS
    elif choice_main[0] == "2":
        choice_graph_list = " "

        while choice_graph_list[0] != "0":
            print("\nGraph List Menu:")
            print("(1)\tTime of Day Histograms")
            print("(2)\tConversation Timelines")
            print("(3)\tRacing Bar Chart Animation")
            print("(4)\tSentiment Distribution Comparison Graphs")
            print("(5)\tSentiment Quadrant Interactive Graphs")
            print("(0)\tEscape to Top Menu\n")
            choice_graph_list = input("")

            # TIME OF DAY HISTOGRAMS
            if choice_graph_list[0] == "1":

                print("\nGenerating Time of Day Histograms")
                pathlib.Path(output_root).mkdir(parents=True, exist_ok=True)

                for ii, convo in enumerate(cached_data.convos.values()):

                    # Print out progress every 50 conversations FIXME: logging (to both console + file)
                    if ii % 50 == 0: print(f"\t\t{ii} / {len(cached_data.convos)}")
                        
                    # Skip empty convos
                    if convo.msg_count < min_msgs or len(convo.speakers) < 2: continue

                    hist_dataset = convo.get_char_counts_by_hour()
                    hist_obj = convo_visualisation.create_msg_time_hist(hist_dataset, convo.convo_name)

                    output_dir = ensure_output_dir(output_root, convo.cleaned_name)
                    save_graph_catch_errs(hist_obj, os.path.join(output_dir, "Time of Day Histogram.jpeg"),
                                          convo.convo_name)

            # GENERATE CONVERSATION MSG COUNT TIMELINE
            elif choice_graph_list[0] == "2":

                print("\nGenerating Conversation Timeline Graphs")
                pathlib.Path(output_root).mkdir(parents=True, exist_ok=True)

                for ii, convo in enumerate(cached_data.convos.values()):
                    
                    # Print out progress every 50 conversations
                    if ii % 50 == 0: print(f"\t\t{ii} / {len(cached_data.convos)}")
                    
                    # Skip empty convos
                    if convo.msg_count < min_msgs or len(convo.speakers) < 2: continue

                    hist_obj = convo_visualisation.create_timeline_hist(convo.convo_name, convo.msgs_df, convo.speakers)
                    output_dir = ensure_output_dir(output_root, convo.cleaned_name)
                    save_graph_catch_errs(hist_obj, os.path.join(output_dir, "Conversation Timeline.jpeg"),
                                          convo.convo_name)

            # GENERATE RACING BAR CHART ANIMATION
            elif choice_graph_list[0] == "3":
                config_is_correct = False
                while not config_is_correct:
                    print("Config for Racing Bar Chart Animation:")
                    print("*******************************************************")
                    print("If you enter no parameters, a default selection will be chosen for you")
                    print(
                        "[Number of bars] [Time Period for each frame] [Frame Length] start_dt:[Start Time] end_dt:[End Time]\n")

                    print("Number of bars: the top x number of ranked conversations to include in the chart")
                    print("\tFormat: 1-99\n")
                    print("Time Period: How many days of data to aggregate for each time period")
                    print("\tFormat: optional number then capital letter E.g. 3D, 14D\n")
                    print(
                        "Frame Length: Milliseconds per period (frames are interpolated across this period)")
                    print("\tThis parameter is optional, Format: 0-9999\n")
                    print("Start Time: Filter out messages before this time (Optional Param)")
                    print("\tFormat: start_dt:YYYY-MM-DD\n")

                    print("End Time: Filter out messages after this time (Optional Param)")
                    print("\tFormat: end_dt:YYYY-MM-DD")

                    print("Recommended Config:")
                    recommended_config = f"8 30D 1250"
                    print(recommended_config)
                    racing_bar_config = input("Selection: ")

                    racing_bar_config = racing_bar_config if racing_bar_config else recommended_config

                    # Only allow days because weeks/months override the origin and offset args in pandas.resample
                    config_regex = r'(\d{1,2})\s(\d{1,3}D)\s?(\d{1,4})?\s?(start_dt:\d{4}-\d{2}-\d{2})?\s?(end_dt:\d{4}-\d{2}-\d{2})?'

                    matched_config = re.match(config_regex, racing_bar_config, re.IGNORECASE)
                    if matched_config:
                        try:
                            top_convo_num = int(matched_config[1])
                            sample_period = matched_config[2]
                            frame_length = int(matched_config[3]) if matched_config[3] else 1250
                            start_date = None
                            end_date = None

                            if matched_config[4]:
                                start_date = dt.datetime.fromisoformat(matched_config[4].replace('start_dt:', ''))
                                print(f"\tStart Date Found: {start_date}")

                            if matched_config[5]:
                                end_date = dt.datetime.fromisoformat(matched_config[5].replace('end_dt:', ''))
                                print(f"\tEnd Date Found: {end_date}")
                        except Exception as err:
                            print("\nIncorrect config:")
                            print(err)
                        else:
                            config_is_correct = True
                            print("\nCleaning data .... \n")
                            joined_sma_df = cached_data.build_sma_df(sample_period, start_date, end_date)

                            title_format_desc = f"({sample_period}ay Periods with Interpolation"
                            start_date_str = f"_start_{start_date.date()}" if start_date else ""
                            end_date_str = f"_end_{end_date.date()}" if end_date else ""
                            output_file_name = f"fb_history_{sample_period}_{frame_length}ms{start_date_str}{end_date_str}.mp4"
                            output_path = os.path.join(output_root, output_file_name)

                            print("\nGenerating Racing Bar Chart Animation")
                            pathlib.Path(output_root).mkdir(parents=True, exist_ok=True)
                            convo_visualisation.create_bcr_top_convo_animation(joined_sma_df, top_convo_num,
                                                                               frame_length,
                                                                               output_path, title_format_desc)


                    elif racing_bar_config.upper().startswith('Q'):
                        config_is_correct = True
                        print("Quitting racing bar chart method")

                    else:
                        print("Config did not match format, please try again!")

            # GENERATE SENTIMENT SAMPLE VS POPULATION DISTRIBUTION COMPARISON GRAPHS
            elif choice_graph_list[0] == "4":
                config_is_correct = False
                while not config_is_correct:
                    print("Config for Sentiment Distribution Comparisons:")
                    print("*******************************************************")
                    print("If you enter parameters, you will regenerate sentiment scores for all conversations")
                    print("[Time Period for each datapoint] [Min characters per Period] [Min periods]\n")

                    print("Time Period: How many days of data to aggregate for each time period")
                    print("\tFormat: optional number then capital letter E.g. 3D, 14D\n")
                    print("Min Characters: Filter out periods with less than this number of characters")
                    print("\tFormat: integer greater than 1 \n")
                    print(
                        "Min Periods: Exclude convos with less than this number of periods, as a distribution cannot be established")
                    print("\tFormat: integer greater than 1 \n")

                    print("Recommended Config:")
                    recommended_config = f"3D 500 20"
                    print(recommended_config)
                    sentiment_dist_config = input("Selection: ")

                    if sentiment_dist_config:

                        # Only allow days because weeks/months override the origin and offset args in pandas.resample
                        config_regex = r'(\d{1,3}D)\s(\d*)\s(\d*)'

                        matched_config = re.match(config_regex, sentiment_dist_config, re.IGNORECASE)
                        if matched_config:
                            try:
                                sample_period = matched_config[1]
                                min_char_num = int(matched_config[2])
                                min_period_count = int(matched_config[3])

                            except Exception as err:
                                print("\nIncorrect config:")
                                print(err)
                            else:
                                print("\nCleaning data .... \n")
                                cached_data.get_or_create_affect_df(
                                    force_refresh=True,
                                    agg_period=sample_period,
                                    min_period_char=min_char_num,
                                    min_periods=min_period_count,
                                    exclude_txt=True
                                )

                    config_is_correct = True

                    # TODO: consider shifting glue code into function
                    full_df = cached_data.get_or_create_affect_df()
                    full_df = full_df[~full_df['exclude_convo']].copy()

                    no_groups_df = full_df[~full_df['is_groupchat']].copy()

                    user_receiver_mask = full_df['sender_name'].eq(user_name)
                    user_df = full_df[user_receiver_mask].copy().reset_index()
                    receiver_df = full_df[~user_receiver_mask].copy().reset_index()

                    pathlib.Path(output_root).mkdir(parents=True, exist_ok=True)

                    print("Generating distribution graphs ...")

                    for ii, (convo_name, convo) in enumerate(cached_data.convos.items()):

                        # Print out progress every 50 conversations
                        if ii % 50 == 0:
                            print(f"\t\t{ii} / {len(cached_data.convos)}")

                        receiver_df['receiver_cat'] = np.where(receiver_df['receiver_name'] != convo_name, 'Population',
                                                               convo_name)

                        # Check if the conversation was excluded and if so, don't generate a graph for it
                        if receiver_df['receiver_cat'].nunique() < 2: continue

                        user_df['user_cat'] = np.where(user_df['receiver_name'] != convo_name, 'Population', convo_name)

                        signs_dist_obj = convo_visualisation.create_sentiment_dist_comparison(user_df, receiver_df,
                                                                                              convo_name,
                                                                                              cached_data.name,
                                                                                              ["pos", "neg"])
                        compound_dist_obj = convo_visualisation.create_sentiment_dist_comparison(user_df, receiver_df,
                                                                                                 convo_name,
                                                                                                 cached_data.name,
                                                                                                 ["compound"])

                        output_dir = ensure_output_dir(output_root, convo.cleaned_name)
                        save_graph_catch_errs(signs_dist_obj,
                                              os.path.join(output_dir, "Sentiment Distribution Raw Comparison.jpeg"),
                                              convo.convo_name)
                        save_graph_catch_errs(compound_dist_obj,
                                              os.path.join(output_dir,
                                                           "Sentiment Distribution Compound Comparison.jpeg"),
                                              convo.convo_name)

            # GENERATE SENTIMENT QUADRANT INTERACTIVE GRAPHS

            elif choice_graph_list[0] == "5":
                full_df = cached_data.get_or_create_affect_df()
                filter_mask = np.logical_or(full_df['is_groupchat'], full_df['exclude_convo'])
                filtered_df = full_df[~filter_mask].copy()

                user_receiver_mask = filtered_df['sender_name'].eq(user_name)
                user_df = filtered_df[user_receiver_mask].copy().reset_index()
                receiver_df = filtered_df[~user_receiver_mask].copy().reset_index()

                pathlib.Path(output_root).mkdir(parents=True, exist_ok=True)

                print("Generating interactive summary graph:")

                agg_methods = {'neg': 'mean', 'pos': 'mean', 'name_gender': 'first'}

                user_means_df = user_df[['receiver_name', 'neg', 'pos', 'name_gender']].groupby(
                    ['receiver_name']).agg(
                    agg_methods).reset_index().rename(columns={'receiver_name': 'name'})

                receiver_means_df = receiver_df[['sender_name', 'neg', 'pos', 'name_gender']].groupby(
                    ['sender_name']).agg(
                    agg_methods).reset_index().rename(columns={'sender_name': 'name'})

                plt.ion()
                user_fig = convo_visualisation.create_sentiment_quadrant_graph(user_means_df, "User Behaviour Scores")
                plt.show(block=True)
                receiver_fig = convo_visualisation.create_sentiment_quadrant_graph(receiver_means_df,
                                                                                   "Recipient Behaviour Scores")
                plt.show(block=True)
                plt.ioff()

            elif choice_graph_list[0] != "0":
                print("Incorrect command, please try again")

    # SEARCH FOR SPECIFIC CONVERSATION
    elif choice_main[0] == "3":

        user_found = False
        choice_ind_convo = ""
        print("\nIndividual Conversation Search")
        print("==============================")

        while choice_ind_convo != "QUIT":
            choice_ind_convo = input("\nConvo to Search For (Type QUIT to exit):")
            # TODO: allow some similarity based suggestions upon failure
            user_found = choice_ind_convo in cached_data.convos.keys()

            if not user_found and choice_ind_convo != "QUIT":
                print("Conversation was not found, please try again\n")

            elif user_found:
                print("\n", str(cached_data.convos[choice_ind_convo]))


    # REBUILD CACHE
    elif choice_main[0] == "4":
        shutil.rmtree(cache_root)
        logging.info("Previous Cache Deleted")

        matching_df = None
        if os.path.isfile(manual_match_file_path):
            matching_df = pd.read_csv(manual_match_file_path)
        cached_data = ConvoReader.build_cache(fb_root_path, cache_root, user_name, ig_path=ig_root_path,
                                              ig_fb_matches=matching_df)

    elif choice_main[0] != "0":
        print("Incorrect command, please try again")
