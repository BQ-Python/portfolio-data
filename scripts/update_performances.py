#!/usr/bin/env python3
import pandas as pd
import yfinance as yf
import numpy as np
from pathlib import Path

# Configuration
ROOT = Path(__file__).parent.parent
COMPO_FILE = ROOT / "composition_portefeuilles.csv"
SP500 = "^GSPC"
NASDAQ = "^IXIC"
START_DATE = "2022-01-01"

OUTPUT_FILES = {
    "Portefeuille Croissance": "portefeuille_portefeuille_croissance_v2.csv",
    "Portefeuille Défensif": "portefeuille_portefeuille_defensif_v2.csv",
    "Portefeuille Europe": "portefeuille_europe_v2.csv"
}

print("Chargement de composition_portefeuilles.csv...")
df = pd.read_csv(COMPO_FILE)
df["Pondération"] = df["Pondération"].str.replace("%", "").astype(float) / 100
df["Date de mise à jour"] = pd.to_datetime(df["Date de mise à jour"], dayfirst=True)

# On prend la composition la plus récente par portefeuille
compo = df.loc[df.groupby("Portefeuille")["Date de mise à jour"].idxmax()].copy()

# Tous les tickers uniques + benchmarks
tickers = compo["Ticker"].dropna().str.strip().unique().tolist() + [SP500, NASDAQ]
tickers = sorted(set(tickers))

print(f"Téléchargement de {len(tickers)} tickers depuis {START_DATE}...")
data = yf.download(tickers, start=START_DATE, progress=False, auto_adjust=True, threads=True)
prices = data["Close"]

# Forcer les benchmarks au cas où
for b in [SP500, NASDAQ]:
    if b not in prices.columns:
        prices[b] = yf.download(b, start=START_DATE, progress=False, auto_adjust=True)["Close"]

for pf_name in compo["Portefeuille"].unique():
    sub = compo[compo["Portefeuille"] == pf_name]
    weights = dict(zip(sub["Ticker"], sub["Pondération"]))

    available = [t for t in weights if t in prices.columns]
    if not available:
        print(f"{pf_name} → aucun ticker disponible")
        continue

    returns = prices[available].pct_change()
    pf_returns = (returns * pd.Series(weights)[available]).sum(axis=1)

    if len(pf_returns) < 300:
        print(f"{pf_name} → pas assez de données")
        continue

    # NAV brutes (débutent au premier jour de données)
    nav_raw = (1 + pf_returns).cumprod()
    sp_nav_raw = (1 + prices[SP500].pct_change()).loc[pf_returns.index].cumprod()
    nas_nav_raw = (1 + prices[NASDAQ].pct_change()).loc[pf_returns.index].cumprod()

    # On normalise tout à 100 au premier jour où la vol annualisée existe (252 jours de trading)
    first_valid_vol = pf_returns.rolling(252).std().first_valid_index()
    if first_valid_vol is None:
        first_valid_vol = pf_returns.index[251]  # fallback

    nav = nav_raw / nav_raw.loc[first_valid_vol] * 100
    sp_nav = sp_nav_raw / sp_nav_raw.loc[first_valid_vol] * 100
    nas_nav = nas_nav_raw / nas_nav_raw.loc[first_valid_vol] * 100

    # Drawdowns
    dd_series = nav / nav.cummax() - 1
    dd_max_series = dd_series.cummin()

    # Volatilités annualisées
    vol_daily = pf_returns.rolling(252).std() * np.sqrt(252) * 100
    vol_weekly = pf_returns.rolling(5).std() * np.sqrt(52) * 100
    vol_monthly = pf_returns.rolling(21).std() * np.sqrt(12) * 100

    # Returns benchmarks
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
        "Return_Port_Weekly":     (pf_returns.rolling(5).apply(lambda x: (1+x).prod() - 1) * 100).round(2),
        "Return_Port_Monthly":    (pf_returns.rolling(21).apply(lambda x: (1+x).prod() - 1) * 100).round(2),
        "Return_SP_Daily":        (sp_ret * 100).round(2),
        "Return_SP_Weekly":       (sp_ret.rolling(5).apply(lambda x: (1+x).prod() - 1) * 100).round(2),
        "Return_SP_Monthly":      (sp_ret.rolling(21).apply(lambda x: (1+x).prod() - 1) * 100).round(2),
        "Return_NASDAQ_Daily":    (nas_ret * 100).round(2),
        "Return_NASDAQ_Weekly":   (nas_ret.rolling(5).apply(lambda x: (1+x).prod() - 1) * 100).round(2),
        "Return_NASDAQ_Monthly":  (nas_ret.rolling(21).apply(lambda x: (1+x).prod() - 1) * 100).round(2),
    })

    # On garde uniquement les lignes où Vol_Daily existe → c’est notre vrai point de départ
    result = result.dropna(subset=["Vol_Daily"]).reset_index(drop=True)

    # Plus besoin de forcer à 100 : c’est déjà naturellement 100.00 sur la première ligne
    # (on peut même vérifier : print(result.iloc[0][["Portfolio_CumReturn", "SP500_CumReturn", "NASDAQ_CumReturn"]]))

    filename = OUTPUT_FILES[pf_name]
    path = ROOT / filename
    result.to_csv(path, index=False)

    start_date_str = result["Date"].iloc[0]
    final_nav = result["Portfolio_CumReturn"].iloc[-1]
    print(f"{pf_name} → OK | Début vol: {start_date_str} | NAV final: {final_nav:.2f} → {filename}")

print("\nTOUS LES FICHIERS V2 SONT À JOUR CORRECTEMENT !")
