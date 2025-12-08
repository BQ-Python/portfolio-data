# scripts/update_prices_daily.py → VERSION ULTIME (à utiliser dès maintenant)
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

CSV_PATH = "prices_daily.csv"

print("Démarrage de la mise à jour automatique des cours...")

# 1. Charger le fichier existant (ou créer vide)
if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH, index_col=0, parse_dates=True)
    print(f"Fichier existant chargé → {len(df)} jours, {len(df.columns)} tickers")
else:
    df = pd.DataFrame()
    print("Nouveau fichier → première exécution")

# 2. Déterminer les tickers à mettre à jour → ceux déjà dans le CSV
tickers = [col for col in df.columns if col != "Date"]

# 3. Trouver la dernière date présente
if len(df) > 0:
    last_date = df.index[-1].date()
    print(f"Dernière date dans le fichier : {last_date}")
else:
    last_date = None
    print("Aucun historique → on va tout télécharger")

# 4. Date d'aujourd'hui (on s'arrête à hier)
today = datetime.now().date()
yesterday = today - timedelta(days=1)

# 5. Générer toutes les dates manquantes (de last_date+1 jusqu'à hier)
if last_date is None:
    # Première fois → on prend les 90 derniers jours (ou plus si tu veux)
    start_date = yesterday - timedelta(days=90)
else:
    start_date = last_date + timedelta(days=1)

if start_date > yesterday:
    print(f"{yesterday} déjà présent → rien à faire aujourd'hui")
    exit()

dates_to_fetch = pd.date_range(start=start_date, end=yesterday, freq='B')  # 'B' = jours ouvrés seulement
print(f"{len(dates_to_fetch)} jour(s) à récupérer : {dates_to_fetch[0].date()} → {dates_to_fetch[-1].date()}")

# 6. Téléchargement jour par jour (fiable même si yfinance bugge)
new_rows = []

for current_date in dates_to_fetch:
    date_str = current_date.strftime("%Y-%m-%d")
    row = {"Date": date_str}
    failed_this_day = 0

    print(f"  → Récupération du {date_str}...", end=" ")

    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(start=current_date, end=current_date + timedelta(days=1))
            if not hist.empty and current_date in hist.index.date:
                price = round(hist["Close"].iloc[-1], 4)
                row[ticker] = price
            else:
                # Garder dernière valeur connue
                prev_date = current_date - timedelta(days=1)
                while prev_date >= df.index[0].date() if len(df) > 0 else yesterday:
                    if prev_date in df.index.date:
                        known = df.loc[df.index.date == prev_date, ticker].iloc[-1]
                        row[ticker] = known if pd.notna(known) else None
                        break
                    prev_date -= timedelta(days=1)
                else:
                    row[ticker] = None
        except:
            row[ticker] = None
            failed_this_day += 1

    new_rows.append(row)
    print(f"OK ({failed_this_day} erreurs)")

# 7. Ajouter les nouvelles lignes
if new_rows:
    new_df = pd.DataFrame(new_rows)
    new_df["Date"] = pd.to_datetime(new_df["Date"])
    new_df = new_df.set_index("Date")

    df = pd.concat([df, new_df])
    df = df.sort_index()

    df.to_csv(CSV_PATH)
    print(f"Mise à jour terminée ! → {len(df)} jours au total")
else:
    print("Aucune nouvelle donnée à ajouter")

print("Tout est à jour !")
