import pandas as pd
import datetime
import dontshare as d  # this is where the Birdeye API key is stored named birdeye
import requests
import time
import json
import pprint
import re as reggie

# Configuration
new_data = True  # THIS ONLY RUNS FOR NEW DATA IF THIS IS TRUE - otherwise it uses last run's data
MARKET_CAP_MAX = 30000  # max market cap *ONLY APPLIES IF NEW_DATA = TRUE*
NUM_TOKENS_2SEARCH = 15000  # number of tokens to search through on Solana *ONLY APPLIES IF NEW_DATA = TRUE*
MIN_24HR_VOLUME = 1000  # min 24 hour volume *ONLY APPLIES IF NEW_DATA = TRUE*

MAX_SELL_PERCENTAGE = 70  # if the sell % more than MAX_SELL_PERCENTAGE sells in the last hour, drop it
MIN_TRADES_LAST_HOUR = 9  # if there are less than MIN_TRADES_LAST_HOUR trades in the last hour, drop it
MIN_UNQ_WALLETS2hr = 30  # if there are less than MIN_UNQ_WALLETS2hr unique wallets in the last 2 hours, drop it
MIN_VIEW24h = 15  # if there are less than MIN_VIEW24h views in the last 24 hours, drop it
MIN_LIQUIDITY = 400  # if there is less than MIN_LIQUIDITY liquidity, drop it

BASE_URL = "https://public-api.birdeye.so/defi"
TOKEN_LIST_URL = "https://public-api.birdeye.so/defi/tokenlist"

# API Key from your 'dontshare' file
API_KEY = d.birdeye


def get_new_token():
    new_token_url = f"https://public-api.birdeye.so/defi/v2/tokens/new_listing?limit=10&meme_platform_enabled=false"
    headers = {
        "accept": "application/json",
        "x-chain": "solana",
        "X-API-KEY": d.birdeye
    }

    response = requests.get(new_token_url, headers=headers)
    if response.status_code == 200:
        return response.json().get('data', {})
    else:
        print(
            f"Failed to retrieve new token: HTTP status code {response.status_code}"
        )
        return {}


def get_token_security(address):
    security_url = f"https://public-api.birdeye.so/defi/token_security?address={address}"
    headers = {"X-API-KEY": d.birdeye}

    response = requests.get(security_url, headers=headers)
    if response.status_code == 200:
        return response.json().get('data', {})
    else:
        print(
            f"Failed to retrieve token security for address {address}: HTTP status code {response.status_code}"
        )
        return {}


def filter_by_security(tokens):
    filtered_tokens = []
    for token in tokens:
        security_data = get_token_security(token['address'])
        if security_data:
            ownership_renounced = security_data.get('ownershipRenounced',
                                                    False)
            freeze_authority = security_data.get('freezeAuthority', False)
            top_10_holders = security_data.get('top10Holders', 100)

            if ownership_renounced and not freeze_authority and top_10_holders < 20:
                filtered_tokens.append(token)
    return filtered_tokens


