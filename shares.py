import csv
import datetime as dt
import pandas as pd
from IPython.display import display
import robin_stocks.robinhood as r

from shared.myLogin import user_login as myLogin1
from shared.myLoginAlt import user_login as myLogin2
from shared.similiar_actions import *

myLogin1()

get_stock_splits();

#Get all Stock Orders
