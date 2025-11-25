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

# On recalcule toujours depuis 3 ans (ou depuis la date de création si plus récent)
HISTO_START = "2022-01-01"   # ← 3 ans d’historique (tu peux mettre "2020-01-01" si tu veux plus)

# Mapping des actifs spéciaux
TICKER_MAP = {
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "Or physique": "GC=F",
    "GOLD": "GC=F",
    "Cash & stablecoins": "BIL",
    "USDT": "BIL",
    "Nestlé": "NSRGY",           # ADR Nestlé (le plus fiable)
    "Novo Nordisk": "NVO",       # ADR
    "ASML": "ASML.AS",
    "LVMH": "MC.PA",
    "Hermès": "RMS.PA",
}

BENCHMARKS = {"SP500": "^GSPC", "NASDAQ": "^IXIC"}

def get_ticker(actif: str) -> str:
    return TICKER_MAP.get(actif.strip(), actif.strip().upper().replace(" ", ""))

# ==================== CHARGEMENT COMPO ====================
df = pd.read_csv(COMPO_PATH)
df["Pondération"] = df["Pondération"].str.rstrip('%').astype(float) / 100
df["Date de mise à jour"] = pd.to_datetime(df["Date de mise à jour"], dayfirst=True)
compo = df.loc[df.groupby("Portefeuille")["Date de mise à jour"].idxmax()]

# ==================== TÉLÉCHARGEMENT ====================
tickers = [get_ticker(a) for a in compo["Actif"]] + list(BENCHMARKS.values())
tickers = sorted(set(tickers))

print(f"Téléchargement de {len(tickers)} actifs depuis {HISTO_START}…")
data = yf.download(tickers, start=HISTO_START, progress=False, threads=True)
prices = data["Close"] if data["Close"].ndim == 1 else data["Close"]  # robuste

# Forcer benchmarks
for t in BENCHMARKS.values():
    if t not in prices.columns:
        prices[t] = yf.download(t, start=HISTO_START, progress=False)["Close"]

# ==================== CALCUL PAR PORTEFEUILLE ====================
for pf_name in compo["Portefeuille"].unique():
    sub = compo[compo["Portefeuille"] == pf_name]
    sub = sub.copy()
    sub["ticker"] = sub["Actif"].apply(get_ticker)

    # Vérifier les actifs manquants
    missing = sub[~sub["ticker"].isin(prices.columns)]["Actif"].tolist()
    if missing:
        print(f"{pf_name} → actifs non trouvés : {missing}")

    valid = sub[sub["ticker"].isin(prices.columns)]
    weights = valid.set_index("ticker")["Pondération"].to_dict()

    # Retours du portefeuille
    returns = prices[list(weights.keys())].pct_change()
    pf_returns = (returns * pd.Series(weights)).sum(axis=1)
    pf_returns = pf_returns.dropna()

    if pf_returns.empty:
        print(f"{pf_name} → pas de données")
        continue

    # NAV depuis HISTO_START
    nav = (1 + pf_returns).cumprod() * 100
    sp_nav = (1 + prices[BENCHMARKS["SP500"]].pct_change().loc[pf_returns.index]).cumprod() * 100
    nas_nav = (1 + prices[BENCHMARKS["NASDAQ"]].pct_change().loc[pf_returns.index]).cumprod() * 100

    # Métriques du dernier jour
    last_ret = pf_returns.iloc[-1]
    week_ret = (1 + pf_returns[-5:]).prod() - 1 if len(pf_returns) >= 5 else 0
    month_ret = (1 + pf_returns[-21:]).prod() - 1 if len(pf_returns) >= 21 else 0

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
        "Return_Port_Daily": round(last_ret * 100, 2),
        "Return_Port_Weekly": round(week_ret * 100, 2),
        "Return_Port_Monthly": round(month_ret * 100, 2),
        "Return_SP_Daily": round(prices[BENCHMARKS["SP500"]].pct_change().iloc[-1] * 100, 2),
        "Return_SP_Weekly": round((1 + prices[BENCHMARKS["SP500"]].pct_change()[-5:]).prod() - 1, 4) * 100,
        "Return_SP_Monthly": round((1 + prices[BENCHMARKS["SP500"]].pct_change()[-21:]).prod() - 1, 4) * 100,
        "Return_NASDAQ_Daily": round(prices[BENCHMARKS["NASDAQ"]].pct_change().iloc[-1] * 100, 2),
        "Return_NASDAQ_Weekly": round((1 + prices[BENCHMARKS["NASDAQ"]].pct_change()[-5:]).prod() - 1, 4) * 100,
        "Return_NASDAQ_Monthly": round((1 + prices[BENCHMARKS["NASDAQ"]].pct_change()[-21:]).prod() - 1, 4) * 100,
    }

    filename = f"perf_{pf_name.lower().replace(' ', '_')}.csv"
    path = DATA_DIR / filename

    # Écrase ou ajoute la ligne du jour
    df = pd.DataFrame([row])
    if path.exists():
        old = pd.read_csv(path)
        if len(old) and old.iloc[-1]["Date"] == row["Date"]:
            old.iloc[-1] = row
        else:
            old = pd.concat([old, df], ignore_index=True)
        old.to_csv(path, index=False)
    else:
        df.to_csv(path, index=False)

    print(f"{pf_name} → NAV {row['Portfolio_CumReturn']} | Vol {row['Vol_Daily']}% | DD {row['Drawdown_Max']}%")

print("Mise à jour quotidienne terminée – historique 3 ans complet")
