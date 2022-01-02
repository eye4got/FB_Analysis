from typing import *

from convo import Convo, Person


class User:

    def __init__(self, name: str, root_path: str):
        self.name = name
        self.root_path = root_path
        self.convos: Dict[str, Convo] = dict()
        self.persons: Dict[str, Person] = dict()

    def get_convos_ranked_by_msg_count(self, n: int = 100, no_groupchats: bool = False):
        # n is the number of convos returned, for n < 1, all results will be returned

        if no_groupchats:
            counts = [(x.msg_count, x.convo_name) for x in self.convos.values() if x.is_group == False]
        else:
            counts = [(x.msg_count, x.convo_name) for x in self.convos.values()]

        counts = sorted(counts, key=lambda x: x[0], reverse=True)

        if n > 1:
            counts = counts[:n]

        return counts

    def get_convos_ranked_by_char_ratio(self, desc: bool, n: int = 100, no_groupchats: bool = True,
                                        min_msgs: int = 200):

        ratios_list: List[Tuple[int, str]] = []
        filtered_convos = [x for x in self.convos.values() if self.name in x.speakers]

        if no_groupchats:
            filtered_convos = [x for x in filtered_convos if x.is_group == True]

        for convo in self.convos.values():
            others_speaker_count = len(convo.speakers.keys()) - 1

            if self.name in convo.speakers and convo.msg_count > (min_msgs * others_speaker_count):
                user_chars = convo.msgs_df[convo.msgs_df["sender_name"] == self.name].sum("text_len")
                others_char_count = convo.msgs_df.sum("text_len") - user_chars

                ratio = others_char_count / (user_chars * others_speaker_count)
                ratios_list.append((ratio, convo.convo_name))

        ratios_list = sorted(ratios_list, key=lambda x: x[0], reverse=desc)

        if n > 1:
            ratios_list = ratios_list[:n]

        return ratios_list

    def get_or_create_persons(self, name_list: List[str]) -> Dict[str, Person]:

        selected_persons = dict()

        for person in name_list:
            if not person in self.persons:
                self.persons[person] = Person(person)
            # Extract instances of person for assignment to avoid instance duplication
            selected_persons[person] = self.persons[person]

        return selected_persons
