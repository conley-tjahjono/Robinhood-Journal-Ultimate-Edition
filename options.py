import csv
import datetime as dt
import pandas as pd
from IPython.display import display
import robin_stocks.robinhood as r
from shared.myLogin import user_login as myLogin1
from shared.myLoginAlt import user_login as myLogin2
from shared.similiar_actions import *
from flask import Flask, request, jsonify

app = Flask(__name__)

myLogin1()
csvName = 'myStocks.csv'

DEFAULT_COLUMNS = [
    'STATUS',
    'OPEN DATE',
    'CLOSE DATE',
    'SYMBOL',
    'STRIKE',
    'EXPIRE',
    'OPTION TYPE',
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

# create the general option data frame format
def create_option_df():
    column_names = DEFAULT_COLUMNS.copy()
    display_column_names = column_names[0:len(column_names)-2]
    return pd.DataFrame(columns=column_names), display_column_names

# export completed option orders into a csv file from newest to oldest orders
def completed_option_orders():
    # keys for all_orders
    # dict_keys(['cancel_url', 'canceled_quantity', 'created_at', 'direction', 'id', 'legs',
    # 'pending_quantity', 'premium', 'processed_premium', 'price', 'processed_quantity',
    # 'quantity', 'ref_id', 'state', 'time_in_force', 'trigger', 'type', 'updated_at', 'chain_id',
    # 'chain_symbol', 'response_category', 'opening_strategy', 'closing_strategy', 'stop_price', 'form_source'])

    file_path = r.export.create_absolute_csv('.', csvName, 'option')
    all_orders = r.get_all_option_orders()
    with open(file_path, 'w', newline='') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow([
            'symbol',
            'order_id',
            'option_id',
            'expiration_date',
            'strike_price',
            'position_effect',
            'option_type',
            'side',
            'order_created_at',
            'time',
            'direction',
            'quantity',
            'average_price',
            'order_type',
            'opening_strategy',
            'closing_strategy',
            'total_price',
            'processed_premium'
        ])
        for order in all_orders:
            if order['state'] == 'filled':
                for leg in order['legs']:
                    for execution in leg['executions']:
                        date_and_time = order['created_at'].split('T')
                        csv_writer.writerow([  # 17 columns
                            order['chain_symbol'],
                            order['id'],
                            leg['option'],
                            leg['expiration_date'],
                            leg['strike_price'],
                            leg['position_effect'],
                            leg['option_type'],
                            leg['side'],
                            date_and_time[0],
                            date_and_time[1],
                            order['direction'],
                            execution['quantity'],
                            execution['price'],
                            order['type'],
                            order['opening_strategy'],
                            order['closing_strategy'],
                            str(float(execution['price']) * \
                                float(execution['quantity']) * 100),
                            order['processed_premium']
                        ])
        f.close()

# total profit/loss of all noncompleted option trades
def noncompleted_option_trades():
    # completed_option_orders()
    option_orders = option_orders_with_symbol_conversion(
        csvName)

    # get a list of all the buy_orders and sell_orders from the list of option_orders
    df_option_orders = pd.DataFrame(option_orders)

    sell_orders = df_option_orders.loc[(
        df_option_orders['side'] == 'sell'), 'total_price']
    buy_orders = df_option_orders.loc[(
        df_option_orders['side'] == 'buy'), 'total_price']

    sell_orders = pd.to_numeric(sell_orders)
    buy_orders = pd.to_numeric(buy_orders)

    premium = sell_orders['total_price'] - buy_orders['total_price']

    return premium

# total profit/loss of all noncompleted option trades by symbol
def noncompleted_option_trades_by_symbol(symbol, option_orders):
    # completed_option_orders()
    # option_orders = similiar_actions.option_orders_with_symbol_conversion(csvName)

    # get a list of all the buy_orders and sell_orders from the list of option_orders
    df_option_orders = pd.DataFrame(option_orders)

    sell_orders = df_option_orders.loc[(df_option_orders['side'] == 'sell') & (
        df_option_orders['symbol'] == symbol), 'total_price']
    buy_orders = df_option_orders.loc[(df_option_orders['side'] == 'buy') & (
        df_option_orders['symbol'] == symbol), 'total_price']

    sell_orders = pd.to_numeric(sell_orders)
    buy_orders = pd.to_numeric(buy_orders)

    premium = sell_orders.sum() - buy_orders.sum()

    return premium

# Subfunction of all completed option trades by symbol
def completed_option_trades_by_symbol_universal(symbol, option_orders):
    # dataframe layout
    df, display_column_names = create_option_df()
    # convert the option_order (list of dict) into a dataframe
    df_option_orders = pd.DataFrame(option_orders)

    # close orders from newest date to oldest date (descending order by date)
    close_orders = df_option_orders.loc[(df_option_orders['position_effect'] == 'close') & (
        df_option_orders['symbol'] == symbol)].to_dict('records')
    # open orders from newest date to oldest date (descending order by date)
    open_order_not_filtered = df_option_orders.loc[(df_option_orders['position_effect'] == 'open') & (
        df_option_orders['symbol'] == symbol)].to_dict('records')

    # get a open dictionary where the key is the option_id and key is a list of orders from newest date to oldest date (descending order by date)
    # option_id contans the unique symbol, strike, expiration date, option type for the stock
    open_orders = {}
    for order in open_order_not_filtered:
        option_id = order['option_id']
        if option_id in open_orders:
            open_orders[option_id].append(order)
        else:
            open_orders[option_id] = [order]

    # matching the close orders "option id" to open orders "option id"
    while len(close_orders) > 0:
        # .pop() grabs the last element (Oldest older by date)
        close_order = close_orders.pop()

        # scenario where the covered "short" call is considered close_order where it really should be open_order
        if len(open_orders[close_order['option_id']]) == 0:
            # print(close_order)
            close_order['position_effect'] = 'open'
            open_orders[close_order['option_id']].append(close_order)
            continue

        # .pop() grabs the last element (Oldest older by date)
        open_order = open_orders[close_order['option_id']].pop()
        close_amount = float(close_order['quantity'])
        open_amount = float(open_order['quantity'])

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
            open_orders[close_order['option_id']].append(open_order)
            size = close_amount  # the amount being processed
        # if the closer_order is the same as the open_order
        else:
            size = open_amount

        # average price of the open order contract
        open_average_price = float(open_order['average_price'])
        # average price of the close order contract
        close_average_price = float(close_order['average_price'])

        # if the open order is a buy order
        if open_order['side'] == 'buy':
            side = 'LONG'
            # calculate the $ return and % return
            returnAmount = round(
                (close_average_price - open_average_price) * 100 * size, 2)
            returnPercentge = round(
                ((close_average_price / open_average_price) - 1) * 100, 2)
        # if the open order is a sell order
        elif open_order['side'] == 'sell':
            side = 'SHORT'
            # calculate the $ return and % return
            returnAmount = round(
                (open_average_price - close_average_price)*100*size, 2)
            returnPercentge = round(
                ((open_average_price / close_average_price) - 1) * 100, 2)

        # completed option trade was a win or loss based on return amount
        status = 'LOSS' if returnAmount < 0 else 'WIN'

        # how long the option contract was being held where date is held in year-month-date like 2-8-2022
        date_difference = holding_amount_by_days(
            open_order['order_created_at'], close_order['order_created_at'])

        new_row = {
            'STATUS': status,
            'OPEN DATE': open_order['order_created_at'],
            'CLOSE DATE': close_order['order_created_at'],
            'SYMBOL': open_order['symbol'],
            'STRIKE': open_order['strike_price'],
            'EXPIRE': open_order['expiration_date'],
            'OPTION TYPE': open_order['option_type'].upper(),
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

    # remaining open_orders that are left after all the close_orders were processed
    for option_id_key in open_orders.keys():
        for open_order in open_orders[option_id_key]:
            # trade side
            side = 'SHORT' if open_order['side'] == 'sell' else 'LONG'

            # open date
            open_y, open_m, open_d = [
                int(x) for x in open_order['order_created_at'].split('-')]
            open_date = dt.date(open_y, open_m, open_d)
            # close date
            close_y, close_m, close_d = [
                int(x) for x in open_order['expiration_date'].split('-')]
            close_date = dt.date(close_y, close_m, close_d)

            # open order quantity and average price
            open_order_quantity = float(open_order['quantity'])
            open_average_price = float(open_order['average_price'])

            # if option is already expired or not
            if close_date <= dt.date.today():
                if side == 'SHORT':
                    returnAmount = round(
                        (open_average_price * open_order_quantity)*100, 2)
                    returnPercentge = round(100, 2)
                else:
                    returnAmount = round(
                        (open_average_price * open_order_quantity)*-100, 2)
                    returnPercentge = round(-100, 2)

                # date difference
                date_difference = (close_date - open_date).days

                status = 'LOSS' if returnAmount < 0 else 'WIN'

                new_row = {
                    'STATUS': status,
                    'OPEN DATE': open_order['order_created_at'],
                    'CLOSE DATE': open_order['expiration_date'],
                    'SYMBOL': open_order['symbol'],
                    'STRIKE': open_order['strike_price'],
                    'EXPIRE': open_order['expiration_date'],
                    'OPTION TYPE': open_order['option_type'].upper(),
                    'SIZE': round(open_order_quantity),
                    'ENTRY PRICE': round(open_average_price, 2),
                    'EXIT PRICE': 0,
                    'RETURN %':  str(returnPercentge)+'%',
                    'RETURN $': returnAmount,
                    'HOLD TIME': date_difference,
                    'SIDE': side,
                    'open_order': open_order,
                }
            # option is not expired and currently being hold
            else:
                # date difference
                date_difference = (dt.date.today() - open_date).days
                new_row = {
                    'STATUS': 'OPEN',
                    'OPEN DATE': open_order['order_created_at'],
                    'CLOSE DATE': '',
                    'SYMBOL': open_order['symbol'],
                    'STRIKE': open_order['strike_price'],
                    'EXPIRE': open_order['expiration_date'],
                    'OPTION TYPE': open_order['option_type'].upper(),
                    'SIZE': round(open_order_quantity),
                    'ENTRY PRICE': round(open_average_price, 2),
                    'EXIT PRICE': None,
                    'RETURN %':  None,
                    'RETURN $': None,
                    'HOLD TIME': date_difference,
                    'SIDE': side,
                    'open_order': open_order,
                }
            df = df.append(new_row, ignore_index=True)

    complete_df = df.loc[df['CLOSE DATE'] != ''].sort_values(
        by=['CLOSE DATE'], ascending=False).reset_index()
    open_df = df.loc[df['CLOSE DATE'] == ''].sort_values(
        by=['OPEN DATE'], ascending=False).reset_index()
    df = pd.concat([complete_df, open_df])
    return df[display_column_names], df

# completed option trades by symbol
def completed_option_trades_by_symbol(symbol):
    completed_option_orders()
    option_orders = option_orders_with_symbol_conversion(
        csvName)
    simple_df, complex_df = completed_option_trades_by_symbol_universal(
        symbol, option_orders)

    noncomplete_order_return = round(
        noncompleted_option_trades_by_symbol(symbol, option_orders), 2)
    complete_order_return = simple_df['RETURN $'].sum()

    if complete_order_return != noncomplete_order_return:
        print('symbol: ', symbol)
        print('complete order amount:', complete_order_return)
        print('noncomplete order amount:', noncomplete_order_return)

    return simple_df, complex_df

# completed option trades
def completed_option_trades():
    completed_option_orders()
    option_orders = option_orders_with_symbol_conversion(
        csvName)
    # grab all the symbols ever traded for option orders
    symbols_df = pd.DataFrame(option_orders)[
        'symbol'].drop_duplicates().reset_index()

    df, display_column_names = create_option_df()
    for row in symbols_df['symbol']:
        df_by_symbol_simple, df_by_symbol = completed_option_trades_by_symbol_universal(
            row, option_orders)

        # compare totals
        noncomplete_order_return = round(noncompleted_option_trades_by_symbol(
            row, option_orders), 2)  # fix this function
        complete_order_return = df_by_symbol_simple['RETURN $'].sum()

        if noncomplete_order_return != complete_order_return:
            print(row)
            print('complete order amount:', complete_order_return)
            print('noncomplete order amount:', noncomplete_order_return)
        df = df.append(df_by_symbol_simple)

    complete_df = df.loc[df['CLOSE DATE'] != ''].sort_values(
        by=['CLOSE DATE'], ascending=False).reset_index()
    open_df = df.loc[df['CLOSE DATE'] == ''].sort_values(
        by=['OPEN DATE'], ascending=False).reset_index()
    df = pd.concat([complete_df, open_df])
    return df[display_column_names], df

