#!/usr/bin/env python3
import pandas as pd
import yfinance as yf
import numpy as np
from pathlib import Path

# Tout est à la racine du repo (comme dans ton main)
ROOT = Path(__file__).parent.parent
COMPO_FILE = ROOT / "composition_portefeuilles.csv"  # à la racine
SP500 = "^GSPC"
NASDAQ = "^IXIC"
START_DATE = "2022-01-01"

# Tes vrais fichiers finaux (ne pas toucher leurs noms ni emplacement)
OUTPUT_FILES = {
    "Portefeuille Croissance": "portefeuille_portefeuille_croissance_v2.csv",
    "Portefeuille Défensif": "portefeuille_portefeuille_defensif_v2.csv",
    "Portefeuille Europe": "portefeuille_europe_v2.csv"
}

print("Chargement de composition_portefeuilles.csv (racine)...")
df = pd.read_csv(COMPO_FILE)
df["Pondération"] = df["Pondération"].str.replace("%", "").astype(float) / 100
df["Date de mise à jour"] = pd.to_datetime(df["Date de mise à jour"], dayfirst=True)
compo = df.loc[df.groupby("Portefeuille")["Date de mise à jour"].idxmax()].copy()

# Tous les tickers
tickers = compo["Ticker"].dropna().str.strip().unique().tolist() + [SP500, NASDAQ]
tickers = sorted(set(tickers))

print(f"Téléchargement de {len(tickers)} tickers depuis {START_DATE}...")
data = yf.download(tickers, start=START_DATE, progress=False, auto_adjust=True, threads=True)
prices = data["Close"]

# Forcer les benchmarks
for b in [SP500, NASDAQ]:
    if b not in prices.columns:
        prices[b] = yf.download(b, start=START_DATE, progress=False, auto_adjust=True)["Close"]

for pf_name in compo["Portefeuille"].unique():
    sub = compo[compo["Portefeuille"] == pf_name]
    weights = dict(zip(sub["Ticker"], sub["Pondération"]))

    available = [t for t in weights if t in prices.columns]
    if not available:
        print(f"{pf_name} → aucun ticker trouvé")
        continue

    returns = prices[available].pct_change()
    pf_returns = (returns * pd.Series(weights)[available]).sum(axis=1).dropna()

    if len(pf_returns) < 300:
        print(f"{pf_name} → pas assez de données")
        continue

    # NAVs bruts
    nav_raw = (1 + pf_returns).cumprod()
    sp_nav_raw = (1 + prices[SP500].pct_change().loc[pf_returns.index]).cumprod()
    nas_nav_raw = (1 + prices[NASDAQ].pct_change().loc[pf_returns.index]).cumprod()

    # On force tout à 100 au premier jour où Vol_Daily est calculable
    first_valid = pf_returns.rolling(252).std().first_valid_index()
    if first_valid is None:
        first_valid = pf_returns.index[251]

    base_nav = nav_raw.loc[first_valid]
    base_sp = sp_nav_raw.loc[first_valid]
    base_nas = nas_nav_raw.loc[first_valid]

    nav = (nav_raw / base_nav) * 100
    sp_nav = (sp_nav_raw / base_sp) * 100
    nas_nav = (nas_nav_raw / base_nas) * 100

    dd_series = nav / nav.cummax() - 1
    dd_max_series = dd_series.cummin()

    # Volatilités
    vol_daily = pf_returns.rolling(252).std() * np.sqrt(252) * 100
    vol_weekly = pf_returns.rolling(5).std() * np.sqrt(52) * 100
    vol_monthly = pf_returns.rolling(21).std() * np.sqrt(12) * 100

    # Returns
    sp_ret = prices[SP500].pct_change().loc[pf_returns.index]
    nas_ret = prices[NASDAQ].pct_change().loc[pf_returns.index]

    result = pd.DataFrame({
        "Date":                   pf_returns.index.strftime("%Y-%m-%d"),
        "Portfolio_CumReturn":    nav.round(2),
        "SP500_CumReturn":        sp_nav.round(2),
        "NASDAQ_CumReturn":       nas_nav.round(2),
        "Vol_Daily":              vol_daily.round(2),
        "Vol_Weekly":             vol_weekly.round(2),
        "Vol_Monthly":            vol_monthly.round(2),
        "Drawdown_Current":       (dd_series * 100).round(2),
        "Drawdown_Max":           (dd_max_series * 100).round(2),
        "Return_Port_Daily":      (pf_returns * 100).round(2),
        "Return_Port_Weekly":     pf_returns.rolling(5).apply(lambda x: (1+x).prod()-1).round(2) * 100,
        "Return_Port_Monthly":    pf_returns.rolling(21).apply(lambda x: (1+x).prod()-1).round(2) * 100,
        "Return_SP_Daily":        (sp_ret * 100).round(2),
        "Return_SP_Weekly":       sp_ret.rolling(5).apply(lambda x: (1+x).prod()-1).round(2) * 100,
        "Return_SP_Monthly":      sp_ret.rolling(21).apply(lambda x: (1+x).prod()-1).round(2) * 100,
        "Return_NASDAQ_Daily":    (nas_ret * 100).round(2),
        "Return_NASDAQ_Weekly":   nas_ret.rolling(5).apply(lambda x: (1+x).prod()-1).round(2) * 100,
        "Return_NASDAQ_Monthly":  nas_ret.rolling(21).apply(lambda x: (1+x).prod()-1).round(2) * 100,
    })

    result = result.dropna(subset=["Vol_Daily"]).reset_index(drop=True)
    result.loc[0, ["Portfolio_CumReturn", "SP500_CumReturn", "NASDAQ_CumReturn"]] = 100.0

    filename = OUTPUT_FILES[pf_name]
    path = ROOT / filename
    result.to_csv(path, index=False)

    print(f"{pf_name} → mis à jour : {filename} ({len(result)} jours, NAV final = {result['Portfolio_CumReturn'].iloc[-1]})")

print("\nTOUS TES FICHIERS V2 SONT À JOUR À LA RACINE !")
