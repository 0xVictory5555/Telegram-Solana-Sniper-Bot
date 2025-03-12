import pandas as pd
import dontshare as d
import requests
import json
import requests
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.rpc import types
import base58
import base64
import asyncio
import time
from solders.message import to_bytes_versioned, Message
from solders.transaction import Transaction, VersionedTransaction
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.token.associated import get_associated_token_address
from solders.hash import Hash
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from spl.token.instructions import create_associated_token_account
import threading

API_KEY = d.birdeye
PRIVATE_KEY = d.key
HELIUS_API_KEY = d.HELIUS_API_KEY
WALLET_ADDRESS = d.WALLET_ADDRESS
JUPITER_QUOTE_URI = 'https://quote-api.jup.ag/v6/quote'
JUPITER_SWAP_URP = "https://quote-api.jup.ag/v6/swap"

solana_client = Client("https://api.mainnet-beta.solana.com")


def get_buying_token():
    try:
        data_array = pd.read_csv('data/new_launches.csv', on_bad_lines='skip')
        data = data_array.to_numpy()
    except pd.errors.ParserError as e:
        print(f"ParserError: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    buying_tokens = []

    for row in data:
        buying_tokens.append({
            'address': row[1],
            'price': row[2],
            'amount': row[3]
        })  # Adjust indices based on your data structure
    return buying_tokens


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
    if transaction_type == "buy":
        swapMode = "ExactOut"
    else:
        swapMode = "ExactIn"

    params = {
        'inputMint': from_token_mint,
        'outputMint': to_token_mint,
        'amount': amount,
        'slippageBps': 10000
    }

    # print(params)

    headers = {'Accept': 'application/json'}
    response = requests.get(JUPITER_QUOTE_URI, headers=headers, params=params)
    if response.status_code == 200:
        # print(response)
        return response.json()
    else:
        #print(f"Error getting swap route: {response.json()}")
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
    #print("body: {}".format(body))
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    response = requests.post(JUPITER_SWAP_URP,
                             headers=headers,
                             data=json.dumps(body))
    #print("res from jup_swap: {}".format(response.json()))
    if response.status_code == 200:
        return response  # Get the first best route
    else:
        print(f"Error getting swap res: {response.json()}")
        return None


def send_swap_transaction(swapResponse):
    # Create the transaction
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
    #print(quote_res)
    if quote_res:
        if transaction_type == "buy":
            in_amount = min(int(quote_res["inAmount"]), max_buy_amount)
        balance = get_token_balance(
            base58.b58encode(
                sender_keypair.pubkey().__bytes__()).decode('utf-8'),
            base_token, HELIUS_API_KEY)
        #print(balance)
        if balance <= 0:
            return None
        elif balance <= in_amount:
            in_amount = balance
            quote_res = get_quote(base_token, quote_token, in_amount, dex,
                                  "sell")
        if quote_res != None:
            #print(quote_res)
            swap_res = build_swap_transaction_jup(quote_res, sender_keypair)
            if swap_res and swap_res.status_code == 200:
                tx_response = send_swap_transaction(swap_res.json())
                if tx_response:
                    txn_hash = tx_response['result']
                    #print(txn_hash)
                    return txn_hash
                else:

                    return None
            else:
                return None
        else:
            return None
    else:
        print("error")


def get_token(wallet_address, helius_api_key):
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
                "programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            }, {
                "encoding": "jsonParsed",
                "commitment": "confirmed"
            }
        ]
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if "result" in response.json():
        wallet_tokens = []
        result = response.json()['result']['value']
        if result:
            for account in result:
                balance = account['account']['data']['parsed']['info'][
                    'tokenAmount']['uiAmount']
                if balance > 0:
                    wallet_tokens.append(
                        account['account']['data']['parsed']['info'])
        return wallet_tokens
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None


def get_token_2022(wallet_address, helius_api_key):
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
                "programId": "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
            }, {
                "encoding": "jsonParsed",
                "commitment": "confirmed"
            }
        ]
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if "result" in response.json():
        wallet_tokens = []
        result = response.json()['result']['value']
        if result:
            for account in result:
                balance = account['account']['data']['parsed']['info'][
                    'tokenAmount']['uiAmount']
                if balance > 0:
                    wallet_tokens.append(
                        account['account']['data']['parsed']['info'])
        return wallet_tokens
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None


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
    postBalance_sol = 0
    preBalance_sol = 0
    if transaction_information is not None:
        # Safely access keys using get()
        result = transaction_information.get("result")
        if result is not None:
            meta = result.get("meta")
            if meta is not None:
                postTokenBalances = meta.get("postTokenBalances")
                preTokenBalances = meta.get("preTokenBalances")
                if postTokenBalances is not None and preTokenBalances is not None:
                    for i in postTokenBalances:
                        if i.get(
                                "mint"
                        ) == "So11111111111111111111111111111111111111112":
                            postBalance_sol = i.get("uiTokenAmount",
                                                    {}).get("uiAmount")
                            #print(balance_token)  # Output the balance_token
                    for i in preTokenBalances:
                        if i.get(
                                "mint"
                        ) == "So11111111111111111111111111111111111111112":
                            preBalance_sol = i.get("uiTokenAmount",
                                                   {}).get("uiAmount")
    if preBalance_sol and postBalance_sol:
        profit = float(preBalance_sol) - float(postBalance_sol)
        return (profit)


