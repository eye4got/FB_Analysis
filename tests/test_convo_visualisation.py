import unittest

from convo_visualisation import *


class TestConvoVisualisation(unittest.TestCase):

    def test_incorrect_shape_msg_time_hist(self):
        # Check the Message Time histogram only accepts correct shape PandasFrame
        df_wrong_rows = pd.DataFrame({"Raine": [x for x in range(23)], "Ben": [x for x in range(23)]})
        df_no_col = pd.DataFrame()

        with self.assertRaises(ValueError):
            create_msg_time_hist(df_wrong_rows, "test")

        with self.assertRaises(ValueError):
            create_msg_time_hist(df_no_col, "test")


if __name__ == "__main__":
    unittest.main()
