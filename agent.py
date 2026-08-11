import requests
import pandas as pd
from datetime import datetime, timedelta
import sqlite3

def fetch_historical_data(station_id, start_date, end_date, parameter="TL"):
    """
    Ruft historische Stundendaten von der Geosphere-API ab.
    """
    url = (
        f"https://dataset.api.hub.geosphere.at/v1/station/historical/klima-v2-1h"
        f"?parameters={parameter}"
        f"&start={start_date}T00:00"
        f"&end={end_date}T23:59"
        f"&station_ids={station_id}"
        "&output_format=geojson"
    )

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der Daten für {parameter}: {e}")
        return None

def extract_data(api_response, parameter):
    """
    Extrahiert die Daten aus der API-Antwort und erstellt ein DataFrame.
    """
    if not api_response:
        print(f"Keine API-Antwort für {parameter} erhalten.")
        return None

    timestamps = api_response.get("timestamps", [])
    features = api_response.get("features", [])

    if not features or not timestamps:
        print(f"Keine Daten oder Zeitstempel für {parameter} gefunden.")
        return None

    feature = features[0]
    parameter_data = feature.get("properties", {}).get("parameters", {}).get(parameter.lower(), {}).get("data", [])

    if not parameter_data:
        print(f"Keine Daten für Parameter {parameter} gefunden.")
        return None

    if len(timestamps) != len(parameter_data):
        print(f"Warnung: Anzahl der Zeitstempel stimmt nicht mit der Anzahl der Daten überein.")
        min_length = min(len(timestamps), len(parameter_data))
        timestamps = timestamps[:min_length]
        parameter_data = parameter_data[:min_length]

    df = pd.DataFrame({
        "timestamp": timestamps,
        parameter: parameter_data
    })

    return df

def save_to_sqlite(dataframes):
    """
    Speichert die Ist-Daten in der SQLite-Datenbank.
    Löscht vorher die alten Daten vom gleichen Tag.
    """
    conn = sqlite3.connect("weather_data.db")
    cursor = conn.cursor()

    # Tabelle für Ist-Daten erstellen (falls nicht vorhanden)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ist_daten (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        TL REAL
    )
    """)

    # Alte Daten vom gleichen Tag löschen
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(f"DELETE FROM ist_daten WHERE timestamp LIKE '{today}%'")

    for parameter, df in dataframes.items():
        for _, row in df.iterrows():
            cursor.execute(
                "INSERT INTO ist_daten (timestamp, TL) VALUES (?, ?)",
                (row["timestamp"], row[parameter])
            )

    conn.commit()
    conn.close()
    print("Ist-Daten erfolgreich in der SQLite-Datenbank gespeichert.")

def main():
    station_id = "5925"  # Wien Hohe Warte

    # Zeiträume: Gestern 12:00 Uhr bis heute 11:00 Uhr
    yesterday_12h = (datetime.now().replace(hour=12, minute=0, second=0, microsecond=0) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    today_11h = datetime.now().replace(hour=11, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")

    # API-Abruf: Gestern 00:00 bis heute 23:59 (um alle Daten zu bekommen)
    start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    parameters = ["TL"]  # Lufttemperatur

    print(f"Starte Datenabruf für Station {station_id} von {yesterday_12h} bis {today_11h}...")

    dataframes = {}

    for parameter in parameters:
        print(f"\nAbruf der Daten für Parameter {parameter}...")
        api_response = fetch_historical_data(station_id, start_date, end_date, parameter)
        if not api_response:
            continue

        df = extract_data(api_response, parameter)
        if df is not None:
            # Filtere auf gestern 12:00 Uhr bis heute 11:00 Uhr
            df["datetime"] = pd.to_datetime(df["timestamp"])
            filtered_df = df[
                (df["datetime"] >= yesterday_12h) &
                (df["datetime"] <= today_11h)
            ].copy()
            filtered_df.drop(columns=["datetime"], inplace=True)
            dataframes[parameter] = filtered_df

    if not dataframes:
        print("Keine gültigen Daten gefunden.")
        return

    save_to_sqlite(dataframes)

if __name__ == "__main__":
    main()