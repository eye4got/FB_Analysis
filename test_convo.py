import unittest

from convo import *


class TestConvoSide(unittest.TestCase):

    def test_create_convo_side(self):
        # Check the getter works (since it operates through the Person class)
        new_convo_side = ConvoSide(Person("James"))
        self.assertEqual(new_convo_side.get_name(), "James")

    def test_add_multi_msg(self):
        new_convo_side = ConvoSide(Person("James"))
        new_convo_side.add_block_msg_count(datetime(2020, 1, 1, 1), 2)


if __name__ == '__main__':
    unittest.main()
