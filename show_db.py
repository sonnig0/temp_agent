import sqlite3
import pandas as pd

# Verbindung zur Datenbank herstellen
conn = sqlite3.connect("weather_data.db")

# Prognosedaten anzeigen
print("=== PROGNOSEDATEN ===")
prognosen_df = pd.read_sql("SELECT * FROM prognosen LIMIT 24;", conn)
print(prognosen_df)

# Ist-Daten anzeigen
print("\n=== IST-DATEN ===")
ist_daten_df = pd.read_sql("SELECT * FROM ist_daten LIMIT 24;", conn)
print(ist_daten_df)

# Verbindung schließen
conn.close()