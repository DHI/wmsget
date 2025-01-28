import os
from pyogrio import read_dataframe

def read_grid(gridname):
    return read_dataframe(os.path.join(os.path.dirname(__file__), gridname))