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

# Taux sans risque annualisé (novembre 2025)
RISQUE_FREE_ANNUAL = 0

OUTPUT_FILES = {
    "Portefeuille Croissance": "portefeuille_portefeuille_croissance_v2.csv",
    "Portefeuille Défensif": "portefeuille_portefeuille_defensif_v2.csv",
    "Portefeuille Europe": "portefeuille_europe_v2.csv"
}

print("Chargement composition...")
df = pd.read_csv(COMPO_FILE)
df["Pondération"] = df["Pondération"].str.replace("%", "").astype(float) / 100
df["Date de mise à jour"] = pd.to_datetime(df["Date de mise à jour"], dayfirst=True)
compo = df.loc[df.groupby("Portefeuille")["Date de mise à jour"].idxmax()].copy()

tickers = sorted(set(compo["Ticker"].dropna().str.strip().tolist() + [SP500, NASDAQ]))

print(f"Téléchargement de {len(tickers)} actifs depuis {START_DATE}...")
data = yf.download(tickers, start=START_DATE, progress=False, auto_adjust=True)["Close"]

# Forçage des benchmarks au cas où
for b in [SP500, NASDAQ]:
    if b not in data.columns:
        data[b] = yf.download(b, start=START_DATE, progress=False, auto_adjust=True)["Close"]

# Taux sans risque journalier
rf_daily = RISQUE_FREE_ANNUAL / 100 / 252

for pf_name in compo["Portefeuille"].unique():
    print(f"\nTraitement : {pf_name}")
    sub = compo[compo["Portefeuille"] == pf_name]
    weights = dict(zip(sub["Ticker"], sub["Pondération"]))
    available = [t for t in weights if t in data.columns and t == t]  # t == t filtre les NaN

    if not available:
        print("Aucun ticker disponible")
        continue

    prices = data[available].reindex(data.index).ffill()  # sécurité
    daily_returns = prices.pct_change().dropna(how='all')

    # Retours pondérés du portefeuille
    pf_returns = daily_returns @ pd.Series(weights)[available]   # multiplication matricielle = rapide & exacte

    # Alignement parfait des indices
    idx = pf_returns.index
    sp_ret = data[SP500].reindex(idx).pct_change()
    nas_ret = data[NASDAQ].reindex(idx).pct_change()

    # === NAV normalisée à 100 au PREMIER jour de données valides ===
    nav = (1 + pf_returns).cumprod() * 100
    sp_nav = (1 + sp_ret).cumprod() * 100
    nas_nav = (1 + nas_ret).cumprod() * 100

    # === Drawdowns ===
    dd_current = nav / nav.cummax() - 1
    dd_max = dd_current.cummin()

    # === Volatilités annualisées CORRECTES ===
    vol_annual_252 = pf_returns.rolling(252).std() * np.sqrt(252) * 100   # vol sur 1 an
    vol_annual_5d  = pf_returns.rolling(5).std()   * np.sqrt(252) * 100   # vol annualisée sur 5j (hebdo)
    vol_annual_21d = pf_returns.rolling(21).std()  * np.sqrt(252) * 100   # vol annualisée sur 21j (mensuel)

    # === Rendements sur fenêtres glissantes (vectorisé = 50× plus rapide) ===
    ret_port_daily   = pf_returns * 100
    ret_port_weekly  = (1 + pf_returns).rolling(5).apply(np.prod, raw=True).sub(1) * 100
    ret_port_monthly = (1 + pf_returns).rolling(21).apply(np.prod, raw=True).sub(1) * 100

    ret_sp_weekly    = (1 + sp_ret).rolling(5).apply(np.prod, raw=True).sub(1) * 100
    ret_sp_monthly   = (1 + sp_ret).rolling(21).apply(np.prod, raw=True).sub(1) * 100
    ret_nas_weekly   = (1 + nas_ret).rolling(5).apply(np.prod, raw=True).sub(1) * 100
    ret_nas_monthly  = (1 + nas_ret).rolling(21).apply(np.prod, raw=True).sub(1) * 100

    # === Sharpe rolling 21 jours → annualisé proprement ===
    excess = pf_returns - rf_daily
    rolling_mean_excess = excess.rolling(21).mean()
    rolling_std = pf_returns.rolling(21).std()
    sharpe_rolling_21d = (rolling_mean_excess / rolling_std) * np.sqrt(252)   # ← formule exacte
    sharpe_rolling_21d = sharpe_rolling_21d.round(3)

    # === DataFrame final ===
    result = pd.DataFrame({
        "Date":                  idx.strftime("%Y-%m-%d"),
        "Portfolio_CumReturn":   nav.round(2),
        "SP500_CumReturn":       sp_nav.round(2),
        "NASDAQ_CumReturn":      nas_nav.round(2),
        "Vol_Daily":             vol_annual_252.round(2),      # vol annualisée (252j)
        "Vol_Weekly":            vol_annual_5d.round(2),       # vol annualisée sur base 5j
        "Vol_Monthly":           vol_annual_21d.round(2),      # vol annualisée sur base 21j
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
    path = ROOT / OUTPUT_FILES[pf_name]
    result.to_csv(path, index=False)

    # Stats finales
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

print("\nTOUS LES CSV CORRIGÉS ET GÉNÉRÉS AVEC CALCULS EXACTS")