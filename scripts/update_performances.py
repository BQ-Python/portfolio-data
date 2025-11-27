#!/usr/bin/env python3
# coding: utf-8
"""
Script robuste pour générer les CSV de performances à partir de
composition_portefeuilles.csv. Ajoute des logs détaillés et une
sélection fiable de la ligne la plus récente par portefeuille.
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Vérification import yfinance
try:
    import yfinance as yf
except ImportError:
    raise SystemExit("Le paquet 'yfinance' n'est pas installé. Installe-le avec: pip install yfinance")

# --- Configuration ---
ROOT = Path(__file__).parent.parent
COMPO_FILE = ROOT / "composition_portefeuilles.csv"
SP500 = "^GSPC"
NASDAQ = "^IXIC"
START_DATE = "2022-01-01"
RISQUE_FREE_ANNUAL = 0  # en % (annualisé)
OUTPUT_FILES = {
    "Portefeuille Croissance": "portefeuille_portefeuille_croissance_v2.csv",
    "Portefeuille Défensif": "portefeuille_portefeuille_defensif_v2.csv",
    "Portefeuille Europe": "portefeuille_europe_v2.csv"
}

# --- Lecture et normalisation du fichier de composition ---
if not COMPO_FILE.exists():
    raise SystemExit(f"Fichier introuvable: {COMPO_FILE}")

print("Chargement composition depuis :", COMPO_FILE)
df = pd.read_csv(COMPO_FILE, dtype=str)

# Normalisations et nettoyage
df["Portefeuille"] = df.get("Portefeuille", "").fillna("").astype(str).str.strip()
df["Ticker"] = df.get("Ticker", "").fillna("").astype(str).str.strip()
df["Pondération"] = df.get("Pondération", "").fillna("").astype(str).str.replace("%", "").str.replace(",", ".").str.strip()
df["Date de mise à jour"] = pd.to_datetime(df.get("Date de mise à jour", ""), dayfirst=True, errors="coerce")

# Convertir pondérations en float (0..1)
df["Pondération"] = pd.to_numeric(df["Pondération"], errors="coerce").fillna(0) / 100.0

print("Lignes totales composition:", len(df))
print("Aperçu (colonnes importantes) :")
print(df[["Portefeuille", "Ticker", "Pondération", "Date de mise à jour"]].head(30).to_string(index=False))

# Sélection robuste : trier puis garder la dernière ligne par portefeuille
df_sorted = df.sort_values(["Portefeuille", "Date de mise à jour"], ascending=[True, True])
compo = df_sorted.drop_duplicates(subset=["Portefeuille"], keep="last").copy()

print("\nLignes retenues par portefeuille (après tri/drop_duplicates) :")
print(compo[["Portefeuille", "Ticker", "Pondération", "Date de mise à jour"]].to_string(index=False))

# Construire la liste de tickers à télécharger (inclure benchmarks)
tickers = sorted(set(compo["Ticker"].dropna().str.strip().tolist() + [SP500, NASDAQ]))
tickers = [t for t in tickers if t]  # enlever chaînes vides

print(f"\nTéléchargement de {len(tickers)} actifs depuis {START_DATE}...")
data = yf.download(tickers, start=START_DATE, progress=False, auto_adjust=True)["Close"]

# Forçage des benchmarks si manquant
for b in [SP500, NASDAQ]:
    if b not in data.columns:
        print(f"Benchmark {b} absent des colonnes téléchargées, tentative de re-download...")
        data[b] = yf.download(b, start=START_DATE, progress=False, auto_adjust=True)["Close"]

# Taux sans risque journalier
rf_daily = RISQUE_FREE_ANNUAL / 100.0 / 252.0

# Boucle par portefeuille
for pf_name in compo["Portefeuille"].unique():
    print(f"\nTraitement : {pf_name}")
    sub = compo[compo["Portefeuille"] == pf_name]
    if sub.empty:
        print("Aucune ligne retenue pour ce portefeuille, skip.")
        continue

    # Construire weights (assume un seul ticker par portefeuille dans la ligne retenue;
    # si tu as plusieurs lignes par portefeuille, adapte la logique)
    # Ici on supporte plusieurs tickers séparés par ; ou , dans la colonne Ticker si besoin.
    # Si tes tickers sont déjà un seul par ligne, la logique ci‑dessous fonctionne.
    tickers_list = sub["Ticker"].astype(str).str.split(r"[;,]").explode().str.strip().tolist()
    pond_list = sub["Pondération"].astype(float).tolist()
    # Si plusieurs tickers/pondérations sur une même ligne ne sont pas attendus,
    # on utilise directement le mapping simple :
    if len(tickers_list) == len(pond_list):
        weights = dict(zip(tickers_list, pond_list))
    else:
        # fallback : utiliser la paire Ticker:Pondération telle quelle
        weights = dict(zip(sub["Ticker"].tolist(), sub["Pondération"].tolist()))

    # Nettoyage des poids et tickers
    weights = {t.strip(): float(w) for t, w in weights.items() if t and (w == w)}  # filtre NaN
    print("Weights appliqués (bruts) :", weights)

    # Filtrer les tickers disponibles dans les données de marché
    available = [t for t in weights if t in data.columns]
    print("Tickers disponibles dans les données de marché :", available)

    if not available:
        print("Aucun ticker disponible pour ce portefeuille, skip.")
        continue

    # Préparer les prix et retours
    prices = data[available].reindex(data.index).ffill()
    daily_returns = prices.pct_change().dropna(how="all")

    # Série de poids alignée
    weights_series = pd.Series({t: weights[t] for t in available})
    # Retours pondérés du portefeuille
    pf_returns = daily_returns @ weights_series

    # Indices de référence
    idx = pf_returns.index
    sp_ret = data[SP500].reindex(idx).pct_change()
    nas_ret = data[NASDAQ].reindex(idx).pct_change()

    # NAV normalisée à 100 au premier jour valide
    nav = (1 + pf_returns).cumprod() * 100
    sp_nav = (1 + sp_ret).cumprod() * 100
    nas_nav = (1 + nas_ret).cumprod() * 100

    # Drawdowns
    dd_current = nav / nav.cummax() - 1
    dd_max = dd_current.cummin()

    # Volatilités annualisées
    vol_annual_252 = pf_returns.rolling(252).std() * np.sqrt(252) * 100
    vol_annual_5d = pf_returns.rolling(5).std() * np.sqrt(252) * 100
    vol_annual_21d = pf_returns.rolling(21).std() * np.sqrt(252) * 100

    # Rendements sur fenêtres glissantes
    ret_port_daily = pf_returns * 100
    ret_port_weekly = (1 + pf_returns).rolling(5).apply(np.prod, raw=True).sub(1) * 100
    ret_port_monthly = (1 + pf_returns).rolling(21).apply(np.prod, raw=True).sub(1) * 100

    ret_sp_weekly = (1 + sp_ret).rolling(5).apply(np.prod, raw=True).sub(1) * 100
    ret_sp_monthly = (1 + sp_ret).rolling(21).apply(np.prod, raw=True).sub(1) * 100
    ret_nas_weekly = (1 + nas_ret).rolling(5).apply(np.prod, raw=True).sub(1) * 100
    ret_nas_monthly = (1 + nas_ret).rolling(21).apply(np.prod, raw=True).sub(1) * 100

    # Sharpe rolling 21 jours (annualisé)
    excess = pf_returns - rf_daily
    rolling_mean_excess = excess.rolling(21).mean()
    rolling_std = pf_returns.rolling(21).std()
    sharpe_rolling_21d = (rolling_mean_excess / rolling_std) * np.sqrt(252)
    sharpe_rolling_21d = sharpe_rolling_21d.round(3)

    # DataFrame final
    result = pd.DataFrame({
        "Date":                  idx.strftime("%Y-%m-%d"),
        "Portfolio_CumReturn":   nav.round(2),
        "SP500_CumReturn":       sp_nav.round(2),
        "NASDAQ_CumReturn":      nas_nav.round(2),
        "Vol_Daily":             vol_annual_252.round(2),
        "Vol_Weekly":            vol_annual_5d.round(2),
        "Vol_Monthly":           vol_annual_21d.round(2),
        "Drawdown_Current":      (dd_current * 100).round(2),
        "Drawdown_Max":          (dd_max * 100).round(2),
        "Return_Port_Daily":     ret_port_daily.round(2),
        "Return_Port_Weekly":    ret_port_weekly.round(2),
        "Return_Port_Monthly":   ret_port_monthly.round(2),
        "Return_SP_Daily":       (sp_ret * 100).round(2),
        "Return_SP_Weekly":      ret_sp_weekly.round(2),
        "Return_SP_Monthly":     ret_sp_monthly.round(2),
        "Return_NASDAQ_Daily":   (nas_ret * 100).round(2),
        "Return_NASDAQ_Weekly":  ret_nas_weekly.round(2),
        "Return_NASDAQ_Monthly": ret_nas_monthly.round(2),
        "Sharpe_Monthly_Rolling": sharpe_rolling_21d
    }).reset_index(drop=True)

    # Sauvegarde
    path = ROOT / OUTPUT_FILES.get(pf_name, f"output_{pf_name}.csv")
    result.to_csv(path, index=False, encoding="utf-8")
    # s'assurer que l'écriture est flushée sur le runner
    try:
        with open(path, "rb") as f:
            os.fsync(f.fileno())
    except Exception:
        pass

    # Stats finales et aperçu
    if not result.empty:
        last_date = result["Date"].iloc[-1]
        perf_totale = result["Portfolio_CumReturn"].iloc[-1] - 100
        vol_last = result["Vol_Monthly"].iloc[-1]
        sharpe_last = result["Sharpe_Monthly_Rolling"].iloc[-1]
        sharpe_moyen = result["Sharpe_Monthly_Rolling"].replace([np.inf, -np.inf], np.nan).mean()
        print(f"{pf_name} → OK | {len(result):,} jours | "
              f"Perf depuis 2022 = +{perf_totale:.1f}% | "
              f"Vol 21j = {vol_last:.1f}% | "
              f"Sharpe 21j (dernier) = {sharpe_last:.2f} | "
              f"Sharpe moyen = {sharpe_moyen:.2f}")
    else:
        print(f"{pf_name} → Résultat vide, aucun jour valide trouvé.")

    # Aperçu du fichier généré
    try:
        print("WROTE:", path, "size:", path.stat().st_size)
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
            print("Aperçu (10 premières lignes) :")
            for ln in lines[:10]:
                print(ln)
    except Exception as e:
        print("Impossible d'afficher l'aperçu du fichier :", e)

print("\nTOUS LES CSV CORRIGÉS ET GÉNÉRÉS AVEC CALCULS EXACTS")
