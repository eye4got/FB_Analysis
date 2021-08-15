import os.path
import logging
import json

class EventReader:
    """
    """

    def __init__(self, root_path: str):
        self.events_folder = "events"
        self.events_path = os.path.join(root_path, self.events_folder)
        logging.debug(f"events path = {self.events_path}")

        self.event_invitations_fn = "event_invitations"
        self.your_event_resposnes_fn = "your_event_responses"
        self.your_events_fn = "your_events_fn"

        self.event_invitations = list()
        self.your_event_resposnes = list())
        self.your_events = list()


        
    
    def read_events(self, output_path: str, individual_event: str = None, create_Files: bool = False):
        """
        """

        self.read_event_invitations()
        self.read_your_event_responses()
        self.read_your_events()
    
    def read_event_invitations(self):

        fp = os.path.join(self.events_path,self.event_invitations_fn)
        logging.info(f"reading in event invitations from {fp} ...")
        
        try:
            with open(fp) as file_obj:
                raw_json_file_str = file_obj.read().encode('latin1').decode('utf-8')
                raw_json = json.loads(raw_json_file_str)
        except FileNotFoundError as err:
            logging.error(f"failed to open {fp}")
            logging.error(err)
            return None


