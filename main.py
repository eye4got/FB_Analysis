import convo_reader

print("Startup Commencing")
root_path = "raw_data/extract-26_04_2021"
output_path = "output"

# TODO: Consider type hints?

user = convo_reader.ConvoReader(root_path, output_path, "Raine Bianchini")