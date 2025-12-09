# app/models/blockchain_credit.py
from mongoengine import Document, StringField, IntField, DateTimeField
import datetime

class BlockchainCredit(Document):
    project_id = StringField(required=True)
    ngo_address = StringField(required=True)
    amount = IntField(required=True)
    tx_hash = StringField(required=True)

    created_at = DateTimeField(default=datetime.datetime.utcnow)
