import convo_reader

print("Startup Commencing")
root_path = "raw_data/extract-26_04_2021"
output_path = "output"

user = convo_reader.ConvoReader(root_path, "Raine Bianchini")
test = user.extract_convo_from_name("Karratha Kommunity")
test.create_msg_time_hist()
