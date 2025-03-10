import requests
import json

transaction_hash = "4fsPPxQVKxzxtP3vq2dWQdUAtsDjuTCeM2qeubVitjajx4HXAXagEQUhCr4vVToDvEbumV8zjwd9V1qtYco4tK2R"
HELIUS_API_KEY = "8013b84f-3db2-4e68-b05e-9f6a98159afb"


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
                "maxSupportedTransactionVersion": 0
            }
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    transaction_information = response.json()
    balance_token = 0
    if transaction_information is not None:
        # Safely access keys using get()
        result = transaction_information.get("result")
        if result is not None:
            meta = result.get("meta")
            if meta is not None:
                postTokenBalances = meta.get("postTokenBalances")
                if postTokenBalances is not None:
                    for i in postTokenBalances:
                        if i.get(
                                "owner"
                        ) == "Ee81iidJrGRVroesdyyWpS2GMAPi3S4TTwu5gEtkm7AM":
                            balance_token = i.get("uiTokenAmount",
                                                  {}).get("amount")
                            print(balance_token)  # Output the balance_token
                else:
                    print("postTokenBalances is None")
            else:
                print("meta is None")
        else:
            print("result is None")
    else:
        print("transaction_information is None")
    if int(balance_token) > 0:
        token_price = 100000 / int(balance_token)
        return ({"price": token_price, "balance": int(balance_token)})


print(get_transaction_price(transaction_hash, HELIUS_API_KEY))
