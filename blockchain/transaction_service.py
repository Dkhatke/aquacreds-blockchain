from web3 import Web3
from web3.exceptions import ContractLogicError
from blockchain.web3_client import (
    w3, ADMIN_ADDRESS, ADMIN_PRIVATE_KEY, CHAIN_ID
)

class TxService:

    @staticmethod
    def send_user_tx(fn, private_key, user_address):

        user_address = Web3.to_checksum_address(user_address)
        nonce = w3.eth.get_transaction_count(user_address)

        txn = fn.build_transaction({
            "from": user_address,
            "nonce": nonce,
            "gas": 500000,
            "gasPrice": w3.eth.gas_price,
            "chainId": CHAIN_ID
        })

        signed = w3.eth.account.sign_transaction(txn, private_key)

        try:
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            return w3.eth.wait_for_transaction_receipt(tx_hash)

        except ContractLogicError as e:
            raise Exception(f"Smart contract error: {e}")

    @staticmethod
    def send_admin_tx(fn):

        nonce = w3.eth.get_transaction_count(ADMIN_ADDRESS)

        txn = fn.build_transaction({
            "from": ADMIN_ADDRESS,
            "nonce": nonce,
            "gas": 500000,
            "gasPrice": w3.eth.gas_price,
            "chainId": CHAIN_ID
        })

        signed = w3.eth.account.sign_transaction(txn, ADMIN_PRIVATE_KEY)

        try:
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            return w3.eth.wait_for_transaction_receipt(tx_hash)

        except ContractLogicError as e:
            raise Exception(f"Smart contract reverted: {e}")
