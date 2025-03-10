from solana.rpc.api import Client
from solana.rpc.commitment import Commitment
from solana.transaction import Transaction
from spl.token.instructions import (burn_checked, close_account,
                                    CloseAccountParams)
from solana.keypair import Keypair
from base58 import b58decode
from solana.publickey import PublicKey

# Replace this with your actual RPC endpoint
RPC_ENDPOINT = "https://api.mainnet-beta.solana.com"
client = Client(RPC_ENDPOINT)

# Load your wallet using the private key
private_key = "3YjQe4DTSrgB8cuGghJBKyYmwxGa18ZkHZEhL6qFwQAFpPQS4PM1uBoo7NqssAcXSRUKhzf6HwsLemMifvsZtSAZ"
wallet = Keypair.from_secret_key(b58decode(private_key))


# Function to burn and close token account
def burn_and_close_token(token_account, mint, wallet_pubkey, amount, decimals,
                         program_id):
    instructions = []

    # Create burn instruction (commented out, as you are not burning tokens)
    # burn_ix = burn_checked(
    #     program_id=program_id,
    #     mint=mint,
    #     source=token_account,
    #     owner=wallet_pubkey,
    #     amount=amount,
    #     decimals=decimals,
    # )
    # instructions.append(burn_ix)

    # Create close instruction
    params = CloseAccountParams(account=token_account,
                                dest=wallet_pubkey,
                                owner=wallet_pubkey,
                                program_id=program_id)

    close_ix = close_account(params)
    instructions.append(close_ix)

    return instructions


# Main execution
def main():
    token_account = PublicKey(
        "HvpeSdTYZjAjFGnf6726jet78x7SoNtfAeF5bwGPKK98")  # Convert to Pubkey
    mint = PublicKey(
        "5Le3vFbrxgWogqxcaQnmnFcyz8hiLn5G2Wmzd9Pshr1Q")  # Convert to Pubkey
    amount = 2675  # Amount to burn
    decimals = 6  # Token decimals
    program_id = PublicKey(
        "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")  # Convert to Pubkey

    instructions = burn_and_close_token(token_account, mint, wallet.public_key,
                                        amount, decimals, program_id)

    # Create and send transaction
    transaction = Transaction(instructions=instructions)
    response = client.send_transaction(transaction, wallet)

    print("Transaction response:", response)


if __name__ == "__main__":
    main()
