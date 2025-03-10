# i built this OHLCV to filter more
# from here, you can test all types of variables to filter based on oHLCV data
# in the get_new_launches you can change variables to get more or less data

#####################################################

# DISCLAIMER #
# Put in your own strategy before taking any of this live
# I am not a financial advisor and I do not know if this solana bot works, or will work in the future. This is all just a test.

# This course intentionally gives you the pieces and not a full running bot. I do not believe
# in giving plug and play bots because if we all run the same strategy, this would never work
# ill never release a plug and play bot, and if you see that online, run. There is a good chance
# that there is malicious code, or the strategy is going to 0. do not buy pre-built bots
# my goal from this solana course is to teach you how to build your own bot with your own strategy
# I do my best in this course to show you every single lego piece I used to build the current bot you see on YouTube
# if for any reason, you want a refund, we have a 100% money back guarantee
# we will refund your money immediately if you ever feel like you dont get the value you pay for in any of my products
# I will never sell a plug and play bot, I want to teach you how to code your own, so you can build for the rest of your life.
# ps - I will never dm you on discord offering a bot either, be careful out there.

########################################################

import pandas as pd
import requests, time, os
import dontshare as d  # Assuming this module contains your API key
from datetime import datetime, timedelta
import panddas_ta as ta

timeframe = '3m'  # 1m, 3m, 5m, 15m, 1h

# mark out if you dont want new data
import get_new_launches


# Function to calculate the timestamps for now and 10 days from now
def get_time_range():
    now = datetime.now()
    ten_days_earlier = now - timedelta(days=10)
    time_to = int(now.timestamp())
    time_from = int(ten_days_earlier.timestamp())
    print(time_from, time_to)

    return time_from, time_to


# GETTING OHLCV DATA
def get_data(address, time_from, time_to):
    url = f"https://public-api.birdeye.so/defi/ohlcv?address={address}&type={timeframe}&time_from={time_from}&time_to={time_to}"
    #url = f"https://public-api.birdeye.so/defi/ohlcv?address={address}&type={timeframe}&time_from=1706826067&time_to=1706827067"
    # 1706827429 1707691429
    headers = {"X-API-KEY": d.birdeye}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        json_response = response.json()  # Get the JSON response
        items = json_response.get('data',
                                  {}).get('items',
                                          [])  # Safely access the 'items' list

        # Create a list of dictionaries with only the relevant data and the new human-readable time column
        processed_data = [{
            'Datetime (UTC)':
            datetime.utcfromtimestamp(
                item['unixTime']).strftime('%Y-%m-%d %H:%M:%S'),
            'Open':
            item['o'],
            'High':
            item['h'],
            'Low':
            item['l'],
            'Close':
            item['c'],
            'Volume':
            item['v']
        } for item in items]

        # Assuming 'processed_data' is already defined and available
        df = pd.DataFrame(processed_data)

        # Check if the DataFrame has fewer than 40 rows
        if len(df) < 40:
            # Calculate the number of rows to replicate
            rows_to_add = 40 - len(df)

            # Replicate the first row
            first_row_replicated = pd.concat([df.iloc[0:1]] * rows_to_add,
                                             ignore_index=True)

            # Append the replicated rows to the start of the DataFrame
            df = pd.concat([first_row_replicated, df], ignore_index=True)

        # Now that the DataFrame has been padded, you can calculate SMA20 without issues
        df['MA20'] = ta.sma(df['Close'], length=20)

        # Continue with the rest of your calculations
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA40'] = ta.sma(df['Close'], length=40)

        df['Price_above_MA20'] = df['Close'] > df['MA20']
        df['Price_above_MA40'] = df['Close'] > df['MA40']
        df['MA20_above_MA40'] = df['MA20'] > df['MA40']
        # Debug print to check the final dataframe
        print(df.head())

        return df

    else:
        print(
            f"Failed to fetch data for address {address}. Status code: {response.status_code}"
        )
        return pd.DataFrame()


