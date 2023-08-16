# Get the list of SPAC conversions
import pandas as pd
import robin_stocks.robinhood as r  # abbreviated version of robinhoood commands
import csv
import datetime as dt

# symbol conversions for option orders
def get_corporate_actions():
    url = 'https://api.robinhood.com/options/corp_actions/'
    corporate_actions = r.helper.request_get(url, 'pagination')
    result = []
    for action in corporate_actions:
        if action['type'] == 'symbol_conversion':
            # action keys: dict_keys(['id', 'type', 'effective_date', 'state', 'chain', 'new_cash_component',
            # 'old_cash_component', 'new_symbol', 'old_symbol', 'new_trade_value_multiplier',
            # 'old_trade_value_multiplier', 'underlying_instruments', 'affected_positions', 'created_at', 'updated_at'])
            # underlying_instruments keys: dict_keys(['id', 'instrument', 'symbol', 'new_quantity', 'old_quantity'])
            for affected_position in action['affected_positions']:
                result.append({
                    'old_symbol': action['old_symbol'],
                    'old_trade_value_multiplier': action['old_trade_value_multiplier'],
                    'new_symbol': action['new_symbol'],
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
        result.append({
            'old_symbol': r.stocks.get_stock_quote_by_id(split['split']['old_instrument_id'])['symbol'],
            'new_symbol': r.stocks.get_stock_quote_by_id(split['split']['new_instrument_id'])['symbol'],
            'effective_date': split['split']['effective_date'],
            'multiplier': split['split']['multiplier'],
            'divisor': split['split']['divisor'],
            'direction': split['split']['direction'],
        })
    print(result)
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
    corpactions_df_simple = corporate_actions_df.drop_duplicates(subset=['old_symbol']).reset_index(
        drop=True).drop(columns=['option_id', 'new_strike_price', 'new_expiration_date'])

    corpactions_df_simple_same_value = corpactions_df_simple.loc[corpactions_df_simple[
        'old_trade_value_multiplier'] == corpactions_df_simple['new_trade_value_multiplier']]

    df['symbol'] = df['symbol'].replace(corpactions_df_simple_same_value['old_symbol'].to_list(
    ), corpactions_df_simple_same_value['new_symbol'].to_list())
    return df.to_dict('records')

# how long a position has been held for
def holding_amount_by_days(openDate, closeDate):
    open_y, open_m, open_d = [int(x) for x in openDate.split('-')]
    open_date = dt.date(open_y, open_m, open_d)

    close_y, close_m, close_d = [int(y) for y in closeDate.split('-')]
    close_date = dt.date(close_y, close_m, close_d)

    return (close_date - open_date).days
