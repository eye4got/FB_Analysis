import pandas as pd


def get_char_counts_by_hour(msg_df: pd.DataFrame) -> pd.DataFrame:
        # Find the msg counts for each sender, for each hour. Rename columns and fill in the blanks
        hours_series = msg_df.groupby(["sender_name", "hour_of_day"]).size().unstack(fill_value=0)
        hours_series.columns = [str(x) + ":00" for x in hours_series.columns]
        hours_series = hours_series.reindex([str(x) + ":00" for x in range(24)], axis=1, fill_value=0)
        hours_series.sort_index()

        return hours_series.T
