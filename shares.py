import csv
import datetime as dt
import pandas as pd
from IPython.display import display
import robin_stocks.robinhood as r

from shared.myLogin import user_login as myLogin1
from shared.myLoginAlt import user_login as myLogin2
from shared.similiar_actions import *



myLogin1()
csvName = 'myStocks.csv'


# create the general option data frame format
def create_stock_df():
    column_names = [
        'STATUS',
        'OPEN DATE',
        'CLOSE DATE',
        'SYMBOL',
        'SIZE',
        'ENTRY PRICE',
        'EXIT PRICE',
        'RETURN %',
        'RETURN $',
        'HOLD TIME',
        'open_order',
        'close_order'
    ]

    display_column_names = column_names[0:len(column_names)-2]

    return pd.DataFrame(columns=column_names), display_column_names

def completed_stock_orders_with_symbol_conversion_and_option_events():
    completed_stock_orders(csvName)
    df = pd.DataFrame(stock_orders_with_symbol_conversion(csvName) + list_option_events()
                      ).sort_values(by=['date'], ascending=False).reset_index(drop=True).to_dict('records')
    return df

def completed_stock_trades_by_symbol_universal(symbol, stock_orders):
    # dataframe layout
    df, display_column_names = create_stock_df()
    # convert the option_order (list of dict) into a dataframe
    df_stock_orders = pd.DataFrame(stock_orders)
    # close orders from newest date to oldest date (descending order by date)
    close_orders = df_stock_orders.loc[(df_stock_orders['side'] == 'sell') & (
        df_stock_orders['symbol'] == symbol)].to_dict('records')
    # open orders from newest date to oldest date (descending order by date)
    open_orders = df_stock_orders.loc[(df_stock_orders['side'] == 'buy') & (
        df_stock_orders['symbol'] == symbol)].to_dict('records')
    fractional_amount = 6  # Fractional shares can be as small as 1/1000000
    # matching the close orders to open orders
    while len(close_orders) > 0:
        # .pop() grabs the last element (Oldest older by date)
        close_order = close_orders.pop()
        close_amount = round(float(close_order['quantity']), fractional_amount)
        # scenario with the free robinhood shares
        if len(open_orders) == 0:
            # print('specific', symbol)
            open_order = close_order.copy()
            open_order['average_price'] = 0
            open_order['total_price'] = 0
            open_orders.append(open_order)

        # .pop() grabs the last element (Oldest older by date)
        open_order = open_orders.pop()
        open_amount = round(float(open_order['quantity']), fractional_amount)
        # if the close_order quantity is bigger than open_order
        if close_amount > open_amount:
            close_order['quantity'] = str(close_amount - open_amount)
            # put the remaining quantity of the close order back to the end of the list
            close_orders.append(close_order)
            size = open_amount  # the amount being processed
        # if the close_order quantity is smaller than open_order
        elif close_amount < open_amount:
            open_order['quantity'] = str(open_amount - close_amount)
            # put the remaining quantity of the open order back to the end of the list
            open_orders.append(open_order)
            size = close_amount  # the amount being processed
        # if the closer_order is the same as the open_order
        else:
            size = open_amount

        # average price of the open order
        open_average_price = float(open_order['average_price'])
        # average price of the close order
        close_average_price = float(close_order['average_price'])
        returnAmount = round(
            (close_average_price - open_average_price) * size, 2)
        returnPercentge = 100 if open_average_price == 0 else round(
            ((close_average_price / open_average_price) - 1), 2)

        # completed option trade was a win or loss based on return amount
        status = 'LOSS' if returnAmount < 0 else 'WIN'

        # how long the option contract was being held where date is held in year-month-date like 2022-02-08
        date_difference = holding_amount_by_days(
            open_order['date'], close_order['date'])

        new_row = {
            'STATUS': status,
            'OPEN DATE': open_order['date'],
            'CLOSE DATE': close_order['date'],
            'SYMBOL': open_order['symbol'],
            'SIZE': round(float(size), fractional_amount),
            'ENTRY PRICE': round(open_average_price, 2),
            'EXIT PRICE': round(close_average_price, 2),
            'RETURN %':  str(returnPercentge)+'%',
            'RETURN $': returnAmount,
            'HOLD TIME': date_difference,
            'open_order': open_order,
            'close_order': close_order
        }

        df = df.append(new_row, ignore_index=True)
    # remaining open_orders that are left after all the close_orders were processed
    for open_order in open_orders:
        # open date
        open_y, open_m, open_d = [int(x)
                                  for x in open_order['date'].split('-')]
        open_date = dt.date(open_y, open_m, open_d)
        # date difference
        date_difference = (dt.date.today() - open_date).days
        new_row = {
            'STATUS': 'OPEN',
            'OPEN DATE': open_order['date'],
            'CLOSE DATE': '',
            'SYMBOL': open_order['symbol'],
            'SIZE': round(float(open_order['quantity']), fractional_amount),
            'ENTRY PRICE': round(float(open_order['average_price']), 2),
            'EXIT PRICE': None,
            'RETURN %':  None,
            'RETURN $': None,
            'HOLD TIME': date_difference,
            'open_order': open_order,
            'close_order': None,
        }
        df = df.append(new_row, ignore_index=True)
    complete_df = df.loc[df['CLOSE DATE'] != ''].sort_values(
        by=['CLOSE DATE'], ascending=False).reset_index()
    open_df = df.loc[df['CLOSE DATE'] == ''].sort_values(
        by=['OPEN DATE'], ascending=False).reset_index()
    df = pd.concat([complete_df, open_df])
    return df[display_column_names], df

def completed_stock_trades_by_symbol(symbol):
    stock_orders = completed_stock_orders_with_symbol_conversion_and_option_events()
    simple_df, complex_df = completed_stock_trades_by_symbol_universal(
        symbol, stock_orders)
    return simple_df, complex_df

def completed_stock_trades():
    stock_orders = completed_stock_orders_with_symbol_conversion_and_option_events()
    # grab all the symbols ever traded for option orders
    symbols_df = pd.DataFrame(stock_orders)[
        'symbol'].drop_duplicates().reset_index()
    # print(symbols_df)
    df, display_column_names = create_stock_df()
    for row in symbols_df['symbol']:
        # print(row)
        df_by_symbol_simple, df_by_symbol = completed_stock_trades_by_symbol_universal(
            row, stock_orders)
        df = df.append(df_by_symbol_simple)

    complete_df = df.loc[df['CLOSE DATE'] != ''].sort_values(
        by=['CLOSE DATE'], ascending=False).reset_index()
    open_df = df.loc[df['CLOSE DATE'] == ''].sort_values(
        by=['OPEN DATE'], ascending=False).reset_index()
    df = pd.concat([complete_df, open_df])
    return df[display_column_names], df

# simple_df, complex_df = completed_stock_trades_by_symbol('NIO')
simple_df, complex_df = completed_stock_trades()

display(simple_df.to_string())
print('Overall Return:', simple_df['RETURN $'].sum())

simple_df['CLOSE DATE'] = pd.to_datetime(simple_df['CLOSE DATE'])

monthly_amounts = simple_df.groupby(
    simple_df['CLOSE DATE'].dt.to_period('M'))['RETURN $'].sum()

print(monthly_amounts)
print('Overall Return:', simple_df['RETURN $'].sum())

grouped_totals = simple_df.dropna(subset=['CLOSE DATE']).groupby('SYMBOL')['RETURN $'].sum()

display(grouped_totals)
with pd.option_context('display.max_rows', None, 'display.max_columns', None):
    print(grouped_totals)