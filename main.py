import pickle

import convo_reader

print("Startup Commencing")
root_path = "raw_data/facebook-2021_07_22"
output_path = "output"

# reader = pickle.load(open("output/user_pickle.p","rb"))

reader = convo_reader.ConvoReader(root_path, "Raine Bianchini")
reader.read_convos(output_path)

pickle.dump(reader, open("output/user_pickle.p", "wb"))
