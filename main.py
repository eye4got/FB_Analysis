import os
import pathlib
import pickle
import shutil

import convo_visualisation
from convo_reader import ConvoReader

# Custom Inputs, Replace with questions
root_path = os.path.join("raw_data", "facebook-2022-01-02")
output_root = "output"
cache_root = "cache"
user_name = "Raine Bianchini"
# TODO: add options for create_files?

# Constants
cache_file_name = "user_pickle.p"


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


# STARTUP
print("\nAnalysis of FaceBook Data by Raine Bianchini")
print("Version 0.1")
full_cache_path = os.path.join(cache_root, cache_file_name)

## TODO: create output file if it doesn't exist?

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
    cached_data = build_cache(root_path, cache_root, full_cache_path, user_name)

choice_main = " "

while choice_main[0] != "0":
    print("\nFacebook Analysis Main Menu:")
    print("==============================")
    print("(1)\tList Top Conversations")
    print("(2)\tGenerate Msg Time of Day Histograms")
    print("(3)\tGenerate Conversation Timeline")
    print("(4)\tSearch Specific Conversation")
    print("(5)\tRebuild Cache")
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


    # GENERATE TIME OF DAY HISTOGRAMS
    elif choice_main[0] == "2":

        print("\nGenerating Time of Day Histograms")
        pathlib.Path(output_root).mkdir(parents=True, exist_ok=True)

        for ii, convo in enumerate(cached_data.convos.values()):

            # Print out progress every 50 conversations FIXME: logging needs to replace this
            if ii % 50 == 0:
                print(f"\t\t{ii} / {len(cached_data.convos)}")

            hist_dataset = convo.get_char_counts_by_hour()
            hist_obj = convo_visualisation.create_msg_time_hist(hist_dataset, convo.convo_name)

            output_dir = os.path.join(output_root, convo.cleaned_name)
            pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
            hist_obj.savefig(os.path.join(output_dir, "Time of Day Histogram.jpeg"))


    # GENERATE CONVERSATION MSG COUNT TIMELINE
    elif choice_main[0] == "3":

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
            hist_obj.savefig(os.path.join(output_dir, "Conversation Timeline.jpeg"))


    # SEARCH FOR SPECIFIC CONVERSATION
    elif choice_main[0] == "4":

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
    elif choice_main[0] == "5":

        shutil.rmtree(cache_root)
        print("\nPrevious Cache Deleted")

        cached_data = build_cache(root_path, cache_root, full_cache_path, user_name)

    elif choice_main[0] != "0":
        print("Incorrect command, please try again")
