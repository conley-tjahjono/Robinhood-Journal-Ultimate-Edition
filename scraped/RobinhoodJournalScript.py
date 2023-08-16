import csv
import datetime as dt
import pandas as pd
from IPython.display import display
import pprint
import math

# Extract the CSV file
file_path = 'robinhood.csv'

extracted_columns = ['Activity Date', 'Instrument',
                     'Description', 'Trans Code', 'Quantity', 'Price', 'Amount']

# Extract the data in ascending order
all_data = pd.read_csv(file_path, usecols=extracted_columns)[::-1].fillna("0")

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


def get_completed_option_orders_by_symbol(symbol=None):
    column_names = [
        'STATUS',
        'OPEN DATE',
        'CLOSE DATE',
        'INSTRUMENT',
        'DESCRIPTION',
        'SIZE',
        'ENTRY PRICE',
        'EXIT PRICE',
        'RETURN %',
        'RETURN $',
        'HOLD TIME',
        'SIDE',
        'open_order',
        'close_order'
    ]
    display_column_names = column_names[0:len(column_names)-2]
    df = pd.DataFrame(columns=display_column_names)

    # 'OEXP', 'OASGN', 'OEXCS', 'OCA' on hold
    # list of dictionaries
    open_orders = options_data[options_data['Trans Code'].isin([
        'STO', 'BTO'])].query('Instrument == @symbol').to_dict('records')
    close_orders = options_data[options_data['Trans Code'].isin([
        'STC', 'BTC', 'OEXP', 'OASGN', 'OEXCS'])].query('Instrument == @symbol').to_dict('records')

    # Creating a Dictionary: open_orders_dict
    # key = Option Description
    # value = Array of Option Orders
    open_orders_dict = {}
    for order in open_orders:
        option_id = order['Description']
        if option_id in open_orders_dict:
            open_orders_dict[option_id].append(order)
        else:
            open_orders_dict[option_id] = [order]

    # pprint.pprint(open_orders_dict)
    while len(close_orders) > 0:
        close_order = close_orders.pop()
        key = close_order['Description']
        if close_order['Trans Code'] == 'OEXP':
            key = key.replace('Option Expiration for ', "")

        # .pop() grabs the last element (Oldest older by date)
        open_order = open_orders_dict[key].pop()
        close_amount = float(close_order['Quantity'])
        open_amount = float(open_order['Quantity'])

        # if the close_order quantity is bigger than open_order
        if close_amount > open_amount:
            close_order['Quantity'] = str(close_amount - open_amount)
            # put the remaining quantity of the close order back to the end of the list
            close_orders.append(close_order)
            size = open_amount  # the amount being processed
        # if the close_order quantity is smaller than open_order
        elif close_amount < open_amount:
            open_order['Quantity'] = str(open_amount - close_amount)
            # put the remaining quantity of the open order back to the end of the list
            open_orders_dict[close_order['Description']].append(open_order)
            size = close_amount  # the amount being processed
        # if the closer_order is the same as the open_order
        else:
            size = open_amount
        print(close_order)
        # average price of the open order contract
        open_average_price = float(open_order['Price'].replace('$', ''))
        # average price of the close order contract
        print(close_order['Price'])
        close_average_price = float(close_order['Price'].replace('$', ''))

        # if the open order is a buy order
        if open_order['Trans Code'] in ['BTC', 'BTO']:
            side = 'LONG'
            # calculate the $ return and % return
            returnAmount = round(
                (close_average_price - open_average_price) * 100 * size, 2)
            returnPercentge = round(
                ((close_average_price / open_average_price) - 1) * 100, 2)
        # if the open order is a sell order
        elif open_order['Trans Code'] in ['STO', 'STC']:
            side = 'SHORT'
            # calculate the $ return and % return
            returnAmount = round(
                (open_average_price - close_average_price)*100*size, 2)
            if close_average_price == 0:
                returnPercentge = 100
            else:
                returnPercentge = round(
                    ((open_average_price / close_average_price) - 1) * 100, 2)

        # completed option trade was a win or loss based on return amount
        status = 'LOSS' if returnAmount < 0 else 'WIN'

        # how long the option contract was being held where date is held in year-month-date like 2-8-2022
        date_difference = 'IGNORE'

        new_row = {
            'STATUS': status,
            'OPEN DATE': open_order['Activity Date'],
            'CLOSE DATE': close_order['Activity Date'],
            'INSTRUMENT': open_order['Instrument'],
            'DESCRIPTION': open_order['Description'],
            'SIZE': round(size),
            'ENTRY PRICE': round(open_average_price, 2),
            'EXIT PRICE': round(close_average_price, 2),
            'RETURN %':  str(returnPercentge)+'%',
            'RETURN $': returnAmount,
            'HOLD TIME': date_difference,
            'SIDE': side,
            'open_order': open_order,
            'close_order': close_order
        }
        df = df.append(new_row, ignore_index=True)

    pprint.pprint(df[display_column_names])

def get_completed_stock_trades_by_symbol(symbol):
    # 'Buy', 'Sell',
    # 'SPL' Splits
    # 'AFEE' ADR Fee
    # 'SXCH' Share Exchange Merger
    # 'REC' Free Shares from Referral
    # 'CIL' Share Dividend??
    # list of dictionaries
    open_orders = options_data[options_data['Trans Code'].isin([
        'Buy', 'BTO'])].query('Instrument == @symbol').to_dict('records')
    close_orders = options_data[options_data['Trans Code'].isin([
        'STC', 'BTC', 'OEXP', 'OASGN', 'OEXCS'])].query('Instrument == @symbol').to_dict('records')

def get_total_profit_and_loss_by_symbol():

def get_SXCH_symbols:
    # 'SXCH'

get_completed_option_orders_by_symbol('SOFI')
