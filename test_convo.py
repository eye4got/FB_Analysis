import unittest
from convo import *
from typing import no_type_check


class TestConvoSide(unittest.TestCase):

    # noinspection PyTypeChecker
    @no_type_check
    def test_create_convo_side(self):
        # Make sure that you cannot define a conversation side with
        # a string not a Person
        with self.assertRaises(ValueError):
            ConvoSide("James")

        # Check the getter works (since it operates through the Person class)
        new_convo_side = ConvoSide(Person("James"))
        self.assertEqual(new_convo_side.get_name(), "James")

    def test_add_multi_msg(self):
        new_convo_side = ConvoSide(Person("James"))
        new_convo_side.add_block_msg_count(2, datetime.datetime(2020, 1, 1, 1))

if __name__ == '__main__':
    unittest.main()
