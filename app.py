import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

@st.cache_data
def get_date_bounds():
    """Cached Abfrage für Min/Max Datum"""
    conn = sqlite3.connect("weather_data.db")
    min_date = pd.read_sql("SELECT MIN(DATE(timestamp)) FROM ist_daten", conn).iloc[0, 0]
    max_date = pd.read_sql("SELECT MAX(DATE(timestamp)) FROM ist_daten", conn).iloc[0, 0]
    conn.close()
    return min_date, max_date

@st.cache_data
def load_data(start_date, end_date):
    """Lädt die neueste Prognose für jeden Timestamp im Zeitraum"""
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    conn = sqlite3.connect("weather_data.db")

    # ✅ Optimiert: Nimm die neueste Prognose pro Timestamp (falls doch Mehrfacheinträge)
    prognosen_query = """
    SELECT p.timestamp, p.t2m
    FROM prognosen p
    INNER JOIN (
        SELECT timestamp, MAX(reference_time) as latest_ref
        FROM prognosen
        WHERE DATE(timestamp) BETWEEN ? AND ?
        GROUP BY timestamp
    ) latest ON p.timestamp = latest.timestamp AND p.reference_time = latest.latest_ref
    WHERE DATE(p.timestamp) BETWEEN ? AND ?
    """
    prognosen_df = pd.read_sql(prognosen_query, conn, params=(start_str, end_str, start_str, end_str))
    ist_daten_df = pd.read_sql(
        "SELECT timestamp, TL FROM ist_daten WHERE DATE(timestamp) BETWEEN ? AND ?",
        conn, params=(start_str, end_str)
    )
    conn.close()

    if prognosen_df.empty or ist_daten_df.empty:
        return pd.DataFrame()

    merged_df = pd.merge(prognosen_df, ist_daten_df, on="timestamp", how="inner")
    merged_df = merged_df.rename(columns={"t2m": "Prognose (°C)", "TL": "Ist-Temperatur (°C)"})
    if not merged_df.empty:
        merged_df["Abweichung (°C)"] = merged_df["Ist-Temperatur (°C)"] - merged_df["Prognose (°C)"]
        merged_df["Abweichung (%)"] = (merged_df["Abweichung (°C)"] / merged_df["Prognose (°C)"]) * 100
    return merged_df

# [... alle Imports und Funktionen bleiben gleich ...]

def main():
    st.set_page_config(layout="wide")
    st.title("📊 Temperaturvergleich: Prognose vs. Ist-Daten")
    st.write("Hier siehst du die Abweichungen zwischen den Prognosedaten und den tatsächlichen Messwerten.")

    st.write("### 📅 Zeitraum auswählen")
    min_date, max_date = get_date_bounds()
    today = datetime.now().date()

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Startdatum", value=today, min_value=min_date, max_value=today)
    with col2:
        end_date = st.date_input("Enddatum", value=today, min_value=min_date, max_value=today)

    # ✅ NEU: Neu-Laden-Button
    st.divider()
    if st.button("🔄 Daten neu laden", type="primary"):
        st.rerun()  # ⚡ Erzwingt Neuladen der gesamten App (inkl. Cache!)

    df = load_data(start_date, end_date)

    # [...] Rest bleibt unverändert [...]

    if not df.empty:
        st.subheader("📈 Temperaturverlauf (Prognose vs. Ist)")
        st.plotly_chart(px.line(
            df, x="timestamp", y=["Prognose (°C)", "Ist-Temperatur (°C)"],
            title="Temperaturverlauf", labels={"value": "Temperatur (°C)", "variable": "Daten"}
        ))
        st.subheader("📊 Abweichungen in Prozent")
        st.plotly_chart(px.bar(df, x="timestamp", y="Abweichung (%)", title="Abweichung in %"))
        st.subheader("📉 Abweichungen (absolut)")
        st.plotly_chart(px.line(df, x="timestamp", y="Abweichung (°C)", title="Abweichung in °C"))
        st.subheader("📋 Daten")
        st.dataframe(df)
    else:
        st.warning(f"⚠️ Keine Daten für {start_date} bis {end_date} gefunden. Verfügbar: {min_date} bis {max_date}")

if __name__ == "__main__":
    main()