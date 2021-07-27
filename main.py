import convo_reader

print("Startup Commencing")
root_path = "raw_data/facebook-2021_07_22"
output_path = "output"

user = convo_reader.ConvoReader(root_path, "Raine Bianchini")
user.generate_output(output_path, "Big Beans Banter Club")
