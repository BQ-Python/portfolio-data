# update_script.py – REMPLACE LES 3 DERNIÈRES LIGNES CHAQUE JOUR
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
import os

FILE_NAME = "prices_daily.csv"
TICKERS_FILE = "tickers.csv"
TIMEZONE = "Europe/Paris"
KEEP_LAST_DAYS = 3  # On garde et remplace toujours les 3 derniers jours

def get_current_date():
    return datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d")

def load_tickers():
    if not os.path.exists(TICKERS_FILE):
        raise FileNotFoundError(f"{TICKERS_FILE} introuvable !")
    df = pd.read_csv(TICKERS_FILE)
    if 'ticker' not in df.columns:
        raise ValueError("Colonne 'ticker' manquante dans tickers.csv")
    return df['ticker'].dropna().str.strip().tolist()

def get_last_n_days_data(n=3):
    tickers = load_tickers()
    print(f"Téléchargement des {n} derniers jours de clôture pour {len(tickers)} tickers...")

    data = yf.download(
        tickers=tickers,
        period=f"{n+3}d",      # on prend un peu plus pour être sûr d’avoir n jours valides
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
        ignore_tz=True,
        timeout=30
    )

    if data.empty or "Close" not in data.columns:
        print("Aucune donnée récupérée")
        return None

    close_data = data["Close"].dropna(how='all')  # enlève les lignes vides
    if close_data.empty:
        return None

    # Prend les n dernières lignes disponibles
    last_n = close_data.tail(n).copy()
    last_n = last_n.reset_index()
    last_n['Date'] = last_n['Date'].dt.strftime('%Y-%m-%d')
    last_n = last_n.set_index('Date')

    # Créer un DataFrame avec les colonnes dans le bon ordre (comme avant)
    row_dicts = []
    for date_str in last_n.index:
        row = {"Date": date_str}
        for ticker in tickers:
            price = last_n.loc[date_str, ticker] if ticker in last_n.columns else None
            row[ticker] = round(float(price), 4) if pd.notna(price) else None
        row_dicts.append(row)

    return pd.DataFrame(row_dicts)

def update_csv_file(new_df):
    if new_df is None or new_df.empty:
        print("Aucune donnée à écrire")
        return

    if os.path.exists(FILE_NAME):
        existing_df = pd.read_csv(FILE_NAME)
        # On garde tout sauf les 3 dernières lignes (qu'on va remplacer)
        if len(existing_df) > KEEP_LAST_DAYS:
            base_df = existing_df.iloc[:-KEEP_LAST_DAYS]
            updated_df = pd.concat([base_df, new_df], ignore_index=True)
        else:
            updated_df = new_df  # si moins de 3 lignes, on remplace tout
    else:
        updated_df = new_df

    updated_df.to_csv(FILE_NAME, index=False)
    print(f"prices_daily.csv mis à jour → les {KEEP_LAST_DAYS} dernières lignes ont été remplacées")

# =================== EXÉCUTION ===================
if __name__ == "__main__":
    current_date = get_current_date()
    print(f"=== Mise à jour forcée des {KEEP_LAST_DAYS} derniers jours – {current_date} ===")
    new_data = get_last_n_days_data(n=KEEP_LAST_DAYS)
    update_csv_file(new_data)
