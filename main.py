import convo_reader

print("Startup Commencing")
root_path = "raw_data/extract-26_04_2021"
output_path = "output"

user = convo_reader.ConvoReader(root_path, output_path, "Raine Bianchini")
