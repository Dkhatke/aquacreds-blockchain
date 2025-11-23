from web3 import Web3
from web3.exceptions import ContractLogicError
from blockchain.web3_client import w3, ADMIN_ADDRESS, ADMIN_PRIVATE_KEY


class TxService:

    @staticmethod
    def send_user_tx(fn, private_key, user_address):

        # checksum wallet
        user_address = Web3.to_checksum_address(user_address)

        # get nonce
        nonce = w3.eth.get_transaction_count(user_address)

        # build tx
        txn = fn.build_transaction({
            "from": user_address,
            "nonce": nonce,
            "gas": 500000,
            "gasPrice": w3.eth.gas_price
        })

        # sign
        signed = w3.eth.account.sign_transaction(txn, private_key)

        try:
            # FIX: correct field name
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            return receipt

        except ContractLogicError as e:
            raise Exception(f"Smart contract reverted: {str(e)}")

        except Exception as e:
            raise Exception(f"Transaction failed: {str(e)}")


    @staticmethod
    def send_admin_tx(fn):

        nonce = w3.eth.get_transaction_count(ADMIN_ADDRESS)

        txn = fn.build_transaction({
            "from": ADMIN_ADDRESS,
            "nonce": nonce,
            "gas": 500000,
            "gasPrice": w3.eth.gas_price
        })

        signed = w3.eth.account.sign_transaction(txn, ADMIN_PRIVATE_KEY)

        try:
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            return receipt

        except ContractLogicError as e:
            raise Exception(f"Smart contract reverted: {str(e)}")

        except Exception as e:
            raise Exception(f"Transaction failed: {str(e)}")
