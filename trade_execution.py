import requests
import time
import json
import base64
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
import dontshare as d

# Configuration for sniper bot
ENTRY_MARKET_CAP = 20000  # Enter when market cap is $20,000
STOP_LOSS_MARKET_CAP = 15000  # Stop loss when market cap falls to $15,000
TAKE_PROFIT_MARKET_CAP_90 = 200000  # Take profit 90% when market cap reaches $200,000
TAKE_PROFIT_MARKET_CAP_10 = 2000000  # Take profit remaining 10% when market cap reaches $2,000,000

BUY_AMOUNT = 0.05  # Minimum buy amount in SOL
SELL_PERCENT_90 = 0.90  # Sell 90%
SELL_PERCENT_10 = 0.10  # Sell remaining 10%

# Solana specific configurations
SOL_RPC_URL = "https://api.mainnet-beta.solana.com"
SLIPPAGE = 50
QUOTE_TOKEN = 'So11111111111111111111111111111111111111112'
KEY = Keypair.from_base58_string(d.key)
http_client = Client(SOL_RPC_URL)

# Birdseye API Key
BIRDEYE_API_KEY = d.birdeye  # Assuming the API key is stored in dontshare.py


def get_token_data(token_address):
    market_cap = fetch_market_cap(token_address)
    if market_cap is None:
        print(f"Failed to fetch market cap for token: {token_address}")
        return None
    return {'address': token_address, 'market_cap': market_cap}


def fetch_market_cap(token_address):
    try:
        # Birdseye API endpoint and headers
        headers = {
            'Authorization': f'Bearer {BIRDEYE_API_KEY}',
            'Content-Type': 'application/json'
        }
        response = requests.get(
            f"https://api.birdeye.com/v1/marketcap/{token_address}",
            headers=headers)
        response.raise_for_status()  # Raise an HTTPError on bad responses
        market_cap_data = response.json()
        return market_cap_data['market_cap']
    except requests.exceptions.RequestException as e:
        print(f"Error fetching market cap: {e}")
        return None


def execute_trade(token_address, trade_type, amount):
    try:
        if trade_type == 'buy':
            print(f"Buying token: {token_address} Amount: {amount} SOL")
            amount_lamports = int(amount *
                                  1000000000)  # Convert SOL to lamports
            quote = requests.get(
                f'https://quote-api.jup.ag/v6/quote?inputMint={QUOTE_TOKEN}\
&outputMint={token_address}\
&amount={amount_lamports}\
&slippageBps={SLIPPAGE}').json()
            tx_res = requests.post('https://quote-api.jup.ag/v6/swap',
                                   headers={
                                       "Content-Type": "application/json"
                                   },
                                   data=json.dumps({
                                       "quoteResponse":
                                       quote,
                                       "userPublicKey":
                                       str(KEY.pubkey())
                                   })).json()
            swap_tx = base64.b64decode(tx_res['swapTransaction'])
            tx1 = VersionedTransaction.from_bytes(swap_tx)
            tx = VersionedTransaction(tx1.message, [KEY])
            tx_id = http_client.send_raw_transaction(
                bytes(tx), TxOpts(skip_preflight=True)).value
            print(f"https://solscan.io/tx/{str(tx_id)}")

        elif trade_type == 'sell':
            print(f"Selling token: {token_address} Amount: {amount * 100}%")
            amount_lamports = int(amount *
                                  1000000000)  # Convert SOL to lamports
            quote = requests.get(
                f'https://quote-api.jup.ag/v6/quote?inputMint={token_address}\
&outputMint={QUOTE_TOKEN}\
&amount={amount_lamports}\
&slippageBps={SLIPPAGE}').json()
            tx_res = requests.post('https://quote-api.jup.ag/v6/swap',
                                   headers={
                                       "Content-Type": "application/json"
                                   },
                                   data=json.dumps({
                                       "quoteResponse":
                                       quote,
                                       "userPublicKey":
                                       str(KEY.pubkey())
                                   })).json()
            swap_tx = base64.b64decode(tx_res['swapTransaction'])
            tx1 = VersionedTransaction.from_bytes(swap_tx)
            tx = VersionedTransaction(tx1.message, [KEY])
            tx_id = http_client.send_raw_transaction(
                bytes(tx), TxOpts(skip_preflight=True)).value
            print(f"https://solscan.io/tx/{str(tx_id)}")
    except Exception as e:
        print(f"Error executing trade: {e}")


def evaluate_market_cap(token_data):
    if token_data is None:
        return
    market_cap = token_data['market_cap']
    if market_cap >= ENTRY_MARKET_CAP and market_cap < STOP_LOSS_MARKET_CAP:
        print(f"Entering trade. Market cap: {market_cap}")
        execute_trade(token_data['address'], 'buy', BUY_AMOUNT)
    elif market_cap <= STOP_LOSS_MARKET_CAP:
        print(f"Executing stop loss. Market cap: {market_cap}")
        execute_trade(token_data['address'], 'sell',
                      1.0)  # Sell 100% to stop loss
    elif market_cap >= TAKE_PROFIT_MARKET_CAP_90 and market_cap < TAKE_PROFIT_MARKET_CAP_10:
        print(f"Taking profit 90%. Market cap: {market_cap}")
        execute_trade(token_data['address'], 'sell', SELL_PERCENT_90)
    elif market_cap >= TAKE_PROFIT_MARKET_CAP_10:
        print(f"Taking profit remaining 10%. Market cap: {market_cap}")
        execute_trade(token_data['address'], 'sell', SELL_PERCENT_10)


def monitor_tokens(token_address):
    while True:
        token_data = get_token_data(token_address)
        evaluate_market_cap(token_data)
        time.sleep(60)  # Check every 60 seconds


# Example token address for Birdeye
token_address = ''

# Start monitoring the token
monitor_tokens(token_address)
