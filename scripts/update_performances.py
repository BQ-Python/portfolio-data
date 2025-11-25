#!/usr/bin/env python3
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
from pathlib import Path

# Chemins
ROOT = Path(__file__).parent.parent
COMPO_PATH = ROOT / "data" / "compositions_portefeuilles.csv"
DATA_DIR = ROOT / "data"

# Benchmarks
BENCHMARKS = {"SP500": "^GSPC", "NASDAQ": "^IXIC"}

# Mapper certains actifs non standards vers leur ticker yfinance
TICKER_MAP = {
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "Or physique": "GC=F",      # Gold futures
    "Cash & stablecoins": "BIL", # ETF ultra-court terme ≈ cash (ou tu peux mettre 0% vol)
    "USDT": "BIL"
}

def load_current_weights():
    df = pd.read_csv(COMPO_PATH)
    # Nettoyer la pondération (enlever % et convertir en float)
    df["Pondération"] = df["Pondération"].str.replace('%', '').astype(float) / 100
    # Garder seulement la composition la plus récente par portefeuille
    df["Date de mise à jour"] = pd.to_datetime(df["Date de mise à jour"], dayfirst=True)
    latest = df.loc[df.groupby("Portefeuille")["Date de mise à jour"].idxmax()]
    return latest

def get_yf_ticker(actif):
    return TICKER_MAP.get(actif.strip(), actif.strip().upper().replace(" ", ""))

def calculate_vol_and_returns(daily_ret):
    if len(daily_ret) < 2:
        return {k: 0.0 for k in ["daily", "weekly", "monthly", "vol_daily", "vol_weekly", "vol_monthly"]}
    
    vol_daily = daily_ret.std() * np.sqrt(252) * 100
    vol_weekly = daily_ret.rolling(5).std().dropna().mean() * np.sqrt(52) * 100
    vol_monthly = daily_ret.rolling(21).std().dropna().mean() * np.sqrt(12) * 100

    ret_daily = (1 + daily_ret.iloc[-1])
    ret_weekly = (1 + daily_ret[-5:]).prod() if len(daily_ret) >= 5 else 1
    ret_monthly = (1 + daily_ret[-21:]).prod() if len(daily_ret) >= 21 else 1

    return {
        "vol_daily": round(vol_daily, 2),
        "vol_weekly": round(vol_weekly, 2),
        "vol_monthly": round(vol_monthly, 2),
        "ret_daily": round((ret_daily - 1) * 100, 2),
        "ret_weekly": round((ret_weekly - 1) * 100, 2),
        "ret_monthly": round((ret_monthly - 1) * 100, 2),
    }

def calculate_drawdown(nav_series):
    peak = nav_series.cummax()
    dd = (nav_series - peak) / peak
    return round(dd.iloc[-1] * 100, 2), round(dd.min() * 100, 2)

# ==================== DÉBUT DU SCRIPT ====================
print("Chargement des compositions...")
compo = load_current_weights()

# Tous les tickers nécessaires
tickers = [get_yf_ticker(t) for t in compo["Ticker"].unique()]
tickers += list(BENCHMARKS.values())
tickers = list(set(tickers))

print(f"Téléchargement données yfinance pour {len(tickers)} actifs...")
prices = yf.download(tickers, period="max", progress=False)["Adj Close"]

# Pour chaque portefeuille
for portefeuille_name in compo["Portefeuille"].unique():
    print(f"\nTraitement → {portefeuille_name}")
    sub = compo[compo["Portefeuille"] == portefeuille_name].copy()
    
    # Résoudre les tickers
    sub["yf_ticker"] = sub["Actif"].apply(get_yf_ticker)
    valid = sub[sub["yf_ticker"].isin(prices.columns)]
    missing = sub[~sub["yf_ticker"].isin(prices.columns)]["Actif"].tolist()
    if missing:
        print(f"   Attention : actifs non trouvés → {missing}")

    # Période depuis la première date de mise à jour du portefeuille
    start_date = sub["Date de mise à jour"].iloc[0]

    # Retours journaliers du portefeuille
    weights = valid.set_index("yf_ticker")["Pondération"]
    returns = prices[weights.index].pct_change()
    port_returns = (returns * weights).sum(axis=1)
    port_returns = port_returns[port_returns.index >= start_date.strftime("%Y-%m-%d")]

    # NAV (départ à 100)
    nav = (1 + port_returns).cumprod() * 100

    # Benchmarks
    sp_ret = prices[BENCHMARKS["SP500"]].pct_change()[port_returns.index]
    nas_ret = prices[BENCHMARKS["NASDAQ"]].pct_change()[port_returns.index]
    sp_nav = (1 + sp_ret).cumprod() * 100
    nas_nav = (1 + nas_ret).cumprod() * 100

    # Métriques
    port_met = calculate_vol_and_returns(port_returns)
    sp_met = calculate_vol_and_returns(sp_ret)
    nas_met = calculate_vol_and_returns(nas_ret)
    dd_curr, dd_max = calculate_drawdown(nav)

    # Ligne du jour
    today = datetime.now().strftime("%Y-%m-%d")
    row = {
        "Date": today,
        "Portfolio_CumReturn": round(nav.iloc[-1], 2),
        "SP500_CumReturn": round(sp_nav.iloc[-1], 2),
        "NASDAQ_CumReturn": round(nas_nav.iloc[-1], 2),
        "Vol_Daily": port_met["vol_daily"],
        "Vol_Weekly": port_met["vol_weekly"],
        "Vol_Monthly": port_met["vol_monthly"],
        "Drawdown_Current": dd_curr,
        "Drawdown_Max": dd_max,
        "Return_Port_Daily": port_met["ret_daily"],
        "Return_Port_Weekly": port_met["ret_weekly"],
        "Return_Port_Monthly": port_met["ret_monthly"],
        "Return_SP_Daily": sp_met["ret_daily"],
        "Return_SP_Weekly": sp_met["ret_weekly"],
        "Return_SP_Monthly": sp_met["ret_monthly"],
        "Return_NASDAQ_Daily": nas_met["ret_daily"],
        "Return_NASDAQ_Weekly": nas_met["ret_weekly"],
        "Return_NASDAQ_Monthly": nas_met["ret_monthly"],
    }

    # Sauvegarder / mettre à jour le CSV de perf
    filename = f"perf_{portefeuille_name.lower().replace(' ', '_')}.csv"
    # MODE TEST → écrit dans data_test au lieu de data (aucun risque)
    filepath = ROOT / "data_test" / f"TEST_{filename}"
    
    if filepath.exists():
        df = pd.read_csv(filepath)
        if len(df) and df.iloc[-1]["Date"] == today:
            df.iloc[-1] = row
        else:
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df.to_csv(filepath, index=False)
    print(f"   Perf mise à jour → NAV = {row['Portfolio_CumReturn']}")

print("\nToutes les performances sont à jour !")
