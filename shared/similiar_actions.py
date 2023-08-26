# Get the list of SPAC conversions
import pandas as pd
import robin_stocks.robinhood as r  # abbreviated version of robinhoood commands
import csv
import datetime as dt
from IPython.display import display


# symbol conversions for option orders
def get_corporate_actions():
    url = 'https://api.robinhood.com/options/corp_actions/'
    corporate_actions = r.helper.request_get(url, 'pagination')
    result = []
    for action in corporate_actions:
        # if action['type'] == 'symbol_conversion':
        # action keys: dict_keys(['id', 'type', 'effective_date', 'state', 'chain', 'new_cash_component',
        # 'old_cash_component', 'new_symbol', 'old_symbol', 'new_trade_value_multiplier',
        # 'old_trade_value_multiplier', 'underlying_instruments', 'affected_positions', 'created_at', 'updated_at'])
        # underlying_instruments keys: dict_keys(['id', 'instrument', 'symbol', 'new_quantity', 'old_quantity'])
        for affected_position in action['affected_positions']:
            underlying_instruments = action['underlying_instruments']
            new_symbol = underlying_instruments[1]['symbol']
            result.append({
                'old_symbol': action['old_symbol'],
                'old_trade_value_multiplier': action['old_trade_value_multiplier'],
                'new_symbol': new_symbol,
                'new_trade_value_multiplier': action['new_trade_value_multiplier'],
                'effective_date': action['effective_date'],
                'type': action['type'],
                'option_id': affected_position['option'],
                'new_strike_price': affected_position['new_strike_price'],
                'new_expiration_date': affected_position['new_expiration_date']
            })
    return result

# symbol conversion for stock splits
def get_stock_splits():
    url = 'https://api.robinhood.com/corp_actions/v2/split_payments/'
    stock_splits = r.helper.request_get(url, 'pagination')
    result = []
    for split in stock_splits:
        split_data = split['split']
        old_symbol = r.stocks.get_stock_quote_by_id(split_data['old_instrument_id'])['symbol']
        new_symbol = r.stocks.get_stock_quote_by_id(split_data['new_instrument_id'])['symbol']
        result.append({
            'old_symbol': old_symbol,
            'new_symbol': new_symbol,
            'effective_date': split_data['effective_date'],
            'multiplier': split_data['multiplier'],
            'divisor': split_data['divisor'],
            'direction': split_data['direction'],
        })
    return result

# converts csv to list of dictionaries
def csv_to_list(filename):
    # pass the file object to DictReader() to get the DictReader object
    with open(filename, 'r') as updated_csv:
        # get a list of dictionaries from dict_reader by mapping the information read
        dict_reader = csv.DictReader(updated_csv)
        # list of dictionaries where every row is an order
        updated_list = list(dict_reader)
        return updated_list

# converts existing SPAC holding tickers to the proper tickers if the user held on/after SPAC Date
# return newest to oldest option orders
def option_orders_with_symbol_conversion(filename):
    # grabs completed option order from csv file to updated list of dictionaries
    # returns newest to oldest option orders
    option_orders = csv_to_list(filename)
    df = pd.DataFrame(option_orders)

    corporate_actions_df = pd.DataFrame(get_corporate_actions())
    corpactions_df_simple = corporate_actions_df.drop_duplicates(
        subset=['option_id']).reset_index(drop=True)
    df_unique_option_id = df.drop_duplicates(
        subset=['option_id']).reset_index(drop=True)

    replacement_links_df = pd.merge(
        corpactions_df_simple,
        df_unique_option_id.loc[:, [
            'symbol', 'option_id', 'expiration_date', 'strike_price']],
        left_on=['new_symbol', 'new_expiration_date', 'new_strike_price'],
        right_on=['symbol', 'expiration_date', 'strike_price']
    ).loc[:, ['option_id_x', 'option_id_y']]

    df['option_id'] = df['option_id'].replace(replacement_links_df['option_id_x'].to_list(
    ), replacement_links_df['option_id_y'].to_list())
    df['symbol'] = df['symbol'].replace(corporate_actions_df['old_symbol'].to_list(
    ), corporate_actions_df['new_symbol'].to_list())

    return df.to_dict('records')

# converts existing SPAC holding tickers to the proper tickers if the user held on/after SPAC Date
# return newest to oldest stock orders
def stock_orders_with_symbol_conversion(filename):
    # grabs completed option order from csv file to updated list of dictionaries
    # returns newest to oldest option orders
    option_orders = csv_to_list(filename)
    df = pd.DataFrame(option_orders)

    corporate_actions_df = pd.DataFrame(get_corporate_actions())
    unique_actions = corporate_actions_df.drop_duplicates(subset=['old_symbol']).reset_index(
        drop=True).drop(columns=['option_id', 'new_strike_price', 'new_expiration_date'])

    same_value_actions = unique_actions[unique_actions['old_trade_value_multiplier'] == unique_actions['new_trade_value_multiplier']]

    df['symbol'] = df['symbol'].replace(same_value_actions['old_symbol'].to_list(
    ), same_value_actions['new_symbol'].to_list())
    return df.to_dict('records')

