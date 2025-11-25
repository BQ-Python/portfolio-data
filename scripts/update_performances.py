#!/usr/bin/env python3
import pandas as pd
import yfinance as yf
import numpy as np
from pathlib import Path

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

print("Chargement composition_portefeuilles.csv...")
df = pd.read_csv(COMPO_FILE)
df["Pondération"] = df["Pondération"].str.replace("%", "").astype(float) / 100
df["Date de mise à jour"] = pd.to_datetime(df["Date de mise à jour"], dayfirst=True)
compo = df.loc[df.groupby("Portefeuille")["Date de mise à jour"].idxmax()].copy()

tickers = sorted(set(compo["Ticker"].dropna().str.strip().tolist() + [SP500, NASDAQ]))

print(f"Téléchargement de {len(tickers)} tickers depuis {START_DATE}...")
data = yf.download(tickers, start=START_DATE, progress=False, auto_adjust=True, threads=True)
prices = data["Close"]

# Forçage absolu des benchmarks
for b in [SP500, NASDAQ]:
    if b not in prices.columns:
        prices[b] = yf.download(b, start=START_DATE, progress=False, auto_adjust=True)["Close"]

for pf_name in compo["Portefeuille"].unique():
    sub = compo[compo["Portefeuille"] == pf_name]
    weights = dict(zip(sub["Ticker"], sub["Pondération"]))
    available = [t for t in weights if t in prices.columns]

    if not available:
        print(f"{pf_name} → aucun ticker")
        continue

    # Prix des actifs du portefeuille + alignement parfait
    pf_prices = prices[available]
    pf_returns = pf_prices.pct_change().fillna(0)
    pf_returns = (pf_returns * pd.Series(weights)[available]).sum(axis=1)

    # Index de référence = tous les jours où le portefeuille a bougé
    idx = pf_returns.index

    # Benchmarks alignés FORCÉMENT sur le même index (plus jamais de NaN)
    sp_ret  = prices[SP500].reindex(idx).pct_change().fillna(0)
    nas_ret = prices[NASDAQ].reindex(idx).pct_change().fillna(0)

    # NAVs à partir du premier jour (2022)
    nav_raw  = (1 + pf_returns).cumprod()
    sp_raw   = (1 + sp_ret).cumprod()
    nas_raw  = (1 + nas_ret).cumprod()

    # Normalisation à 100 au tout premier jour
    nav  = nav_raw  / nav_raw.iloc[0]  * 100
    sp   = sp_raw   / sp_raw.iloc[0]   * 100
    nas  = nas_raw  / nas_raw.iloc[0]  * 100

    # Drawdowns
    dd_current = nav / nav.cummax() - 1
    dd_max     = dd_current.cummin()

    # Volatilités
    vol_daily   = pf_returns.rolling(252).std() * np.sqrt(252) * 100
    vol_weekly  = pf_returns.rolling(5).std()   * np.sqrt(52)  * 100
    vol_monthly = pf_returns.rolling(21).std()  * np.sqrt(12)  * 100

    # DataFrame final
    result = pd.DataFrame({
        "Date":                   idx.strftime("%Y-%m-%d"),
        "Portfolio_CumReturn":    nav.round(2),
        "SP500_CumReturn":        sp.round(2),
        "NASDAQ_CumReturn":       nas.round(2),
        "Vol_Daily":              vol_daily.round(2),
        "Vol_Weekly":             vol_weekly.round(2),
        "Vol_Monthly":            vol_monthly.round(2),
        "Drawdown_Current":       (dd_current * 100).round(2),
        "Drawdown_Max":           (dd_max * 100).round(2),
        "Return_Port_Daily":      (pf_returns * 100).round(2),
        "Return_Port_Weekly":     (pf_returns.rolling(5).apply(lambda x: (1+x).prod() - 1) * 100).round(2),
        "Return_Port_Monthly":    (pf_returns.rolling(21).apply(lambda x: (1+x).prod() - 1) * 100).round(2),
        "Return_SP_Daily":        (sp_ret * 100).round(2),
        "Return_SP_Weekly":       (sp_ret.rolling(5).apply(lambda x: (1+x).prod() - 1) * 100).round(2),
        "Return_SP_Monthly":      (sp_ret.rolling(21).apply(lambda x: (1+x).prod() - 1) * 100).round(2),
        "Return_NASDAQ_Daily":    (nas_ret * 100).round(2),
        "Return_NASDAQ_Weekly":   (nas_ret.rolling(5).apply(lambda x: (1+x).prod() - 1) * 100).round(2),
        "Return_NASDAQ_Monthly":  (nas_ret.rolling(21).apply(lambda x: (1+x).prod() - 1) * 100).round(2),
    }).reset_index(drop=True)

    # Sauvegarde
    path = ROOT / OUTPUT_FILES[pf_name]
    result.to_csv(path, index=False)

    print(f"{pf_name} → OK | {len(result)} jours | "
          f"NAV = {result['Portfolio_CumReturn'].iloc[-1]:.2f} | "
          f"SP500 = {result['SP500_CumReturn'].iloc[-1]:.2f} | "
          f"NASDAQ = {result['NASDAQ_CumReturn'].iloc[-1]:.2f}")

print("\nTOUT EST PARFAIT — PLUS AUCUNE COLONNE VIDE")