def birdeye_bot():
    headers = {"x-chain": "solana", "X-API-KEY": d.birdeye}

    new_tokens = get_new_token()

    print(new_tokens)

    tokens = []
    offset = 0
    limit = 50
    total_tokens = 0
    num_tokens = NUM_TOKENS_2SEARCH
    mc_high = MARKET_CAP_MAX
    mc_low = 50

    # Set minimum liquidity and minimum 24-hour volume
    min_liquidity = MIN_LIQUIDITY
    min_volume_24h = MIN_24HR_VOLUME
    mins_last_trade = 59

    # THIS LOOPS AND GRABS ALL THE TOKENS TIL WE HIT MAX TOKENS
    # while total_tokens < NUM_TOKENS_2SEARCH:
    #     try:
    #         print(f'scanning Solana for new tokens, total scanned: {total_tokens}...')
    #         params = {"sort_by": "v24hChangePercent", "sort_type": "desc", "offset": offset, "limit": limit}
    #         response = requests.get(TOKEN_LIST_URL, headers=headers, params=params)
    #         response.raise_for_status()

    #         new_tokens = response.json()['data']['tokens']
    #         print(new_tokens)

    #         if response.status_code == 200:
    #             response_data = response.json()
    #             new_tokens = response_data.get('data', {}).get('tokens', [])
    #             tokens.extend(new_tokens)
    #             total_tokens += len(new_tokens)
    #             offset += limit
    #         else:
    #             print(f"Error {response.status_code}: trying again in 10 seconds...")
    #             time.sleep(10)  # Sleep longer on error before retrying
    #             continue  # Skip to the next pagination

    #         time.sleep(0.1)  # Sleep to avoid hitting rate limits
    #     except requests.exceptions.RequestException as e:
    #         print(f"Request failed: {e}. Retrying in 10 seconds...")
    #         time.sleep(10)
    #         continue

    # DATA SCIENCE PART
    df = pd.DataFrame(tokens)

    # Add the token URL column
    df['token_url'] = df['address'].apply(lambda x: BASE_URL + x)

    # Drop rows with missing 'liquidity' or 'v24hUSD'
    df = df.dropna(subset=['liquidity', 'v24hUSD'])

    # Filter for minimum liquidity
    df = df[df['liquidity'] >= min_liquidity]

    # Filter for minimum 24-hour volume
    df = df[df['v24hUSD'] >= min_volume_24h]

    # Filter the DataFrame to keep only the tokens with 'mc' between mc_low and mc_high
    df = df[(df['mc'] >= mc_low) & (df['mc'] <= mc_high)]

    # Drop specified columns
    drop_columns = ['logoURI', '_id']
    for col in drop_columns:
        if col in df.columns:
            df = df.drop(columns=col)

    # Convert lastTradeUnixTime to UTC and make it tz-aware
    df['lastTradeUnixTime'] = pd.to_datetime(df['lastTradeUnixTime'],
                                             unit='s').dt.tz_localize('UTC')

    # Calculate the current time in UTC
    current_time = datetime.datetime.now(datetime.timezone.utc)

    # Calculate the time 10 minutes ago in UTC
    ten_minutes_ago = current_time - datetime.timedelta(
        minutes=mins_last_trade)

    # Filter the DataFrame to keep only the rows with trades within the last 10 minutes based on the lastTradeUnixTime
    df = df[df['lastTradeUnixTime'] >= ten_minutes_ago]

    # Save the DataFrame to a local CSV file
    df.to_csv("data/filtered_pricechange_with_urls.csv", index=False)

    # Pretty-print the modified DataFrame with each piece of data in its own column
    pd.set_option('display.max_columns', None)  # Show all columns

    return df


# This checks to see if we want new data
if new_data:
    print('getting new data...')
    data = birdeye_bot()
else:
    data = pd.read_csv('data/filtered_pricechange_with_urls.csv')


# in the df if the v24hUSD column has a number in it, drop it from the data and make a new df + save as 'new_launces-mm-dd-hh.csv'
# THIS ONE IS CHILL IT JUST DROPS A COLUMN TO GET NEW LAUNCHES ONLY
def new_launches(data):
    # Create a new DataFrame with rows where 'v24hUSD' is NaN (empty)
    new_launches = data[data['v24hChangePercent'].isna()]

    # Generate a timestamp for the current date and time
    timestamp = datetime.datetime.now().strftime("%m-%d-%H")

    # Construct the CSV file name with the timestamp
    csv_filename = 'data/new_launches.csv'

    # Save the new launches DataFrame as a CSV file with the generated filename
    new_launches.to_csv(csv_filename, index=False)

    return new_launches


# RUN NEW LAUNCHES TO GET RID OF THINGS THAT LAUNCHED TOO LONG AGO
new_launches(data)


# Custom function to print JSON in a human-readable format
def print_pretty_json(data):
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(data)


# Function to print JSON in a human-readable format - assuming you already have it as print_pretty_json
# Helper function to find URLs in text
def find_urls(string):
    # Regex to extract URLs
    return reggie.findall(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        string)


