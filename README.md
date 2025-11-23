.\.venv\Scripts\activate
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pip install -r requirements.nopillow.txt
pip install web3 python-dotenv
cd "C:\AquaCreds Backend\aquacreds-backend"
