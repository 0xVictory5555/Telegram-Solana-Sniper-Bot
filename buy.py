import pandas as pd
import dontshare as d  # this is where the Birdseye API key is stored named birdeye
import requests
import time
import json
import base64
import re as reggie
import base58
from base58 import b58decode
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.rpc import types
from solders.message import to_bytes_versioned, Message
from solders.transaction import Transaction, VersionedTransaction
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.token.associated import get_associated_token_address
from solders.hash import Hash
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
import asyncio

solana_client = Client("https://api.mainnet-beta.solana.com")
rpc_url = "https://api.mainnet-beta.solana.com"

# Configuration
PRIVATE_KEY = d.key
API_KEY = d.birdeye
HELIUS_API_KEY = d.HELIUS_API_KEY
WALLET_ADDRESS = d.WALLET_ADDRESS
JUPITER_QUOTE_URI = 'https://quote-api.jup.ag/v6/quote'
JUPITER_SWAP_URI = "https://quote-api.jup.ag/v6/swap"


# Function to safely make GET requests with retries
def safe_get(url, headers, retries=3, delay=2):
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers,
                                    timeout=10)  # 10 seconds timeout
            response.raise_for_status()  # Raise an error for bad responses
            return response
        except (requests.exceptions.RequestException, ConnectionError) as e:
            #print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(delay)
    return None  # Return None if all attempts fail

# Snipe new token_list
def get_new_token():
    new_token_url = f"https://public-api.birdeye.so/defi/v2/tokens/new_listing?limit=20&meme_platform_enabled=false"
    headers = {
        "accept": "application/json",
        "x-chain": "solana",
        "X-API-KEY": API_KEY
    }

    response = safe_get(new_token_url, headers)
    if response and response.status_code == 200:
        return response.json().get('data', {})
    else:
        print(
            f"Failed to retrieve new token: {response.status_code if response else 'No response'}"
        )
        return {}


def get_token_security(data):
    new_token_time = []
    for i in data:
        address = i['address']
        url = "https://public-api.birdeye.so/defi/token_security?address=FEZUSUS8AiEUPFfzBGVGQiw9pvgSzcZLEo4YCJeHKxoj"
        security_url = f"https://public-api.birdeye.so/defi/token_security?address={address}"
        headers = {"X-API-KEY": API_KEY}

        response = safe_get(security_url, headers)

        if response and response.status_code == 200:
            token_infor = response.json().get('data', {})
            #print("dsfasdf", token_infor)
            token_time = token_infor.get('mintTime')
            token_transfer = token_infor.get('transferFeeEnable')
            if token_time is None and token_transfer is None:
                new_token_time.append(i)
            elif token_time is not None and token_transfer is None and (
                    time.time() - token_time < 120):
                new_token_time.append(i)
        #time.sleep(0.5)

    return new_token_time


def birdeye_bot():
    new_tokens = get_new_token()
    tokens = new_tokens['items']
    df = pd.DataFrame(tokens)

    # Save the DataFrame to a local CSV file
    df.to_csv("data/filtered_pricechange_with_urls.csv", index=False)
    pd.set_option('display.max_columns', None)  # Show all columns

    return tokens


def token_overview(token):
    new_tokens_infor = []
    for i in token:
        overview_url = f"https://public-api.birdeye.so/defi/token_overview?address={i['address']}"
        headers = {"X-API-KEY": API_KEY}

        response = safe_get(overview_url, headers)

        if response and response.status_code == 200:
            overview_data = response.json().get('data', {})
            if overview_data and 'name' in overview_data and 'price' in overview_data:
                if overview_data['price'] is not None and overview_data[
                        'price'] > 0.0001:
                    new_tokens_infor.append({
                        'name': overview_data['name'],
                        'address': overview_data['address'],
                        'price': overview_data['price'],
                    })
            # else:
            #     print(
            #         f"Missing keys in overview_data for address {i['address']}: {overview_data}"
            #     )
        else:
            print(
                f"Failed to retrieve token overview: HTTP status code {response.status_code if response else 'No response'}"
            )
    return new_tokens_infor


def get_transaction_price(transaction_hash, helius_api_key):
    url = f"https://mainnet.helius-rpc.com/?api-key={helius_api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc":
        "2.0",
        "id":
        1,
        "method":
        "getTransaction",
        "params": [
            transaction_hash, {
                "encoding": "jsonParsed",
                "maxSupportedTransactionVersion": 0,
                "commitment": "confirmed"
            }
        ]
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    transaction_information = response.json()
    balance_token = 0
    if transaction_information is not None:
        result = transaction_information.get("result")
        if result is not None:
            meta = result.get("meta")
            if meta is not None:
                postTokenBalances = meta.get("postTokenBalances")
                if postTokenBalances is not None:
                    for i in postTokenBalances:
                        if i.get("owner") == WALLET_ADDRESS:
                            balance_token = i.get("uiTokenAmount",
                                                  {}).get("uiAmount")

    if float(balance_token) > 0:
        token_price = d.sol / float(balance_token)
        return {"price": token_price, "balance": float(balance_token)}


def get_balance(wallet_address, helius_api_key):
    url = f"https://mainnet.helius-rpc.com/?api-key={helius_api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "getBalance",
        "params": [wallet_address]
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if "result" in response.json():
        result = response.json()['result']['value']
        return result
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None


