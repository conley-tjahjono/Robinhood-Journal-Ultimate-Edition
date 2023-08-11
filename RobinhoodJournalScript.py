import csv
import datetime as dt
import pandas as pd
from IPython.display import display

# Extract the CSV file
file_path = 'robinhood.csv'

extracted_columns = ['Activity Date', 'Instrument',
                     'Description', 'Trans Code', 'Quantity', 'Price', 'Amount']

# Extract the data
all_data = pd.read_csv(file_path, usecols=extracted_columns)

# Filter the data into their own data frames based on filter criteria
options_data = all_data[all_data['Trans Code'].isin(
    ['STO', 'STC', 'OEXP', 'OASGN', 'BTO', 'BTC', 'OEXCS', 'OCA'])]
shares_data = all_data[all_data['Trans Code'].isin(
    ['Buy', 'Sell', 'SPL', 'OASGN', 'AFEE', 'SXCH', 'REC', 'CIL'])]
dividend_data = all_data[all_data['Trans Code'].isin(['CDIV'])]
interest_data = all_data[all_data['Trans Code'].isin(['INT'])]
gold_data = all_data[all_data['Trans Code'].isin(['GOLD'])]
stock_lending_data = all_data[all_data['Trans Code'].isin(['SLIP'])]
ach_data = all_data[all_data['Trans Code'].isin(['ACH'])]
misc_data = all_data[all_data['Trans Code'].isin(['MISC', 'ROC', 'DTAX'])]

# Completed Share Trades Based on FIFO


def get_completed_option_orders(symbol=None):
    # 'OEXP', 'OASGN', 'OEXCS', 'OCA'
    open_orders = options_data[options_data['Trans Code'].isin([
        'STO', 'BTO'])]
    close_orders = options_data[options_data['Trans Code'].isin([
        'STC', 'BTC'])]

    if symbol:
        open_orders = open_orders.query('Instrument == @symbol')
        close_orders = close_orders.query('Instrument == @symbol')
    print(open_orders)


get_completed_option_orders('SOFI')
