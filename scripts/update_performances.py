#!/usr/bin/env python3
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
from pathlib import Path

# ==================== CHEMINS ====================
ROOT = Path(__file__).parent.parent
COMPO_PATH = ROOT / "data" / "composition_portefeuilles.csv"   # ton vrai nom
TEST_DIR = ROOT / "data_test"
TEST_DIR.mkdir(exist_ok=True)

# ==================== MAPPING ACTIFS SPÉCIAUX ====================
TICKER_MAP = {
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "Or physique": "GC=F",
    "GOLD": "GC=F",
    "Cash & stablecoins": "BIL",
    "USDT": "BIL",
}

BENCHMARKS = {"SP500": "^GSPC", "NASDAQ": "^IXIC"}

def get_yf_ticker(actif: str) -> str:
    return TICKER_MAP.get(actif.strip(), actif.strip().upper().replace(" ", ""))

# ==================== CHARGEMENT COMPO ====================
def load_current_weights():
    df = pd.read_csv(COMPO_PATH)
    df["Pondération"] = df["Pondération"].str.replace('%', '').astype(float) / 100
    df["Date de mise à jour"] = pd.to_datetime(df["Date de mise à jour"], dayfirst=True)
    latest = df.loc[df.groupby("Portefeuille")["Date de mise à jour"].idxmax()]
    return latest

# ==================== CALCULS ====================
def calculate_metrics(daily_ret):
    if len(daily_ret) < 2:
        return {k: 0.0 for k in ["vol_d", "vol_w", "vol_m", "ret_d", "ret_w", "ret_m"]}
    vol_d = daily_ret.std() * np.sqrt(252) * 100
    vol_w = daily_ret.rolling(5).std().mean() * np.sqrt(52) * 100
    vol_m = daily_ret.rolling(21).std().mean() * np.sqrt(12) * 100
    ret_d = daily_ret.iloc[-1]
    ret_w = (1 + daily_ret[-5:]).prod() - 1 if len(daily_ret) >= 5 else 0
    ret_m = (1 + daily_ret[-21:]).prod() - 1 if len(daily_ret) >= 21 else 0
    return {k: round(v, 2) for k, v in zip(
        ["vol_d","vol_w","vol_m","ret_d","ret_w","ret_m"],
        [vol_d, vol_w, vol_m, ret_d*100, ret_w*100, ret_m*100]
    )}

def calculate_drawdown(nav):
    peak = nav.cummax()
    dd = (nav / peak) - 1
    return round(dd.iloc[-1]*100, 2), round(dd.min()*100, 2)

# ==================== MAIN ====================
print("Chargement des compositions...")
compo = load_current_weights()

tickers = [get_yf_ticker(t) for t in compo["Ticker"]] + list(BENCHMARKS.values())
tickers = sorted(set(tickers))

print(f"Téléchargement de {len(tickers)} tickers…")
data = yf.download(tickers, period="max", progress=False, threads=True)

# Correction : yfinance renvoie parfois une Series au lieu d’un DataFrame
if len(tickers) == 1:
    prices = pd.DataFrame(data["Adj Close"]).rename(columns={0: tickers[0]})
else:
    prices = data["Adj Close"]

# Forcer les benchmarks s’ils manquent
for name, t in BENCHMARKS.items():
    if t not in prices.columns or prices[t].isna().all():
        print(f"   → Forçage {name} ({t})")
        prices[t] = yf.download(t, period="max", progress=False)["Adj Close"]

for pf_name in compo["Portefeuille"].unique():
    print(f"\nTraitement → {pf_name}")
    sub = compo[compo["Portefeuille"] == pf_name].copy()
    sub["yf"] = sub["Actif"].apply(get_yf_ticker)

    missing = sub[~sub["yf"].isin(prices.columns)]["Actif"].tolist()
    if missing:
        print("   Non trouvés :", missing)

    valid = sub[sub["yf"].isin(prices.columns)]
    weights = valid.set_index("yf")["Pondération"]

    returns = prices[weights.index].pct_change()
    pf_ret = (returns * weights).sum(axis=1)
    start = sub["Date de mise à jour"].min().strftime("%Y-%m-%d")
    pf_ret = pf_ret[pf_ret.index >= start]

    if pf_ret.empty:
        print("   Pas de données → ignoré")
        continue

    nav = (1 + pf_ret).cumprod() * 100

    sp = prices[BENCHMARKS["SP500"]].pct_change()[pf_ret.index]
    nas = prices[BENCHMARKS["NASDAQ"]].pct_change()[pf_ret.index]
    sp_nav = (1 + sp).cumprod() * 100
    nas_nav = (1 + nas).cumprod() * 100

    met = calculate_metrics(pf_ret)
    sp_met = calculate_metrics(sp)
    nas_met = calculate_metrics(nas)
    dd_curr, dd_max = calculate_drawdown(nav)

    row = {
        "Date": datetime.now().strftime("%Y-%m-%d"),
        "Portfolio_CumReturn": round(nav.iloc[-1], 2),
        "SP500_CumReturn": round(sp_nav.iloc[-1], 2),
        "NASDAQ_CumReturn": round(nas_nav.iloc[-1], 2),
        "Vol_Daily": met["vol_d"],
        "Vol_Weekly": met["vol_w"],
        "Vol_Monthly": met["vol_m"],
        "Drawdown_Current": dd_curr,
        "Drawdown_Max": dd_max,
        "Return_Port_Daily": met["ret_d"],
        "Return_Port_Weekly": met["ret_w"],
        "Return_Port_Monthly": met["ret_m"],
        "Return_SP_Daily": sp_met["ret_d"],
        "Return_SP_Weekly": sp_met["ret_w"],
        "Return_SP_Monthly": sp_met["ret_m"],
        "Return_NASDAQ_Daily": nas_met["ret_d"],
        "Return_NASDAQ_Weekly": nas_met["ret_w"],
        "Return_NASDAQ_Monthly": nas_met["ret_m"],
    }

    filename = f"TEST_perf_{pf_name.lower().replace(' ', '_')}.csv"
    path = TEST_DIR / filename

    df = pd.DataFrame([row])
    if path.exists():
        old = pd.read_csv(path)
        if len(old) and old.iloc[-1]["Date"] == row["Date"]:
            old.iloc[-1] = row
            old.to_csv(path, index=False)
        else:
            pd.concat([old, df], ignore_index=True).to_csv(path, index=False)
    else:
        df.to_csv(path, index=False)

    print(f"   OK → {path.name} (NAV = {row['Portfolio_CumReturn']})")

print("\nTerminé ! Tous les CSV sont dans data_test/")
