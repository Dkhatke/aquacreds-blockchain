from mongoengine import Document, StringField, BooleanField, DateTimeField
import datetime

class BlockchainMRV(Document):
    project_id = StringField(required=True)
    mrv_hash = StringField(required=True)
    verifier = StringField(required=True)
    submitted_tx = StringField(required=True)

    approved = BooleanField(default=False)
    approved_tx = StringField()
    
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    approved_at = DateTimeField()
