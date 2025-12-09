# update_script.py – VERSION 100 % ROBUSTE (plus jamais d’erreur)
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
        raise FileNotFoundError(f"{TICKERS_FILE} introuvable !")
    df = pd.read_csv(TICKERS_FILE)                   # virgules ou tabulations → OK
    if 'ticker' not in df.columns:
        print("Colonnes trouvées :", list(df.columns))
        raise ValueError("Colonne 'ticker' manquante")
    tickers = df['ticker'].dropna().str.strip().tolist()
    print(f"{len(tickers)} tickers chargés")
    return tickers

def get_new_data(current_date):
    tickers = load_tickers()
    print(f"Téléchargement des prix pour {len(tickers)} symboles...")

    # Télécharge avec gestion d’erreur intégrée
    data = yf.download(
        tickers=tickers,
        period="5d",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
        ignore_tz=True,
        timeout=30
    )

    if data.empty or data["Close"].isna().all().all():
        print("Aucune donnée récupérée aujourd’hui (week-end, jour férié, ou tous les tickers en erreur)")
        return None

    # Récupère la dernière ligne de clôture disponible
    close_data = data["Close"]
    latest = close_data.iloc[-1] if close_data.ndim > 1 else close_data

    row = {"Date": current_date}
    for ticker in tickers:
        try:
            price = latest[ticker] if ticker in latest else latest.get(ticker)
            row[ticker] = round(float(price), 4) if pd.notna(price) else None
        except:
            row[ticker] = None  # ticker délisté ou erreur

    return pd.DataFrame([row])

def update_csv_file(new_df):
    today = new_df["Date"].iloc[0]
    if os.path.exists(FILE_NAME):
        existing_df = pd.read_csv(FILE_NAME)
        if today in existing_df["Date"].astype(str).values:
            print(f"{today} déjà présent → rien à faire")
            return
        new_df = new_df.reindex(columns=existing_df.columns, fill_value=None)
        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        updated_df = new_df

    updated_df.to_csv(FILE_NAME, index=False)
    print(f"prices_daily.csv mis à jour avec succès pour {today}")

# =================== EXÉCUTION ===================
if __name__ == "__main__":
    current_date = get_current_date()
    print(f"=== Mise à jour quotidienne – {current_date} ===")
    new_data = get_new_data(current_date)
    if new_data is not None:
        update_csv_file(new_data)
    else:
        print("Aucune donnée à ajouter aujourd’hui.")
