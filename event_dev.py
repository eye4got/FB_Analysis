import logging
import event_reader


print("Startup Commencing")
root_path = "raw_data"
output_path = "output"

# reader = pickle.load(open("output/user_pickle.p","rb"))

logging.basicConfig(level=logging.DEBUG)

logging.info("initalising event reader...")
reader = event_reader.EventReader(root_path,)
logging.info("...done")