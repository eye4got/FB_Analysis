import pickle

print("Startup Commencing")
root_path = "raw_data/facebook-2021_07_22"
output_path = "output"

reader = pickle.load(open("output/user_pickle.p", "rb"))

# reader = convo_reader.ConvoReader(root_path, "Raine Bianchini")
# reader.read_convos(output_path)
counts = reader.user.get_convos_ranked_by_msg_count(n=800)

for ii in range(1, len(counts) + 1):
    print(ii, " ", counts[ii - 1])

# pickle.dump(reader, open("output/user_pickle.p", "wb"))