# how long a position has been held for
def holding_amount_by_days(open_date, close_date):
    open_date = dt.datetime.strptime(open_date, '%Y-%m-%d').date()
    close_date = dt.datetime.strptime(close_date, '%Y-%m-%d').date()
    return (close_date - open_date).days

# Completing Stock Orders
def completed_stock_orders(fileName):
    file_path = r.export.create_absolute_csv('.', fileName, 'stock')
    all_orders = r.export.get_all_stock_orders()
    with open(file_path, 'w', newline='') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow([
            'symbol',
            'instrument',
            'instrument_id',
            'date',
            'time',
            'order_type',
            'side',
            'fees',
            'quantity',
            'average_price',
            'total_price'
        ])
        # getting the stock splits
        stock_splits = get_stock_splits()
        list_of_stock_splits = []
        for split in stock_splits:
            list_of_stock_splits.append(split['old_symbol'])

        for order in all_orders:
            if 'filled' in order['state'] and order['cancel'] is None:
                date_and_time = order['last_transaction_at'].split('T')

                if r.stocks.get_symbol_by_url(order['instrument']) in list_of_stock_splits and dt.datetime.strptime(date_and_time[0], "%Y-%m-%d") < dt.datetime.strptime(split['effective_date'], "%Y-%m-%d"):
                    price_amount = float(
                        order['cumulative_quantity']) * float(order['average_price'])
                    csv_writer.writerow([
                        r.stocks.get_symbol_by_url(order['instrument']),
                        order.get('instrument'),
                        order.get('instrument_id'),
                        date_and_time[0],
                        date_and_time[1],
                        order['type'],
                        order['side'],
                        order['fees'],
                        str(float(order['cumulative_quantity']) *
                            float(split['multiplier']) / float(split['divisor'])),
                        str(float(
                            order['average_price']) * float(split['divisor']) / float(split['multiplier'])),
                        str(float(order['cumulative_quantity']) *
                            float(order['average_price']) - float(order['fees']))
                    ])
                else:
                    price_amount = float(
                        order['cumulative_quantity']) * float(order['average_price'])
                    csv_writer.writerow([
                        r.stocks.get_symbol_by_url(order['instrument']),
                        order.get('instrument'),
                        order.get('instrument_id'),
                        date_and_time[0],
                        date_and_time[1],
                        order['type'],
                        order['side'],
                        order['fees'],
                        order['cumulative_quantity'],
                        order['average_price'],
                        str(float(order['cumulative_quantity']) *
                            float(order['average_price']) - float(order['fees']))
                    ])
        f.close()

# grabs assignment or exercised options
def list_option_events():
    url = 'https://api.robinhood.com/options/events/'
    option_events_request = r.request_get(url, 'pagination')

    # dict_keys(['account', 'cash_component', 'chain_id', 'created_at', 'direction', 'equity_components',
    # 'event_date', 'id', 'option', 'position', 'quantity', 'source_ref_id', 'state', 'total_cash_amount',
    # 'type', 'underlying_price', 'updated_at'])
    # for the key: type, there are two types: expiration or assignment
    # for equity_components: dict_keys(['id', 'instrument', 'price', 'quantity', 'side', 'symbol'])

    df_option_events = pd.DataFrame(option_events_request)
    df_option_events = df_option_events.loc[df_option_events['type'].isin(
        ['assignment', 'exercise'])]
    option_events_request = df_option_events.to_dict('records')

    option_events = []
    for option_event in option_events_request:
        # equity_components
        #   instrument
        #   price
        #   quantity
        #   side
        #   symbol
        # event_date
        # total_cash_amount
        # fee is price * quantity - total cash amount
        event_date = option_event.get('event_date')
        total_cash_amount = option_event.get('total_cash_amount')
        equity_components = option_event.get('equity_components')
        round_num = 6
        for component in equity_components:
            event = {
                'symbol': component.get('symbol'),
                'instrument': component.get('instrument'),
                'instrument_id': component.get('instrument').replace('https://api.robinhood.com/instruments/', '').replace('/', ''),
                'date': event_date,
                'time': '16:00:00.000000Z',
                'order_type': 'option event',
                'side': component.get('side'),
                'fees': str(round(float(component.get('price')) * float(component.get('quantity')) - float(total_cash_amount), round_num)),
                'quantity': component.get('quantity'),
                'average_price': component.get('price'),
                'total_price': total_cash_amount,
            }
            option_events.append(event)
    return option_events