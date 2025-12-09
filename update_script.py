# update_script.py – VERSION FINALE (fonctionne avec virgules OU tabulations)
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
import os

FILE_NAME = "prices_daily.csv"
TICKERS_FILE = "tickers.csv"
TIMEZONE = "Europe/Paris"

def get_current_date():
    return datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d")

def load_tickers():
    if not os.path.exists(TICKERS_FILE):
        raise FileNotFoundError(f"Fichier {TICKERS_FILE} introuvable !")

    # pandas détecte tout seul si c’est des virgules ou des tabulations
    df = pd.read_csv(TICKERS_FILE)

    if 'ticker' not in df.columns:
        print("Colonnes détectées :", list(df.columns))
        raise ValueError("Colonne 'ticker' absente ou mal orthographiée dans tickers.csv")

    tickers = df['ticker'].dropna().str.strip().tolist()
    print(f"{len(tickers)} tickers chargés avec succès")
    return tickers

def get_new_data(current_date):
    tickers = load_tickers()
    print(f"Téléchargement des prix pour {len(tickers)} symboles...")

    data = yf.download(
        tickers=tickers,
        period="5d",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
        group_by='ticker'
    )

    if data.empty:
        print("Aucune donnée récupérée aujourd’hui (week-end ou jour férié ?)")
        return None

    # Gestion d’un seul ticker vs plusieurs
    if len(tickers) == 1:
        latest = data["Close"]
    else:
        latest = data["Close"].iloc[-1]

    row = {"Date": current_date}
    for ticker in tickers:
        price = latest[ticker] if ticker in latest else None
        row[ticker] = round(float(price), 4) if price is not None and pd.notna(price) else None

    return pd.DataFrame([row])

def update_csv_file(new_df):
    today = new_df["Date"].iloc[0]

    if os.path.exists(FILE_NAME):
        existing_df = pd.read_csv(FILE_NAME)
        if today in existing_df["Date"].astype(str).values:
            print(f"La date {today} existe déjà → rien à faire.")
            return
        new_df = new_df.reindex(columns=existing_df.columns, fill_value=None)
        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        updated_df = new_df

    updated_df.to_csv(FILE_NAME, index=False)
    print(f"prices_daily.csv mis à jour avec succès pour {today}")

if __name__ == "__main__":
    current_date = get_current_date()
    print(f"Lancement de la mise à jour – {current_date}")
    new_data = get_new_data(current_date)
    if new_data is not None and not new_data.empty:
        update_csv_file(new_data)
    else:
        print("Aucune donnée à ajouter aujourd’hui.")
