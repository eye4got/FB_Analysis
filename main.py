import datetime as dt
import logging
import os
import pathlib
import re
import shutil
import sys

from conversations import convo_visualisation
from conversations.convo_reader import ConvoReader

# logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(asctime)s - %(message)s')

sys.path.append("conversations")

# Custom Inputs, Replace with questions
root_path = os.path.join("raw_data", "facebook-rainebianchini")
output_root = "output"
cache_root = "cache"
user_name = "Raine Bianchini"


# TODO: add options for create_files?

def catch_graph_save_errs(fig, filepath, convo_name):
    # Bad practice catchall, but program shouldn't halt because of any file I/O error
    # FIXME: Check for collisions ahead of time and add custom suffix
    try:
        fig.savefig(filepath)

    except Exception as err:
        logging.warning(f"Failed to save graph for Convo: {convo_name}, due to the following: {err}")


# STARTUP
print("\nAnalysis of FaceBook Data by Raine Bianchini")
print("Version 0.1")
cached_data = ConvoReader.load_or_create_cache(root_path, cache_root, user_name)

choice_main = " "
if not cached_data:
    print("Aborting as cached data cannot be built")
    choice_main = "0"

## TODO: create output file if it doesn't exist?


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

                top_char_counts = cached_data.get_convos_ranked_by_char_ratio(desc=False, n=50)
                bottom_char_counts = cached_data.get_convos_ranked_by_char_ratio(desc=True, n=50)

                for ii, convo in enumerate(top_char_counts):
                    name, count = convo
                    print(f" {ii + 1}) {name} : {count}")

                bottom_50_start = len(cached_data.convos) - 1

                # Need to reverse list in order to keep it consistent with the above
                for ii, convo in enumerate(reversed(bottom_char_counts)):
                    index = ii + bottom_50_start
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
            print("(0)\tEscape to Top Menu\n")
            choice_graph_list = input("")

            # TIME OF DAY HISTOGRAMS
            if choice_graph_list[0] == "1":

                print("\nGenerating Time of Day Histograms")
                pathlib.Path(output_root).mkdir(parents=True, exist_ok=True)

                for ii, convo in enumerate(cached_data.convos.values()):

                    # Print out progress every 50 conversations FIXME: logging (to both console + file)
                    if ii % 50 == 0:
                        print(f"\t\t{ii} / {len(cached_data.convos)}")

                    hist_dataset = convo.get_char_counts_by_hour()
                    hist_obj = convo_visualisation.create_msg_time_hist(hist_dataset, convo.convo_name)

                    output_dir = os.path.join(output_root, convo.cleaned_name)
                    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
                    catch_graph_save_errs(hist_obj, os.path.join(output_dir, "Time of Day Histogram.jpeg"),
                                          convo.convo_name)

            # GENERATE CONVERSATION MSG COUNT TIMELINE
            elif choice_graph_list[0] == "2":

                print("\nGenerating Conversation Timeline Graphs")
                pathlib.Path(output_root).mkdir(parents=True, exist_ok=True)

                for ii, convo in enumerate(cached_data.convos.values()):

                    # Print out progress every 50 conversations FIXME: logging needs to replace this
                    if ii % 50 == 0:
                        print(f"\t\t{ii} / {len(cached_data.convos)}")

                    speakers = list(convo.speakers.keys())
                    hist_obj = convo_visualisation.create_timeline_hist(convo.convo_name, convo.msgs_df, speakers)

                    output_dir = os.path.join(output_root, convo.cleaned_name)
                    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
                    catch_graph_save_errs(hist_obj, os.path.join(output_dir, "Conversation Timeline.jpeg"),
                                          convo.convo_name)

            # GENERATE RACING BAR CHART ANIMATION
            elif choice_graph_list[0] == "3":
                config_is_correct = False
                while not config_is_correct:
                    print("Config for Racing Bar Chart Animation:")
                    print("*******************************************************")
                    print("If you enter no parameters, a default selection will be chosen for you")
                    print(
                        "[Number of bars] [Time Period for each frame] [Smoothing Window] start_dt:[Start Time] end_dt:[End Time]\n")

                    print("Number of bars: the top x number of ranked conversations to include in the chart")
                    print("\tFormat: 1-99\n")
                    print("Time Period: How many days of data to aggregate for each time period")
                    print("\tFormat: optional number then capital letter E.g. 3D, 14D\n")
                    print(
                        "Smoothing Window: How many of the time periods should be smoothed together, to make the chart readable")
                    print("\tThis parameter is optional, Format: 1-20\n")
                    print("Start Time: Filter out messages before this time (Optional Param)")
                    print("\tFormat: start_dt:YYYY-MM-DD\n")

                    print("End Time: Filter out messages after this time (Optional Param)")
                    print("\tFormat: end_dt:YYYY-MM-DD")

                    print("Recommended Config:")
                    recommended_config = f"10 14D 3 end_dt:{dt.date.today() - dt.timedelta(days=90)}"
                    print(recommended_config)
                    racing_bar_config = input("Selection: ")

                    racing_bar_config = racing_bar_config if racing_bar_config else recommended_config

                    # Only allow days because weeks/months override the origin and offset args in pandas.resample
                    config_regex = r'(\d{1,2})\s(\d{1,3}D)\s?(\d{1,2})?\s?(start_dt:\d{4}-\d{2}-\d{2})?(end_dt:\d{4}-\d{2}-\d{2})?'

                    matched_config = re.match(config_regex, racing_bar_config, re.IGNORECASE)
                    if matched_config:
                        try:
                            top_convo_num = int(matched_config[1])
                            sample_period = matched_config[2]
                            rolling_window = int(matched_config[3]) if matched_config[3] else 1
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
                            joined_sma_df = cached_data.build_sma_df(sample_period, rolling_window, start_date,
                                                                     end_date)

                            title_format_desc = f"({sample_period}ay periods, {rolling_window} period rolling window)"

                            print("\nGenerating Racing Bar Chart Animation")
                            pathlib.Path(output_root).mkdir(parents=True, exist_ok=True)
                            convo_visualisation.create_bcr_top_convo_animation(joined_sma_df, top_convo_num,
                                                                               output_root, title_format_desc)


                    elif racing_bar_config.upper().startswith('Q'):
                        config_is_correct = True
                        print("Quitting racing bar chart method")

                    else:
                        print("Config did not match format, please try again!")

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
            user_found = choice_ind_convo in cached_data.persons

            if not user_found and choice_ind_convo != "QUIT":
                print("Conversation was not found, please try again\n")

            elif user_found:
                print("\n", str(cached_data.convos[choice_ind_convo]))


    # REBUILD CACHE
    elif choice_main[0] == "4":
        shutil.rmtree(cache_root)
        logging.info("Previous Cache Deleted")
        cached_data = ConvoReader.build_cache(root_path, cache_root, user_name)

    elif choice_main[0] != "0":
        print("Incorrect command, please try again")
