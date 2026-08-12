import sqlite3
import pandas as pd
import json
from datetime import datetime

def load_data():
    """Lädt die Prognose- und Ist-Daten aus der SQLite-Datenbank."""
    conn = sqlite3.connect("weather_data.db")

    prognosen_query = """
    SELECT timestamp, t2m, reference_time
    FROM prognosen
    WHERE reference_time = (SELECT MAX(reference_time) FROM prognosen)
    """
    prognosen_df = pd.read_sql(prognosen_query, conn)

    ist_daten_query = """
    SELECT timestamp, TL
    FROM ist_daten
    """
    ist_daten_df = pd.read_sql(ist_daten_query, conn)

    conn.close()

    common_timestamps = pd.merge(
        prognosen_df[["timestamp"]],
        ist_daten_df[["timestamp"]],
        on="timestamp",
        how="inner"
    )["timestamp"]

    if common_timestamps.empty:
        return pd.DataFrame()

    prognosen_filtered = prognosen_df[prognosen_df["timestamp"].isin(common_timestamps)]
    ist_daten_filtered = ist_daten_df[ist_daten_df["timestamp"].isin(common_timestamps)]

    merged_df = pd.merge(prognosen_filtered, ist_daten_filtered, on="timestamp", how="inner")
    merged_df = merged_df.rename(columns={
        "t2m": "Prognose",
        "TL": "Ist"
    })

    merged_df["Abweichung"] = merged_df["Ist"] - merged_df["Prognose"]
    merged_df["Abweichung_pct"] = (merged_df["Abweichung"] / merged_df["Prognose"]) * 100

    return merged_df

def save_json(df):
    """Speichert die Daten als JSON für die Webpage."""
    data = {
        "timestamps": df["timestamp"].tolist(),
        "prognose": df["Prognose"].tolist(),
        "ist": df["Ist"].tolist(),
        "abweichung": df["Abweichung"].tolist(),
        "abweichung_pct": df["Abweichung_pct"].tolist()
    }

    with open("docs/data.json", "w") as f:
        json.dump(data, f, indent=2)

def save_html():
    """Erzeugt eine HTML-Datei, die Chart.js lädt und das JSON visualisiert."""
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Temperaturvergleich</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h1>Temperaturvergleich: Prognose vs. Ist</h1>
    <canvas id="chart1"></canvas>
    <canvas id="chart2"></canvas>
    <canvas id="chart3"></canvas>

    <script>
        fetch('data.json')
            .then(response => response.json())
            .then(data => {
                const labels = data.timestamps;

                new Chart(document.getElementById('chart1'), {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [
                            { label: 'Prognose', data: data.prognose, borderColor: 'red' },
                            { label: 'Ist', data: data.ist, borderColor: 'blue' }
                        ]
                    }
                });

                new Chart(document.getElementById('chart2'), {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [
                            { label: 'Abweichung (%)', data: data.abweichung_pct, backgroundColor: 'orange' }
                        ]
                    }
                });

                new Chart(document.getElementById('chart3'), {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [
                            { label: 'Abweichung (°C)', data: data.abweichung, borderColor: 'green' }
                        ]
                    }
                });
            });
    </script>
</body>
</html>
"""
    with open("docs/index.html", "w") as f:
        f.write(html)

def main():
    df = load_data()
    if df.empty:
        print("Keine Daten gefunden.")
        return

    save_json(df)
    save_html()
    print("Statische Webpage erfolgreich erzeugt.")

if __name__ == "__main__":
    main()
