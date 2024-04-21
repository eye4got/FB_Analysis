import os
import re
from typing import *

import nltk
import pandas as pd
import unicodedata
# from django.utils.text import slugify
from tabulate import tabulate

nltk.download('vader_lexicon')
from nltk.sentiment.vader import SentimentIntensityAnalyzer


class Person:

    def __init__(self, name: str):
        self.name = name


class Convo:
    count_cols = {
        'sender_name': 'Messages',
        'text_len': 'Character Count',
        'photos': 'Photos',
        'call_duration': 'Call Time (Min)',
        'successful_call': 'Successful Calls',
        'missed_call': 'Missed Calls',
        'videos': 'Videos',
        'gifs': 'GIFs',
        'files': 'Files',
        'share_link': 'Links',
        'sticker_path': 'Stickers',
        'audio_files': 'Voice Memos'
    }

    def __init__(self, name: str, speakers: Dict[str, Person], is_active: bool, is_group: bool,
                 messages_df: pd.DataFrame):
        self.convo_name = name
        # For file paths and similar restricted character sets
        speakers_excl_user = [key for key, val in speakers.items() if key != name]
        cleaned_name = Convo.sanitise_text(name) or Convo.sanitise_text(', '.join(speakers_excl_user))
        if cleaned_name == '':
            raise ValueError(
                f'The following conversation name was converted to empty text when trying to clean to create the filepath: {name}')

        self.cleaned_name = cleaned_name
        self.speakers = speakers
        self.start_time = messages_df.index[0]
        self.is_active = is_active
        self.is_group = is_group
        self.msg_count = messages_df.shape[0]
        self.msgs_df = messages_df

        # Guess 'gender' based on name to avoid extensive data entry
        self._pgf = -1  # Retain logistic regression result to enable troubleshooting (set default value)
        self.name_gender = 'Uncertain'

        # Add categorical hour of day column
        self.msgs_df['hour_of_day'] = self.msgs_df.index.map(lambda x: x.hour)

        # Create character counts for each message
        self.msgs_df['text_len'] = self.msgs_df['text'].apply(lambda x: len(x) if type(x) == str else 0)


    def __str__(self) -> str:
        output = f'''Conversation Name: {self.convo_name}\n
                     Participants: {', '.join(self.speakers.keys())}\n\n'''

        subset_cols = ['sender_name', 'text_len', 'photos', 'share_link', 'sticker_path', 'call_duration',
                       'successful_call', 'missed_call', 'videos', 'files', 'audio_files', 'gifs']
        reaction_cols = [x for x in self.msgs_df.columns if '_reaction' in x]
        subset_cols.extend(reaction_cols)

        # Media Columns have counts of elements per message, need to sum these instead of counting
        # Most columns just need to be counted (how many links, stickers etc)
        sum_cols = ['photos', 'videos', 'audio_files', 'files', 'missed_call', 'successful_call', 'text_len',
                    'call_duration']
        agg_method = {col: ['count'] if col not in sum_cols else ['sum'] for col in subset_cols}

        # Apply aggregation methods determined by above dict
        counts_df = self.msgs_df[subset_cols].groupby('sender_name').agg(agg_method)

        counts_df['call_duration'] = (counts_df['call_duration'] / 60).round(1)  # Convert from seconds to minutes

        # Collapse multi-index columns, rename using class field dictionary and prettified reaction cols
        cleaned_reaction_cols = [x.replace('_', ' ').title() for x in reaction_cols]
        renamed_count_cols = {**Convo.count_cols, **dict(zip(reaction_cols, cleaned_reaction_cols))}

        counts_df.columns = counts_df.columns.get_level_values(0)
        counts_df.rename(columns=renamed_count_cols, inplace=True)

        output += tabulate(counts_df, headers=counts_df.columns, intfmt=",")

        return output

    def get_char_counts_by_hour(self) -> pd.DataFrame:
        '''
        :return: A data frame containing the msg counts for each speaker (columns) for each hour of the day (rows)
        '''

        # Find the msg counts for each sender, for each hour. Rename columns and fill in the blanks
        hours_series = self.msgs_df.groupby(['sender_name', 'hour_of_day']).size().unstack(fill_value=0)
        hours_series.columns = [str(x) + ':00' for x in hours_series.columns]
        hours_series = hours_series.reindex([str(x) + ':00' for x in range(24)], axis=1, fill_value=0)
        hours_series.sort_index()

        return hours_series.T

    def build_sentiment_analysis_df(self, user_name: str, sample_period: str, min_period_char: int,
                                    min_periods: int = 5, exclude_txt=True) -> [pd.DataFrame, None]:

        # Leave field empty for convos with <100 messages
        if self.msgs_df.shape[0] < 100: return None

        df = self.msgs_df.copy()

        # Transform to suitable format
        df['text'] = df['text'].astype(str)
        period_msgs_df = (df.query("text_len > 0")
                          .loc[:, ('sender_name', 'text')]
                          .groupby(['sender_name'])
                          .resample(sample_period)
                          .agg({'text': ' '.join})

                          # Filter only for periods that meet the minimum character requirement for the period
                          .query(f"text.str.len() >= {min_period_char}")

                          # Remove empty periods that resample adds
                          .dropna()
                          .reset_index()
                          )

        period_msgs_df['exclude_convo'] = False

        # If the data frame is empty, return nothing. If it has too few periods, exclude from ranking but not benchmarking
        user_msgs_df = period_msgs_df[period_msgs_df['sender_name'] == user_name]
        if user_msgs_df.shape[0] == 0:
            return None

        # Minimum periods that the user must be involved in, to justify including in benchmark
        if user_msgs_df.shape[0] < min_periods:
            period_msgs_df['exclude_convo'] = True

        vader_results = period_msgs_df['text'].apply(
            lambda x: pd.Series(SentimentIntensityAnalyzer().polarity_scores(x)))
        period_msgs_df = period_msgs_df.join(vader_results)

        period_msgs_df['text_len'] = period_msgs_df['text'].str.len()

        if exclude_txt:
            # Drop massive swathes of text to reduce size (vader compound score and dates is all we often need)
            period_msgs_df = period_msgs_df.drop(columns=['text'])

        return period_msgs_df

    # Following function was stolen from https://github.com/pallets/werkzeug/blob/a3b4572a34269efaca4d91fa4cd07dd7f6f94b6d/src/werkzeug/utils.py#L174-L218
    # As I didn't want to install their entire package or alternatives such as Django
    @staticmethod
    def sanitise_text(text: str) -> str:
        r'''Pass it text and it will return a cleaned and formatted version

        :param text: the text to clean
        '''
        windows_device_files = (
            'CON',
            'AUX',
            'COM1',
            'COM2',
            'COM3',
            'COM4',
            'LPT1',
            'LPT2',
            'LPT3',
            'PRN',
            'NUL',
        )

        filename = unicodedata.normalize('NFKD', text).encode("ascii", "ignore").decode("ascii")

        for sep in os.path.sep, os.path.altsep:
            if sep:
                filename = filename.replace(sep, ' ')

        # Remove illegal chars
        filename = str(re.compile(r'[/\\<>:"|?*]').sub('', filename)).strip('._')

        # Convert all whitespace to a single space character
        filename = re.compile(r'\s+').sub(' ', filename).strip()

        # on nt a couple of special files are present in each folder.  We
        # have to ensure that the target file is not such a filename.  In
        # this case we prepend an underline
        if (
                os.name == 'nt'
                and filename
                and filename.split('.')[0].upper() in windows_device_files
        ):
            filename = f'_{filename}'

        # Avoid exceeding windows char limit (plus some buffer for avoiding collisions)
        if len(filename) > 250:
            filename = filename[:250]

        return filename
