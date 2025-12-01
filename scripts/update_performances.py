#!/usr/bin/env python3
# coding: utf-8
"""
Génère automatiquement tous les CSV de performance pour chaque portefeuille
présent dans portfolios.json et composition_portefeuilles.csv.
→ Plus besoin de modifier le script quand tu ajoutes/supprimes un portefeuille !
"""

import os
from pathlib import Path
import json
import pandas as pd
import numpy as np

# Vérification yfinance
try:
    import yfinance as yf
except ImportError:
    raise SystemExit("Installe yfinance : pip install yfinance")

# --- Chemins ---
ROOT = Path(__file__).parent.parent
COMPO_FILE = ROOT / "composition_portefeuilles.csv"
PORTFOLIOS_JSON = ROOT / "portfolios.json"

# --- Paramètres globaux ---
SP500 = "^GSPC"
NASDAQ = "^IXIC"
START_DATE = "2024-01-01"
RISQUE_FREE_ANNUAL = 0.0  # en %
BENCHMARKS = [SP500, NASDAQ]

# Fonction pour générer le nom de fichier propre (même logique que ton site)
def slugify_portfolio_name(name: str) -> str:
    return "portefeuille_" + name.lower().replace(" ", "_").replace("&", "_") + "_v2.csv"

# Chargement de portfolios.json
if not PORTFOLIOS_JSON.exists():
    raise SystemExit(f"Fichier manquant : {PORTFOLIOS_JSON}")

with open(PORTFOLIOS_JSON, "r", encoding="utf-8") as f:
    portfolios_config = json.load(f)

print(f"{len(portfolios_config)} portefeuille(s) trouvé(s) dans portfolios.json")

# Chargement de la composition
if not COMPO_FILE.exists():
    raise SystemExit(f"Fichier manquant : {COMPO_FILE}")

print(f"Chargement de la composition : {COMPO_FILE}")
df = pd.read_csv(COMPO_FILE, sep=None, engine="python", dtype=str)
df["Portefeuille"] = df["Portefeuille"].str.strip()
df["Ticker"] = df["Ticker"].str.strip()
df["Pondération"] = df["Pondération"].str.replace("%", "").str.replace(",", ".").str.strip()
df["Date de mise à jour"] = pd.to_datetime(df["Date de mise à jour"], dayfirst=True, errors="coerce")
df["Pondération"] = pd.to_numeric(df["Pondération"], errors="coerce").fillna(0) / 100.0

# Garder uniquement la version la plus récente par portefeuille
latest_compo = df.loc[df.groupby("Portefeuille")["Date de mise à jour"].idxmax()].copy()
latest_compo = latest_compo.dropna(subset=["Date de mise à jour"])

print(f"{len(latest_compo['Portefeuille'].unique())} portefeuille(s) avec composition à jour")

# Tous les tickers uniques + benchmarks
all_tickers = set(latest_compo["Ticker"].dropna()) | set(BENCHMARKS)
all_tickers.discard("")  # sécurité

print(f"Téléchargement de {len(all_tickers)} actifs depuis {START_DATE}...")
data = yf.download(list(all_tickers), start=START_DATE, progress=False, auto_adjust=True)["Close"]

# Forcer les benchmarks au cas où
for b in BENCHMARKS:
    if b not in data.columns:
        print(f"   → Re-téléchargement forcé du benchmark {b}")
        data[b] = yf.download(b, start=START_DATE, progress=False, auto_adjust=True)["Close"]

rf_daily = RISQUE_FREE_ANNUAL / 100.0 / 252.0

