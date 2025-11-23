from eth_account import Account
import os
from web3 import Web3

class WalletManager:
    """Handles virtual NGO wallets."""

    @staticmethod
    def create_wallet():
        acct = Account.create()
        return {
            "address": acct.address,
            "private_key": acct._private_key.hex()
        }

    @staticmethod
    def sign_and_send(private_key, tx):
        acct = Account.from_key(private_key)
        signed = acct.sign_transaction(tx)
        return signed
