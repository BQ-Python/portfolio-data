# update_script.py
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
import os

FILE_NAME = "prices_daily.csv"
TICKERS_FILE = "tickers.csv"
TIMEZONE = "Europe/Paris"

def get_current_date():
    """Date du jour en heure de Paris (format YYYY-MM-DD)"""
    return datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d")


def load_tickers():
    """Charge uniquement la colonne 'ticker' depuis ton tickers.csv"""
    if not os.path.exists(TICKERS_FILE):
        raise FileNotFoundError(f"Fichier {TICKERS_FILE} introuvable !")
    
    df = pd.read_csv(TICKERS_FILE, sep="\t")  # ton fichier est tabulé
    if "ticker" not in df.columns:
        raise ValueError("La colonne 'ticker' est absente dans tickers.csv")
    
    tickers = df["ticker"].dropna().tolist()
    print(f"{len(tickers)} tickers chargés depuis tickers.csv")
    return tickers


def get_new_data(current_date):
    """Récupère les prix de clôture du dernier jour de marché disponible"""
    tickers = load_tickers()

    print(f"Téléchargement des données pour {len(tickers)} symboles...")
    
    # On prend 5 jours pour être sûr d’avoir le dernier jour de marché fermé
    data = yf.download(
        tickers=tickers,
        period="5d",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,         # plus rapide quand tu as beaucoup de tickers
        group_by="ticker"
    )

    if data.empty:
        print("Aucune donnée récupérée via yfinance")
        return None

    # yfinance retourne soit un DataFrame simple, soit un multi-index selon le nombre de tickers
    if len(tickers) == 1:
        latest_prices = data["Close"].iloc[-1] if "Close" in data.columns else data.iloc[-1]
    else:
        latest_prices = data["Close"].iloc[-1]

    # Construction de la nouvelle ligne
    row = {"Date": current_date}
    for ticker in tickers:
        price = latest_prices[ticker] if ticker in latest_prices.index else None
        row[ticker] = round(float(price), 4) if price is not None and pd.notna(price) else None

    return pd.DataFrame([row])


def update_csv_file(new_df):
    """Ajoute la nouvelle ligne seulement si la date n’existe pas déjà"""
    today = new_df["Date"].iloc[0]

    if os.path.exists(FILE_NAME):
        existing_df = pd.read_csv(FILE_NAME)

        # Protection contre les doublons
        if today in existing_df["Date"].astype(str).values:
            print(f"La date {today} existe déjà → rien à faire.")
            return

        # Alignement des colonnes (important si tu ajoutes/supprimes des tickers un jour)
        new_df = new_df.reindex(columns=existing_df.columns, fill_value=None)

        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        updated_df = new_df

    updated_df.to_csv(FILE_NAME, index=False)
    print(f"prices_daily.csv mis à jour avec succès pour {today}")


if __name__ == "__main__":
    current_date = get_current_date()
    print(f"Lancement de la mise à jour pour la date : {current_date}")

    new_data = get_new_data(current_date)

    if new_data is not None and not new_data.empty:
        update_csv_file(new_data)
    else:
        print("Aucune donnée n’a pu être récupérée aujourd’hui.")
