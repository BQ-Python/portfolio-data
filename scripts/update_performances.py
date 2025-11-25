#!/usr/bin/env python3
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
from pathlib import Path

# ==================== CHEMINS ====================
ROOT = Path(__file__).parent.parent
COMPO_PATH = ROOT / "data" / "composition_portefeuilles.csv"   # ← ton vrai nom de fichier (sans "s")
TEST_DIR = ROOT / "data_test"                                  # ← sortie en mode test (sans risque)

# ==================== MAPPING ACTIFS SPÉCIAUX ====================
TICKER_MAP = {
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "Or physique": "GC=F",       # Gold futures
    "GOLD": "GC=F",
    "Cash & stablecoins": "BIL", # ETF ultra-court terme ≈ cash
    "USDT": "BIL",
}

# ==================== BENCHMARKS ====================
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

# ==================== CALCULS MÉTRIQUES ====================
def calculate_metrics(daily_ret):
    if len(daily_ret) < 2:
        return {k: 0.0 for k in ["vol_daily", "vol_weekly", "vol_monthly", "ret_daily", "ret_weekly", "ret_monthly"]}
    vol_daily = daily_ret.std() * np.sqrt(252) * 100
    vol_weekly = daily_ret.rolling(5).std().dropna().mean() * np.sqrt(52) * 100
    vol_monthly = daily_ret.rolling(21).std().dropna().mean() * np.sqrt(12) * 100
    ret_daily = (1 + daily_ret.iloc[-1]) - 1
    ret_weekly = (1 + daily_ret[-5:]).prod() - 1 if len(daily_ret) >= 5 else 0
    ret_monthly = (1 + daily_ret[-21:]).prod() - 1 if len(daily_ret) >= 21 else 0
    return {
        "vol_daily": round(vol_daily, 2),
        "vol_weekly": round(vol_weekly, 2),
        "vol_monthly": round(vol_monthly, 2),
        "ret_daily": round(ret_daily * 100, 2),
        "ret_weekly": round(ret_weekly * 100, 2),
        "ret_monthly": round(ret_monthly * 100, 2),
    }

def calculate_drawdown(nav_series):
    peak = nav_series.cummax()
    dd = (nav_series - peak) / peak
    return round(dd.iloc[-1] * 100, 2), round(dd.min() * 100, 2)

# ==================== DÉBUT DU SCRIPT ====================
print("Chargement des compositions...")
compo = load_current_weights()

# Tous les tickers à télécharger
tickers = [get_yf_ticker(t) for t in compo["Ticker"]]
tickers += list(BENCHMARKS.values())
tickers = list(set(tickers))

print(f"Téléchargement données yfinance pour {len(tickers)} actifs...")
prices = yf.download(tickers, period="max", progress=False, threads=True)["Adj Close"]

# Forcer les benchmarks même s’ils n’ont pas été téléchargés
for name, ticker in BENCHMARKS.items():
    if ticker not in prices.columns or prices[ticker].isna().all():
        print(f"   → Téléchargement forcé du benchmark {name} ({ticker})")
        bench = yf.download(ticker, period="max", progress=False)["Adj Close"]
        prices[ticker] = bench

# Créer le dossier de test
TEST_DIR.mkdir(exist_ok=True)

# Pour chaque portefeuille
for portefeuille_name in compo["Portefeuille"].unique():
    print(f"\nTraitement → {portefeuille_name}")
    sub = compo[compo["Portefeuille"] == portefeuille_name].copy()
    sub["yf_ticker"] = sub["Actif"].apply(get_yf_ticker)

    # Vérifier les tickers manquants
    missing = sub[~sub["yf_ticker"].isin(prices.columns)]["Actif"].tolist()
    if missing:
        print(f"   Attention : actifs non trouvés → {missing}")

    valid = sub[sub["yf_ticker"].isin(prices.columns)]
    weights = valid.set_index("yf_ticker")["Pondération"]

    # Retours du portefeuille
    returns = prices[weights.index].pct_change()
    port_returns = (returns * weights).sum(axis=1)
    start_date = sub["Date de mise à jour"].min()
    port_returns = port_returns[port_returns.index >= start_date.strftime("%Y-%m-%d")]

    if port_returns.empty:
        print("   Aucun retour → portefeuille ignoré pour aujourd’hui")
        continue

    # NAV à 100 au départ
    nav = (1 + port_returns).cumprod() * 100

    # Benchmarks
    sp_ret = prices[BENCHMARKS["SP500"]].pct_change()[port_returns.index]
    nas_ret = prices[BENCHMARKS["NASDAQ"]].pct_change()[port_returns.index]
    sp_nav = (1 + sp_ret).cumprod() * 100
    nas_nav = (1 + nas_ret).cumprod() * 100

    # Métriques
    port_met = calculate_metrics(port_returns)
    sp_met = calculate_metrics(sp_ret)
    nas_met = calculate_metrics(nas_ret)
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

    # Nom du fichier de test
    filename = f"TEST_perf_{portefeuille_name.lower().replace(' ', '_').replace('é', 'e')}.csv"
    filepath = TEST_DIR / filename

    # Sauvegarde
    df_new = pd.DataFrame([row])
    if filepath.exists():
        df = pd.read_csv(filepath)
        if len(df) and df.iloc[-1]["Date"] == today:
            df.iloc[-1] = row
        else:
            df = pd.concat([df, df_new], ignore_index=True)
    else:
        df = df_new
    df.to_csv(filepath, index=False)
    print(f"   Fichier créé → {filepath.name} (NAV = {row['Portfolio_CumReturn']})")

print("\nToutes les performances sont à jour ! (mode test)")