# --- Boucle sur chaque portefeuille du JSON ---
for portfolio in portfolios_config:
    pf_name = portfolio["name"].strip()
    expected_file = portfolio["file"]  # tu gardes le contrôle du nom exact si tu veux

    print(f"\nTraitement → {pf_name}")

    # Récupérer la composition la plus récente pour ce portefeuille
    compo_pf = latest_compo[latest_compo["Portefeuille"] == pf_name]
    if compo_pf.empty:
        print(f"   Aucun actif trouvé pour '{pf_name}' dans composition_portefeuilles.csv → ignoré")
        continue

    # Construction des poids (support multi-tickers par ligne avec ; ou ,)
    weights = {}
    for _, row in compo_pf.iterrows():
        ticker_str = str(row["Ticker"]).strip()
        weight = float(row["Pondération"]) if pd.notna(row["Pondération"]) else 0.0
        tickers = [t.strip() for t in ticker_str.replace(",", ";").split(";") if t.strip()]
        if not tickers:
            continue
        w_per_ticker = weight / len(tickers)
        for t in tickers:
            weights[t] = weights.get(t, 0.0) + w_per_ticker

    if not weights:
        print("   Aucun poids valide → skip")
        continue

    # Filtrer les tickers disponibles
    available_tickers = [t for t in weights if t in data.columns]
    missing = [t for t in weights if t not in data.columns]
    if missing:
        print(f"   Tickers manquants : {missing}")

    if not available_tickers:
        print("   Aucun ticker disponible → skip")
        continue

    # Normalisation des poids
    weights_series = pd.Series({t: weights[t] for t in available_tickers})
    weights_series = weights_series / weights_series.sum()

    # Calcul des rendements du portefeuille
    prices = data[available_tickers].ffill()
    returns = prices.pct_change()
    pf_returns = returns.dot(weights_series).dropna()

    if pf_returns.empty:
        print("   Pas de données de rendement → skip")
        continue

    # Alignement benchmarks
    idx = pf_returns.index
    sp_ret = data[SP500].reindex(idx).pct_change()
    nas_ret = data[NASDAQ].reindex(idx).pct_change()

    # NAV à 100 au départ
    nav = (1 + pf_returns).cumprod() * 100
    sp_nav = (1 + sp_ret).cumprod() * 100
    nas_nav = (1 + nas_ret).cumprod() * 100

    # Drawdown
    dd = nav / nav.cummax() - 1

    # Volatilités annualisées
    vol_252 = pf_returns.rolling(252).std() * np.sqrt(252) * 100
    vol_5d = pf_returns.rolling(5).std() * np.sqrt(252) * 100
    vol_21d = pf_returns.rolling(21).std() * np.sqrt(252) * 100

    # Rendements glissants
    ret_daily = pf_returns * 100
    ret_weekly = (1 + pf_returns).rolling(5).apply(np.prod, raw=True).sub(1) * 100
    ret_monthly = (1 + pf_returns).rolling(21).apply(np.prod, raw=True).sub(1) * 100

    sp_weekly = (1 + sp_ret).rolling(5).apply(np.prod, raw=True).sub(1) * 100
    sp_monthly = (1 + sp_ret).rolling(21).apply(np.prod, raw=True).sub(1) * 100
    nas_weekly = (1 + nas_ret).rolling(5).apply(np.prod, raw=True).sub(1) * 100
    nas_monthly = (1 + nas_ret).rolling(21).apply(np.prod, raw=True).sub(1) * 100

    # Sharpe rolling 21j
    excess = pf_returns - rf_daily
    sharpe_21d = (excess.rolling(21).mean() / pf_returns.rolling(21).std()) * np.sqrt(252)
    sharpe_21d = sharpe_21d.round(3)

    # DataFrame final
    result = pd.DataFrame({
        "Date": idx.strftime("%Y-%m-%d"),
        "Portfolio_CumReturn": nav.round(2),
        "SP500_CumReturn": sp_nav.round(2),
        "NASDAQ_CumReturn": nas_nav.round(2),
        "Vol_Daily": vol_252.round(2),
        "Vol_Weekly": vol_5d.round(2),
        "Vol_Monthly": vol_21d.round(2),
        "Drawdown_Current": (dd * 100).round(2),
        "Drawdown_Max": (dd.cummin() * 100).round(2),
        "Return_Port_Daily": ret_daily.round(2),
        "Return_Port_Weekly": ret_weekly.round(2),
        "Return_Port_Monthly": ret_monthly.round(2),
        "Return_SP_Weekly": sp_weekly.round(2),
        "Return_SP_Monthly": sp_monthly.round(2),
        "Return_NASDAQ_Weekly": nas_weekly.round(2),
        "Return_NASDAQ_Monthly": nas_monthly.round(2),
        "Sharpe_Monthly_Rolling": sharpe_21d,
    }).reset_index(drop=True)

    # Sauvegarde avec le nom EXACT que tu as mis dans portfolios.json
    output_path = ROOT / expected_file
    result.to_csv(output_path, index=False, encoding="utf-8")
    print(f"   Généré : {expected_file} ({len(result):,} jours) | +{(nav.iloc[-1]-100):.1f}% depuis 2022")

print("\nTOUS LES PORTFEUILLES SONT À JOUR !")