def get_token_balance(wallet_address, token_mint_address, helius_api_key):
    url = f"https://mainnet.helius-rpc.com/?api-key={helius_api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc":
        "2.0",
        "id":
        111,
        "method":
        "getTokenAccountsByOwner",
        "params": [
            wallet_address, {
                "mint": token_mint_address
            }, {
                "encoding": "jsonParsed",
                "commitment": "confirmed"
            }
        ]
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if "result" in response.json():
        result = response.json()['result']['value']
        if result:
            for account in result:
                if account['account']['data']['parsed']['info'][
                        'mint'] == token_mint_address:
                    balance = account['account']['data']['parsed']['info'][
                        'tokenAmount']['amount']
                    return int(balance)
        return 0
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None


def get_quote(from_token_mint, to_token_mint, amount, dex, transaction_type):
    swapMode = "ExactOut" if transaction_type == "buy" else "ExactIn"
    params = {
        'inputMint': from_token_mint,
        'outputMint': to_token_mint,
        'amount': amount,
        'slippageBps': 10000,
        'swapMode': swapMode,
    }

    headers = {'Accept': 'application/json'}
    response = requests.get(JUPITER_QUOTE_URI, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting swap route: {response.json()}")
        return None


def build_swap_transaction_jup(quote_res: any, wallet: Keypair):
    body = {
        'quoteResponse':
        quote_res,
        'userPublicKey':
        base58.b58encode(wallet.pubkey().__bytes__()).decode('utf-8'),
        'dynamicComputeUnitLimit':
        True,
        'wrapAndUnwrapSol':
        True,
        'dynamicSlippage':
        True,
        'prioritizationFeeLamports': {
            'priorityLevelWithMaxLamports': {
                'maxLamports': 1000000,
                'priorityLevel': "veryHigh"
            }
        }
    }
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    response = requests.post(JUPITER_SWAP_URI,
                             headers=headers,
                             data=json.dumps(body))
    if response.status_code == 200:
        return response  # Get the first best route
    else:
        print(f"Error getting swap res: {response.json()}")
        return None


def send_swap_transaction(swapResponse):
    if swapResponse["simulationError"]:
        print("Simulation Error: ", swapResponse["simulationError"])
        return
    swap_instruction = swapResponse["swapTransaction"]
    transaction = VersionedTransaction.from_bytes(
        base64.b64decode(swap_instruction))
    sender_keypair = Keypair.from_base58_string(PRIVATE_KEY)
    signature = sender_keypair.sign_message(
        to_bytes_versioned(transaction.message))
    signed_transaction = VersionedTransaction.populate(transaction.message,
                                                       [signature])
    tx_response = solana_client.send_transaction(
        signed_transaction,
        types.TxOpts(skip_preflight=True,
                     skip_confirmation=False,
                     preflight_commitment="confirmed"))
    return json.loads(tx_response.to_json())


def send_trade_to_dex(amount, base_token, quote_token, dex, transaction_type,
                      max_buy_amount):
    sender_keypair = Keypair.from_base58_string(PRIVATE_KEY)
    amount = int(amount)
    quote_res = get_quote(base_token, quote_token, amount, dex,
                          transaction_type)
    in_amount = amount
    if quote_res:
        if transaction_type == "buy":
            in_amount = min(int(quote_res["inAmount"]), max_buy_amount)
        balance = get_balance(
            base58.b58encode(
                sender_keypair.pubkey().__bytes__()).decode('utf-8'),
            HELIUS_API_KEY)
        if balance <= 0:
            return None
        elif balance <= in_amount:
            in_amount = balance
            quote_res = get_quote(base_token, quote_token, in_amount, dex,
                                  "sell")
        #print(quote_res['routePlan'][0]['swapInfo']['label'])
        if quote_res != None and quote_res['routePlan'][0]['swapInfo'][
                'label'] != "FluxBeam":

            swap_res = build_swap_transaction_jup(quote_res, sender_keypair)
            if swap_res and swap_res.status_code == 200:
                tx_response = send_swap_transaction(swap_res.json())
                if tx_response:
                    txn_hash = tx_response['result']
                    return txn_hash
                else:
                    print("hash error")
                    return None
            else:
                print("swap error")
                return None
    else:
        print("error")


def main():
    data = birdeye_bot()
    new_tokens = get_token_security(data)
    new_tokens_infor = token_overview(new_tokens)
    transactions_infor = []
    if new_tokens_infor:
        i = new_tokens_infor[0]
        mint_address = i['address']
        transaction = send_trade_to_dex(
            1000000000*d.sol, "So11111111111111111111111111111111111111112",
            mint_address, "dex", "sell", 100)
        transaction_url = f"https://solscan.io/tx/{transaction}"
        token_transaction = get_transaction_price(transaction, HELIUS_API_KEY)
        print(transaction)
        token_price = 0
        token_balance = 0
        if token_transaction is not None:
            token_price = token_transaction.get("price")
            token_balance = token_transaction.get("balance")
            transactions_infor.append({
                "type": "BUY",
                "transaction": transaction,
                "transaction_url": transaction_url
            })
        i['price'] = token_price
        i['amount'] = token_balance
        new = []
        new.append(i)
        df = pd.DataFrame(new)

        # Append to the existing CSV file
        df.to_csv("data/new_launches.csv", mode='a', header=False, index=False)

        pd.set_option('display.max_columns', None)

    if transactions_infor:
        return transactions_infor

# main()
