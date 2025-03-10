# this file manually buys and sells on jupiter
# keep in mind the amount is in lamports so 1 sol would be 1000000000
# https://www.solconverter.com/
# 0.005 sol is 5000000 lamports
# 0.01 sol is 10000000 lamports
# 0.03 sol is 30000000 lamports
# 0.05 sol is 50000000 lamports
# 0.10 sol is 100000000 lamports
# example - to run the code: "python jup.py 8wXtPeU6557ETkp9WHFY1n1EcU6NxDvbAggHGsMYiHsB 100" (buy order for 0.001471656 ($0.000028) GME)


# solana_sniper chat - moondevonyt@gmail.com

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

import requests
import sys
import json 
import base64
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction 
from solana.rpc.api import Client 
from solana.rpc.types import TxOpts
import dontshare as d 

if len(sys.argv) < 3:
    print("Usage: python jup.py <token> <amount>")
    sys.exit(1)

# KEY FROM THE FILE DONTSHARE
KEY = Keypair.from_base58_string(d.key)
SLIPPAGE = 50
QUOTE_TOKEN = 'So11111111111111111111111111111111111111112'

token = sys.argv[1]
amount = sys.argv[2]

http_client = Client("https://api.mainnet-beta.solana.com")

quote = requests.get(f'https://quote-api.jup.ag/v6/quote?inputMint={QUOTE_TOKEN}\
&outputMint={token}\
&amount={amount}\
&slippageBps={SLIPPAGE}').json()
txRes = requests.post('https://quote-api.jup.ag/v6/swap',headers={"Content-Type": "application/json"}, data=json.dumps({"quoteResponse": quote, "userPublicKey": str(KEY.pubkey()) })).json()
swapTx = base64.b64decode(txRes['swapTransaction'])
tx1 = VersionedTransaction.from_bytes(swapTx)
tx = VersionedTransaction(tx1.message, [KEY])
txId = http_client.send_raw_transaction(bytes(tx), TxOpts(skip_preflight=True)).value
print(f"https://solscan.io/token/{str(txId)}")