def analyze_ohlcv_trend(ohlcv_df):
    ohlcv_df['RSI'] = ta.rsi(ohlcv_df['Close'], length=14)
    ohlcv_df['MA20'] = ta.sma(ohlcv_df['Close'], length=20)
    ohlcv_df['MA40'] = ta.sma(ohlcv_df['Close'], length=40)
    ohlcv_df['Price_above_MA20'] = ohlcv_df['Close'] > ohlcv_df['MA20']
    ohlcv_df['Price_above_MA40'] = ohlcv_df['Close'] > ohlcv_df['MA40']
    ohlcv_df['MA20_above_MA40'] = ohlcv_df['MA20'] > ohlcv_df['MA40']

    # Initialize variables to track the previous high and low
    prev_high = ohlcv_df['High'].iloc[0]
    prev_low = ohlcv_df['Low'].iloc[0]
    higher_highs = True
    higher_lows = True

    # Loop through the DataFrame to check for higher highs and higher lows
    for i in range(1, len(ohlcv_df)):
        current_high = ohlcv_df['High'].iloc[i]
        current_low = ohlcv_df['Low'].iloc[i]

        if current_high <= prev_high:
            higher_highs = False
        if current_low <= prev_low:
            higher_lows = False

        # Update the previous values for the next iteration
        prev_high = current_high
        prev_low = current_low

    price_increase_from_launch = ohlcv_df['Close'].iloc[-1] > ohlcv_df[
        'Open'].iloc[0]

    # Prepare the analysis result
    trend_analysis = {
        'higher_highs': higher_highs,
        'higher_lows': higher_lows,
        'price_increase_from_launch': price_increase_from_launch,
        'RSI': ohlcv_df['RSI'].iloc[-1],
        'MA20': ohlcv_df['MA20'].iloc[-1],
        'MA40': ohlcv_df['MA40'].iloc[-1],
        'Price_above_MA20': ohlcv_df['Price_above_MA20'].iloc[-1],
        'Price_above_MA40': ohlcv_df['Price_above_MA40'].iloc[-1],
        'MA20_above_MA40': ohlcv_df['MA20_above_MA40'].iloc[-1]
    }

    return trend_analysis


def filter_and_output_addresses(ohlcv_df, current_address, original_df_path,
                                output_df_path):
    # Check if the majority of the last 30 entries are True for the given conditions
    conditions_met = []
    if len(ohlcv_df) >= 30:
        conditions_met.append((ohlcv_df['Price_above_MA20'].tail(30).sum() /
                               30) > 0.5)
        conditions_met.append((ohlcv_df['Price_above_MA40'].tail(30).sum() /
                               30) > 0.5)
        conditions_met.append((ohlcv_df['MA20_above_MA40'].tail(30).sum() /
                               30) > 0.5)

    # Check if 'price_increase_from_launch' is True
    price_increase_from_launch = ohlcv_df['Close'].iloc[-1] > ohlcv_df[
        'Open'].iloc[0]
    conditions_met.append(price_increase_from_launch)

    if any(conditions_met):
        # If any condition is met, read the original DataFrame
        original_df = pd.read_csv(original_df_path)

        # Find and keep the address in the original DataFrame
        filtered_df = original_df[original_df['address'] == current_address]

        # Append the filtered DataFrame to the output DataFrame
        # Check if the file exists and if not, create it with headers
        if not os.path.isfile(output_df_path):
            filtered_df.to_csv(output_df_path, mode='w', index=False)
        else:
            # Append without headers
            filtered_df.to_csv(output_df_path,
                               mode='a',
                               index=False,
                               header=False)

        print(
            f"Address {current_address} retained and output to {output_df_path}"
        )


# Define the paths - CHANGE TO BE YOUR PATHS
original_df_path = '/Users/tc/Dropbox/dev/github/On-Chain-Solana-Trading-Bot/data/hyper-sorted-sol.csv'
output_df_path = '/Users/tc/Dropbox/dev/github/On-Chain-Solana-Trading-Bot/data/final-sorted.csv'

# Read the addresses data
df = pd.read_csv(original_df_path)

time_from, time_to = get_time_range()

for index, row in df.iterrows():
    address = row['address']
    ohlcv_df = get_data(address, time_from, time_to)

    if not ohlcv_df.empty:
        trend_analysis = analyze_ohlcv_trend(ohlcv_df)
        print(ohlcv_df.tail(30))

        # Call the filter_and_output_addresses function for each address
        filter_and_output_addresses(ohlcv_df, address, original_df_path,
                                    output_df_path)

        # Additional debug prints or logging
        if any(trend_analysis.values()):  # Check if at least one value is True
            dexscreener_url = f"https://dexscreener.com/solana/{address}"
            print(
                f"Analysis for address {address}: {trend_analysis}\nDexScreener Link: {dexscreener_url}\n"
            )
            print('-----------------------------------')

        time.sleep(5)
