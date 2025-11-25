#!/usr/bin/env python3
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
from pathlib import Path

# ==================== CONFIG ====================
ROOT = Path(__file__).parent.parent
COMPO_PATH = ROOT / "data" / "composition_portefeuilles.csv"
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Historique complet depuis 3 ans (ou plus si tu veux)
HISTO_START = "2022-01-01"   # ← c’est ça qui te donne des vraies perfs

TICKER_MAP = {
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "Or physique": "GC=F",
    "GOLD": "GC=F",
    "Cash & stablecoins": "BIL",
    "USDT": "BIL",
    "Nestlé": "NSRGY",
    "Novo Nordisk": "NVO",
    "ASML": "ASML.AS",
    "LVMH": "MC.PA",
    "Hermès": "RMS.PA",
    "Ferrari": "RACE.MI",
}

BENCHMARKS = {"SP500": "^GSPC", "NASDAQ": "^IXIC"}

def get_ticker(actif):
    return TICKER_MAP.get(actif.strip(), actif.strip().upper().replace(" ", ""))

# ==================== CHARGEMENT ====================
print("Chargement des compositions...")
df = pd.read_csv(COMPO_PATH)
df["Pondération"] = df["Pondération"].str.rstrip('%').astype(float) / 100
df["Date de mise à jour"] = pd.to_datetime(df["Date de mise à jour"], dayfirst=True)
compo = df.loc[df.groupby("Portefeuille")["Date de mise à jour"].idxmax()]

# ==================== TÉLÉCHARGEMENT ====================
tickers = [get_ticker(a) for a in compo["Actif"]] + list(BENCHMARKS.values())
tickers = sorted(set(tickers))

print(f"Téléchargement de {len(tickers)} actifs depuis {HISTO_START}…")
data = yf.download(tickers, start=HISTO_START, progress=False, threads=True)
prices = data["Close"]

# Forcer les benchmarks
for b in BENCHMARKS.values():
    if b not in prices.columns or prices[b].isna().all():
        prices[b] = yf.download(b, start=HISTO_START, progress=False)["Close"]

# ==================== CALCUL PAR PORTEFEUILLE ====================
for pf_name in compo["Portefeuille"].unique():
    sub = compo[compo["Portefeuille"] == pf_name].copy()
    sub["ticker"] = sub["Actif"].apply(get_ticker)

    missing = sub[~sub["ticker"].isin(prices.columns)]["Actif"].tolist()
    if missing:
        print(f"   {pf_name} → actifs non trouvés : {missing}")

    valid = sub[sub["ticker"].isin(prices.columns)]
    if valid.empty:
        print(f"   {pf_name} → aucun actif valide")
        continue

    weights = valid.set_index("ticker")["Pondération"]
    returns = prices[weights.index].pct_change()
    pf_returns = (returns * weights).sum(axis=1).dropna()

    if len(pf_returns) < 10:
        print(f"   {pf_name} → pas assez de données")
        continue

    nav = (1 + pf_returns).cumprod() * 100
    sp_nav = (1 + prices[BENCHMARKS["SP500"]].pct_change().loc[pf_returns.index]).cumprod() * 100
    nas_nav = (1 + prices[BENCHMARKS["NASDAQ"]].pct_change().loc[pf_returns.index]).cumprod() * 100
    dd_series = nav / nav.cummax() - 1

    row = {
        "Date": datetime.now().strftime("%Y-%m-%d"),
        "Portfolio_CumReturn": round(nav.iloc[-1], 2),
        "SP500_CumReturn": round(sp_nav.iloc[-1], 2),
        "NASDAQ_CumReturn": round(nas_nav.iloc[-1], 2),
        "Vol_Daily": round(pf_returns.std() * np.sqrt(252) * 100, 2),
        "Vol_Weekly": round(pf_returns.rolling(5).std().mean() * np.sqrt(52) * 100, 2),
        "Vol_Monthly": round(pf_returns.rolling(21).std().mean() * np.sqrt(12) * 100, 2),
        "Drawdown_Current": round(dd_series.iloc[-1] * 100, 2),
        "Drawdown_Max": round(dd_series.min() * 100, 2),
        "Return_Port_Daily": round(pf_returns.iloc[-1] * 100, 2),
        "Return_Port_Weekly": round(((1 + pf_returns[-5:]).prod() - 1) * 100, 2),
        "Return_Port_Monthly": round(((1 + pf_returns[-21:]).prod() - 1) * 100, 2),
        "Return_SP_Daily": round(prices[BENCHMARKS["SP500"]].pct_change().iloc[-1] * 100, 2),
        "Return_SP_Weekly": round(((1 + prices[BENCHMARKS["SP500"]].pct_change()[-5:]).prod() - 1) * 100, 2),
        "Return_SP_Monthly": round(((1 + prices[BENCHMARKS["SP500"]].pct_change()[-21:]).prod() - 1) * 100, 2),
        "Return_NASDAQ_Daily": round(prices[BENCHMARKS["NASDAQ"]].pct_change().iloc[-1] * 100, 2),
        "Return_NASDAQ_Weekly": round(((1 + prices[BENCHMARKS["NASDAQ"]].pct_change()[-5:]).prod() - 1) * 100, 2),
        "Return_NASDAQ_Monthly": round(((1 + prices[BENCHMARKS["NASDAQ"]].pct_change()[-21:]).prod() - 1) * 100, 2),
    }

    filename = f"perf_{pf_name.lower().replace(' ', '_')}.csv"
    path = DATA_DIR / filename
    df_new = pd.DataFrame([row])

    if path.exists():
        old = pd.read_csv(path)
        if len(old) and old.iloc[-1]["Date"] == row["Date"]:
            old.iloc[-1] = row
        else:
            old = pd.concat([old, df_new], ignore_index=True)
        old.to_csv(path, index=False)
    else:
        df_new.to_csv(path, index=False)

    print(f"{pf_name} → NAV {row['Portfolio_CumReturn']} | Vol {row['Vol_Daily']}% | DD max {row['Drawdown_Max']}%")

print("\nMise à jour terminée – historique complet depuis 2022")
