import os
import json
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, auth
import pandas as pd
import duckdb
from datetime import datetime

# ------------------- Firebase Admin Init -------------------
service_account_str = os.getenv("FIREBASE_SERVICE_ACCOUNT")
if not service_account_str:
    raise RuntimeError("FIREBASE_SERVICE_ACCOUNT secret manquant sur Render")

cred = credentials.Certificate(json.loads(service_account_str))
firebase_admin.initialize_app(cred)

# ------------------- FastAPI App -------------------
app = FastAPI(title="Portfolio API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://bq-python.github.io"],  # Ton GitHub Pages
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

class PositionsPayload(BaseModel):
    positions: dict  # {"AAPL": 10, "MSFT": 5}

@app.get("/")
def root():
    return {"status": "Backend OK", "time": datetime.utcnow().isoformat()}

@app.post("/portfolio/equity")
async def get_portfolio_equity(
    payload: PositionsPayload,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        decoded_token = auth.verify_id_token(credentials.credentials)
        uid = decoded_token['uid']
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token Firebase invalide")

    positions = payload.positions
    if not positions:
        return {"dates": [], "values": [], "metrics": {}}

    # TODO : quand tu auras ton prices.parquet → décommente ça
    # df_prices = pd.read_parquet("data/prices.parquet")
    # df_prices["Date"] = pd.to_datetime(df_prices["Date"])
    # df_prices = df_prices.set_index("Date")

    # Pour l’instant : on utilise yfinance (fallback)
    try:
        import yfinance as yf
        tickers = list(positions.keys())
        end = datetime.today()
        start = end - pd.Timedelta(days=730)
        data = yf.download(tickers, start=start, end=end, progress=False)["Adj Close"]
        equity = (data * pd.Series(positions)).sum(axis=1).dropna()
    except:
        raise HTTPException(status_code=500, detail="Erreur téléchargement prix")

    returns = equity.pct_change().dropna()
    total_return = (equity.iloc[-1] / equity.iloc[0] - 1) * 100
    sharpe = (returns.mean() * 252) / (returns.std() * (252**0.5)) if returns.std() != 0 else 0
    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax
    max_dd = drawdown.min() * 100

    return {
        "uid": uid,
        "dates": equity.index.strftime("%Y-%m-%d").tolist(),
        "values": equity.round(2).tolist(),
        "metrics": {
            "total_return_pct": round(total_return, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "final_value": round(equity.iloc[-1], 2),
            "initial_value": round(equity.iloc[0], 2)
        }
    }
