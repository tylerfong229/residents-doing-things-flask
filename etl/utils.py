import pandas as pd
import numpy as np


def df_to_tuples(df: pd.DataFrame):
    """Converts dataframe to tuples to be used in HTML"""
    headings = tuple(df.columns)

    list_of_tuples = []
    for row in df.itertuples(index=False):
        tmp_tuple_row_list = []
        for i in np.arange(len(df.columns)):
            tmp_tuple_row_list.append(row[i])
        list_of_tuples.append(tuple(tmp_tuple_row_list))
    data = tuple(list_of_tuples)

    return headings, data
