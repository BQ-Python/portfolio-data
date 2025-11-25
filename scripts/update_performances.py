#!/usr/bin/env python3
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
from pathlib import Path

# ==================== CONFIG ====================
ROOT = Path(__file__).parent.parent
COMPO_FILE = ROOT / "data" / "composition_portefeuilles.csv"
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# On recalcule tout depuis cette date (ou depuis la création du portefeuille si plus récent)
START_DATE = "2022-01-01"

# Benchmarks
SP500 = "^GSPC"
NASDAQ = "^IXIC"

# ==================== CHARGEMENT COMPO ====================
print("Chargement de composition_portefeuilles.csv...")
df = pd.read_csv(COMPO_FILE)
df["Pondération"] = df["Pondération"].str.replace("%", "").astype(float) / 100
df["Date de mise à jour"] = pd.to_datetime(df["Date de mise à jour"], dayfirst=True)

# Garder seulement la version la plus récente de chaque portefeuille
compo = df.loc[df.groupby("Portefeuille")["Date de mise à jour"].idxmax()].copy()

# ==================== TÉLÉCHARGEMENT DES COURS ====================
all_tickers = compo["Ticker"].tolist() + [SP500, NASDAQ]
all_tickers = sorted(set(all_tickers))

print(f"Téléchargement de {len(all_tickers)} tickers depuis {START_DATE}...")
data = yf.download(all_tickers, start=START_DATE, progress=False, threads=True)
prices = data["Close"]

# ==================== TRAITEMENT PAR PORTEFEUILLE ====================
for portefeuille in compo["Portefeuille"].unique():
    sub = compo[compo["Portefeuille"] == portefeuille].copy()
    inception = sub["Date de mise à jour"].iloc[0]
    start = max(pd.to_datetime(START_DATE), inception)  # max entre 2022 et création

    # Poids + tickers
    weights = dict(zip(sub["Ticker"], sub["Pondération"]))

    # Vérifier quels tickers sont disponibles
    available = [t for t in weights if t in prices.columns and not prices[t].isna().all()]
    missing = [t for t in weights if t not in available]
    if missing:
        print(f"   {portefeuille} → tickers manquants : {missing}")

    if not available:
        print(f"   {portefeuille} → aucun ticker valide → ignoré")
        continue

    # Retours du portefeuille
    returns = prices[available].pct_change()
    pf_returns = (returns * pd.Series({t: weights[t] for t in available})).sum(axis=1)
    pf_returns = pf_returns[pf_returns.index >= start.strftime("%Y-%m-%d")].dropna()

    if len(pf_returns) < 20:
        print(f"   {portefeuille} → pas assez de données ({len(pf_returns)} jours)")
        continue

    # NAV + benchmarks
    nav = (1 + pf_returns).cumprod() * 100
    sp_returns = prices[SP500].pct_change().loc[pf_returns.index]
    nas_returns = prices[NASDAQ].pct_change().loc[pf_returns.index]
    sp_nav = (1 + sp_returns).cumprod() * 100
    nas_nav = (1 + nas_returns).cumprod() * 100

    # Drawdown
    dd = nav / nav.cummax() - 1

    # Ligne du jour
    today = datetime.now().strftime("%Y-%m-%d")
    row = {
        "Date": today,
        "Portfolio_CumReturn": round(nav.iloc[-1], 2),
        "SP500_CumReturn": round(sp_nav.iloc[-1], 2),
        "NASDAQ_CumReturn": round(nas_nav.iloc[-1], 2),
        "Vol_Daily": round(pf_returns.std() * np.sqrt(252) * 100, 2),
        "Vol_Weekly": round(pf_returns.rolling(5).std().mean() * np.sqrt(52) * 100, 2),
        "Vol_Monthly": round(pf_returns.rolling(21).std().mean() * np.sqrt(12) * 100, 2),
        "Drawdown_Current": round(dd.iloc[-1] * 100, 2),
        "Drawdown_Max": round(dd.min() * 100, 2),
        "Return_Port_Daily": round(pf_returns.iloc[-1] * 100, 2),
        "Return_Port_Weekly": round(((1 + pf_returns[-5:]).prod() - 1) * 100, 2),
        "Return_Port_Monthly": round(((1 + pf_returns[-21:]).prod() - 1) * 100, 2),
        "Return_SP_Daily": round(sp_returns.iloc[-1] * 100, 2),
        "Return_SP_Weekly": round(((1 + sp_returns[-5:]).prod() - 1) * 100, 2),
        "Return_SP_Monthly": round(((1 + sp_returns[-21:]).prod() - 1) * 100, 2),
        "Return_NASDAQ_Daily": round(nas_returns.iloc[-1] * 100, 2),
        "Return_NASDAQ_Weekly": round(((1 + nas_returns[-5:]).prod() - 1) * 100, 2),
        "Return_NASDAQ_Monthly": round(((1 + nas_returns[-21:]).prod() - 1) * 100, 2),
    }

    # Sauvegarde
    filename = f"perf_{portefeuille.lower().replace(' ', '_')}.csv"
    path = DATA_DIR / filename
    df_row = pd.DataFrame([row])

    if path.exists():
        old = pd.read_csv(path)
        if not old.empty and old.iloc[-1]["Date"] == today:
            old.iloc[-1] = row
        else:
            old = pd.concat([old, df_row], ignore_index=True)
        old.to_csv(path, index=False)
    else:
        df_row.to_csv(path, index=False)

    print(f"{portefeuille} → NAV {row['Portfolio_CumReturn']} | Vol {row['Vol_Daily']}% | DD max {row['Drawdown_Max']}%")

print("\nMise à jour terminée – historique complet depuis 2022 (ou création)")