# UPDATED TO REMOVE THE OTHER ONE so now we can just use this filter instead of filtering twice
def token_overview(address, MAX_SELL_PERCENTAGE, MIN_TRADES_LAST_HOUR,
                   MIN_UNQ_WALLETS2hr, MIN_VIEW24h, MIN_LIQUIDITY):
    overview_url = f"{BASE_URL}/token_overview?address={address}"
    headers = {"X-API-KEY": API_KEY}

    response = requests.get(overview_url, headers=headers)
    result = {}

    if response.status_code == 200:
        overview_data = response.json().get('data', {})

        buy1h = overview_data.get('buy1h', 0)
        sell1h = overview_data.get('sell1h', 0)
        trade1h = buy1h + sell1h
        total_trades = trade1h

        # Perform buy/sell percentage calculations:
        buy_percentage = (buy1h / total_trades * 100) if total_trades else 0
        sell_percentage = (sell1h / total_trades * 100) if total_trades else 0

        # Criteria checks:
        if sell_percentage > MAX_SELL_PERCENTAGE:
            return None  # Drop the data if sell percentage is too high
        if trade1h < MIN_TRADES_LAST_HOUR:
            return None  # Drop the data if not enough trades
        if overview_data.get('uniqueWallet24h', 0) < MIN_UNQ_WALLETS2hr:
            return None  # Drop the data if not enough unique wallets
        if overview_data.get('view24h', 0) < MIN_VIEW24h:
            return None  # Drop the data if not enough views
        if overview_data.get('liquidity', 0) < MIN_LIQUIDITY:
            return None  # Drop the data if not enough liquidity

        # Add calculated data to the result dictionary:
        result.update({
            'address': address,
            'buy1h': buy1h,
            'sell1h': sell1h,
            'trade1h': trade1h,
            'buy_percentage': buy_percentage,
            'sell_percentage': sell_percentage,
            'liquidity': overview_data.get('liquidity', 0),
            # Add other necessary data from overview_data that passed the checks
        })

        # Process description links if 'extensions' is not None:
        extensions = overview_data.get('extensions', {})
        description = extensions.get('description', '') if extensions else ''
        urls = find_urls(description)
        links = [{'telegram': u} for u in urls if 't.me' in u]
        links.extend([{'twitter': u} for u in urls if 'twitter.com' in u])
        links.extend([{
            'website': u
        } for u in urls if 't.me' not in u and 'twitter.com' not in u])
        result['description'] = links

        return result

    else:
        print(
            f"Failed to retrieve token overview for address {address}: HTTP status code {response.status_code}"
        )
        return None


# Load data from CSV file
df = pd.read_csv('data/new_launches.csv')

dfs_to_concat = []

# Iterate over each row in the DataFrame
for index, row in df.iterrows():
    while True:  # Start an infinite loop to retry upon failure
        try:
            # Calling the updated token_overview function with passing parameters
            token_data = token_overview(
                row['address'],
                MAX_SELL_PERCENTAGE=MAX_SELL_PERCENTAGE,
                MIN_TRADES_LAST_HOUR=MIN_TRADES_LAST_HOUR,
                MIN_UNQ_WALLETS2hr=MIN_UNQ_WALLETS2hr,
                MIN_VIEW24h=MIN_VIEW24h,
                MIN_LIQUIDITY=MIN_LIQUIDITY)

            # Check if there is data to process
            if token_data:
                # Add the address to the data
                token_data['address'] = row['address']

                # Create the URL and add it to the token_data
                token_data[
                    'url'] = f"https://dexscreener.com/solana/{token_data['address']}"

                # Remove priceChanges from the data as we won't be needing it
                token_data.pop('priceChangesXhrs', None)

                # Convert the token_data dictionary to a DataFrame
                temp_df = pd.DataFrame([token_data])

                # Append the DataFrame to the list for concatenation
                dfs_to_concat.append(temp_df)

            break  # because we are done with this one

        except Exception as e:
            print(f"Failed to process token {row['address']}: {e}")
            time.sleep(5)

if dfs_to_concat:
    # Concatenate all the DataFrames in the list
    results_df = pd.concat(dfs_to_concat, ignore_index=True)

    # Save the results to a CSV file
    csv_file_path = 'data/hyper-sorted-sol.csv'
    results_df.to_csv(csv_file_path, index=False)

    # Print a horizontal line for readability
    print('-' * 80)

    # Print the final DataFrame
    print(results_df)

else:
    # Print a process completion text with instructions
    print('-' * 80)
    print("After filtering, there are no tokens meeting the criteria."
          "Try changing your parameters or increasing NUM_TOKENS_2SEARCH.")

birdeye_bot()
