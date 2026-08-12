import requests
import pandas as pd
from datetime import datetime, timedelta
import sqlite3

def fetch_forecast_data(resource_id, lat, lon, parameters, start_date, end_date, forecast_offset=5):
    """
    Ruft Prognosedaten von der Geosphere-API ab.
    forecast_offset=5: Prognose von gestern 12:00 Uhr.
    """
    params = {
        "lat_lon": f"{lat},{lon}",
        "parameters": ",".join(parameters),
        "start": start_date,
        "end": end_date,
        "forecast_offset": forecast_offset,
        "output_format": "geojson"
    }

    url = f"https://dataset.api.hub.geosphere.at/v1/timeseries/forecast/{resource_id}"

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der Prognosedaten: {e}")
        print(f"URL: {url}")
        return None

def extract_forecast_data(api_response, parameters):
    """
    Extrahiert die Prognosedaten aus der API-Antwort und erstellt DataFrames.
    """
    if not api_response:
        print("Keine API-Antwort erhalten.")
        return None, None

    features = api_response.get("features", [])
    if not features:
        print("Keine Features in der API-Antwort gefunden.")
        return None, None

    dataframes = {}
    timestamps = api_response.get("timestamps", [])
    reference_time = api_response.get("reference_time", "Unbekannt")

    for feature in features:
        properties = feature.get("properties", {})
        for parameter in parameters:
            parameter_data = properties.get("parameters", {}).get(parameter, {}).get("data", [])
            if not parameter_data:
                print(f"Keine Daten für Parameter {parameter} gefunden.")
                continue

            if len(timestamps) != len(parameter_data):
                print(f"Warnung: Anzahl der Zeitstempel stimmt nicht mit der Anzahl der Daten für {parameter} überein.")
                min_length = min(len(timestamps), len(parameter_data))
                timestamps = timestamps[:min_length]
                parameter_data = parameter_data[:min_length]

            df = pd.DataFrame({
                "timestamp": timestamps,
                parameter: parameter_data,
                "reference_time": reference_time
            })
            dataframes[parameter] = df

    return dataframes, reference_time

def filter_today_data(dataframes):
    """
    Filtert die Daten, sodass nur die Einträge von heute 00:00 bis 23:00 Uhr übrig bleiben.
    """
    today = datetime.now().date()
    filtered_dataframes = {}

    for parameter, df in dataframes.items():
        df["datetime"] = pd.to_datetime(df["timestamp"])
        today_data = df[
            (df["datetime"].dt.date == today) &
            (df["datetime"].dt.hour >= 0) &
            (df["datetime"].dt.hour < 24)
        ].copy()
        today_data.drop(columns=["datetime"], inplace=True)
        filtered_dataframes[parameter] = today_data

    return filtered_dataframes

def save_to_sqlite(dataframes, reference_time):
    """Speichert die Prognosedaten in der SQLite-Datenbank.
    Überschreibt alle bestehenden Prognosen für den heutigen Tag.
    """
    conn = sqlite3.connect("weather_data.db")
    cursor = conn.cursor()

    # Tabelle für Prognosedaten erstellen (falls nicht vorhanden)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prognosen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        t2m REAL,
        reference_time TEXT
    )
    """)

    # Lösche alle Prognosen für den heutigen Tag (00:00–23:00 Uhr)
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(f"DELETE FROM prognosen WHERE DATE(timestamp) = '{today}'")

    # Füge die neue Prognose ein
    for parameter, df in dataframes.items():
        for _, row in df.iterrows():
            cursor.execute(
                "INSERT INTO prognosen (timestamp, t2m, reference_time) VALUES (?, ?, ?)",
                (row["timestamp"], row[parameter], reference_time)
            )

    conn.commit()
    conn.close()
    print(f"Prognosedaten (reference_time: {reference_time}) erfolgreich in der SQLite-Datenbank gespeichert.")

def main():
    resource_id = "nwp-v1-1h-2500m"
    lat = 48.19912014480653
    lon = 16.36938518275234
    parameters = ["t2m"]

    # Zeitraumberechnung: Gestern 12:00 bis heute + 1 Tag
    yesterday_12h = datetime.now() - timedelta(days=1, hours=12)
    start_date = yesterday_12h.strftime("%Y-%m-%dT%H:%M")
    end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")

    forecast_offset = 5  # Prognose von gestern 12:00 Uhr

    print(f"Starte Abruf der Prognosedaten für Koordinaten (Lat: {lat}, Lon: {lon})...")
    print(f"Zeitraum: {start_date} bis {end_date}")

    api_response = fetch_forecast_data(resource_id, lat, lon, parameters, start_date, end_date, forecast_offset)
    if not api_response:
        return

    dataframes, reference_time = extract_forecast_data(api_response, parameters)
    if not dataframes:
        return

    filtered_dataframes = filter_today_data(dataframes)
    save_to_sqlite(filtered_dataframes, reference_time)

if __name__ == "__main__":
    main()