def get_token_price(token_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Assuming the price is in the 'pair' object
            price = data['pairs'][0]['priceNative']
            return price
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        #print(f"An error occurred: {e}")
        return None


def buy_token_information(token):

    timer = 0
    while True:
        if timer > 20:
            return 0
        timer += 1
        transactions_infor = []
        buying_price = token['price']
        token_address = token['address']
        price = get_token_price(token_address)

        if price is not None and float(price) < 0.0000000001:
            df = pd.read_csv('data/new_launches.csv')
            factor = token_address
            df = df[~df.apply(
                lambda row: row.astype(str).str.contains(factor).any(), axis=1
            )]
            df.to_csv('data/new_launches.csv', index=False)
            return 0

        elif price is not None and float(price) > float(buying_price) * 1.1:
            #print(token_address, price, buying_price)
            transaction_hash = send_trade_to_dex(
                10000000000000000, token_address,
                "So11111111111111111111111111111111111111112", "DEX", "sell",
                100)
            if transaction_hash:
                #print(transaction_hash)
                if get_transaction_price(transaction_hash,
                                         HELIUS_API_KEY) != 0:
                    profit = get_transaction_price(transaction_hash,
                                                   HELIUS_API_KEY) - d.sol
                    #print(f"https://solscan.io/tx/{transaction_hash}")
                    #print("profit", profit)
                    transaction_url = f"https://solscan.io/tx/{transaction_hash}"
                    df = pd.read_csv('data/new_launches.csv')
                    factor = token_address
                    df = df[~df.apply(lambda row: row.astype(str).str.contains(
                        factor).any(),
                                      axis=1)]
                    df.to_csv('data/new_launches.csv', index=False)
                    transactions_infor.append({
                        "type": "SELL",
                        "transaction": transaction_hash,
                        "transaction_url": transaction_url,
                        "profit": profit
                    })
            else:
                df = pd.read_csv('data/new_launches.csv')
                factor = token_address
                df = df[~df.apply(lambda row: row.astype(str).str.contains(
                    factor).any(),
                                  axis=1)]
                df.to_csv('data/new_launches.csv', index=False)
                return 0
        elif price is not None and float(price) < float(buying_price) * 0.3:
            #print(token_address, price, buying_price)
            transaction_hash = send_trade_to_dex(
                1000000000000000, token_address,
                "So11111111111111111111111111111111111111112", "DEX", "sell",
                100)
            if transaction_hash:
                loss = get_transaction_price(transaction_hash,
                                                      HELIUS_API_KEY) - d.sol
                #print(f"https://solscan.io/tx/{transaction_hash}")
                transaction_url = f"https://solscan.io/tx/{transaction_hash}"
                #print("Loss", loss)
                df = pd.read_csv('data/new_launches.csv')
                factor = token_address
                df = df[~df.apply(lambda row: row.astype(str).str.contains(
                    factor).any(),
                                  axis=1)]
                df.to_csv('data/new_launches.csv', index=False)
                transactions_infor.append({
                    "type": "SELL",
                    "transaction": transaction_hash,
                    "transaction_url": transaction_url,
                    "profit": loss
                })
            else:
                # df = pd.read_csv('data/new_launches.csv')
                # factor = token_address
                # df = df[~df.apply(lambda row: row.astype(str).str.contains(
                #     factor).any(),
                #                   axis=1)]
                # df.to_csv('data/new_launches.csv', index=False)
                return 0

        if transactions_infor:
            result = json.dumps(transactions_infor, indent=4)
            result_type = "💎💎💎 " + transactions_infor[0]["type"] + " 💎💎💎"
            result_transaction = transactions_infor[0]["transaction"]
            result_transaction_url = transactions_infor[0]["transaction_url"]
            result_profit = transactions_infor[0]["profit"]
            result_profit_str = f"{result_profit:.9f}"
            token = "7221811319:AAEa58VnjDPWXDqiLmYPF9CcvkyKwd9kVys"
            url = f'https://api.telegram.org/bot{token}/sendMessage'
            if result_profit>0:
                data = {
                    'chat_id': d.chat_id,
                    'text': result_type + '\n' + result_transaction_url + '\n' +"💰 Profit: "+result_profit_str+"SOL"+"  ❤"
                }
            else:
                data = {
                    'chat_id': d.chat_id,
                    'text': result_type+ '\n' + result_transaction_url + '\n' +"💰 Loss: "+result_profit_str+"SOL"+"  😥"
                }
            requests.post(url, data).json()
            return transactions_infor  # Return only the transactions information
        time.sleep(1)


def main():
    buying_tokens = get_buying_token()
    for i in buying_tokens:
        buying_price = i['price']
        token_address = i['address']
        if float(buying_price) == 0:
            df = pd.read_csv('data/new_launches.csv')
            factor = token_address
            df = df[~df.apply(
                lambda row: row.astype(str).str.contains(factor).any(), axis=1
            )]
            # Save the updated DataFrame back to CSV
            df.to_csv('data/new_launches.csv', index=False)
    buying_tokens = get_buying_token()
    #print(buying_tokens)
    threads = []
    for i in buying_tokens:
        thread = threading.Thread(target=buy_token_information, args=(i, ))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()


#main()
