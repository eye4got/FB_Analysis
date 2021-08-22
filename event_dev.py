import logging
import event_reader
import pdb
from pprint import pprint as pp


root_path = "raw_data"
output_path = "output"

# reader = pickle.load(open("output/user_pickle.p","rb"))

logging.basicConfig(level=logging.DEBUG)

logging.info("initalising event reader...")
reader = event_reader.EventReader(root_path)
logging.info("...done")

logging.info("reading event invitations...")
event_invitations = reader.read_event_invitations()
logging.info("...done")

logging.debug("test")
pp(event_invitations)
