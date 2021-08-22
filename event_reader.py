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

        self.event_invitations_fn = "event_invitations.json"
        self.your_event_resposnes_fn = "your_event_responses.json"
        self.your_events_fn = "your_events_fn.json"

        self.event_invitations = list()
        self.your_event_resposnes = list()
        self.your_events = list()


    def _get_event_param(self, event: dict, param:str):
        return(event.get(param))

    def get_event_name(self, event: dict, field = "name"):
        return(self._get_event_param(event = event, param = field))
    
    def read_events(self, output_path: str, individual_event: str = None, create_Files: bool = False):
        """

        Args:
            output_path (str): 

        Returns:
            list: list of event names
        """

        self.read_event_invitations()
        self.read_your_event_responses()
        self.read_your_events()

    def _read_raw_json_file(self, fn:str):
        fp = os.path.join(self.events_path,fn)
        logging.info(f"reading in event invitations from {fp} ...")
        
        try:
            with open(fp) as file_obj:
                raw_json_file_str = file_obj.read().encode('latin1').decode('utf-8')
                raw_json = json.loads(raw_json_file_str)
                return(raw_json)
        except FileNotFoundError as err:
            logging.error(f"failed to open {fp}")
            logging.error(err)
            return None


    def read_event_invitations(self,events_loc:str = "events_invited_v2"):
        """
        Args:
            events_loc (str): name of top level in json file containing list of events

        Returns:
            list: event names
        """
        json = self._read_raw_json_file(self.event_invitations_fn)
        events_list = json.get(events_loc)

        l = [self.get_event_name(event) for event in events_list]
        return(l)



