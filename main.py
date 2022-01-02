import os
import pickle
import shutil
import time

import convo_reader

# Custom Inputs, Replace with questions
root_path = os.path.join("raw_data", "facebook-2021_07_22")
output_root = "output"
cache_root = "cache"
user_name = "Raine Bianchini"
# TODO: add options for create_files?

# Constants
cache_file_name = "user_pickle.p"


def build_cache(root_path, output_root, full_cache_path, user_name):
    cached_data = None

    try:
        # Import Convos
        main_reader = convo_reader.ConvoReader(root_path, user_name)
        main_reader.read_convos(output_root)
        cached_data = main_reader.user

        # Check if cache directory exists, if not create it
        if not os.path.exists(cache_root):
            os.mkdir(cache_root)

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
    cached_data = build_cache(root_path, output_root, full_cache_path, user_name)

choice_main = " "

while choice_main[0].upper() != "0":
    print("\nFacebook Analysis Main Menu:")
    print("==============================")
    print("(1)\tList Conversations")
    print("(2)\tRebuild Cache")
    print("(0)\tQuit\n")
    choice_main = input("")

    # LIST CONVERSATIONS
    if choice_main[0] == "1":
        print(cached_data.convos.keys())
        # TODO: Add options

    # REBUILD CACHE
    elif choice_main[0] == "2":
        print("Rebuilding Cache:")

        shutil.rmtree(cache_root)
        print("\tPrevious Cache Deleted")

        rebuild_start = time.perf_counter()
        cached_data = build_cache(root_path, output_root, full_cache_path, user_name)
        rebuild_end = time.perf_counter()
        print("\tCache Rebuild Complete, Time taken:", rebuild_end - rebuild_start)

    elif choice_main[0] != "0":
        print("Incorrect command, please try again")
