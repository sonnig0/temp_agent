import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

def load_data():
    """Lädt die Prognose- und Ist-Daten aus der SQLite-Datenbank."""
    conn = sqlite3.connect("weather_data.db")

    # Prognosedaten: reference_time = neueste reference_time
    prognosen_query = """
    SELECT timestamp, t2m, reference_time
    FROM prognosen
    WHERE reference_time = (SELECT MAX(reference_time) FROM prognosen)
    """
    prognosen_df = pd.read_sql(prognosen_query, conn)

    # Ist-Daten
    ist_daten_query = """
    SELECT timestamp, TL
    FROM ist_daten
    """
    ist_daten_df = pd.read_sql(ist_daten_query, conn)

    conn.close()

    # Gemeinsamen Zeitraum finden
    common_timestamps = pd.merge(
        prognosen_df[["timestamp"]],
        ist_daten_df[["timestamp"]],
        on="timestamp",
        how="inner"
    )["timestamp"]

    if common_timestamps.empty:
        return pd.DataFrame()

    # Daten für den gemeinsamen Zeitraum laden
    prognosen_filtered = prognosen_df[prognosen_df["timestamp"].isin(common_timestamps)]
    ist_daten_filtered = ist_daten_df[ist_daten_df["timestamp"].isin(common_timestamps)]

    # Zusammenführen und Spalten umbenennen
    merged_df = pd.merge(prognosen_filtered, ist_daten_filtered, on="timestamp", how="inner")
    merged_df = merged_df.rename(columns={
        "t2m": "Prognose (°C)",
        "TL": "Ist-Temperatur (°C)"
    })
    if not merged_df.empty:
        merged_df["Abweichung (°C)"] = merged_df["Ist-Temperatur (°C)"] - merged_df["Prognose (°C)"]
        merged_df["Abweichung (%)"] = (merged_df["Abweichung (°C)"] / merged_df["Prognose (°C)"]) * 100

    return merged_df

def main():
    st.set_page_config(layout="wide")  # Seitenbreite erweitern
    st.title("📊 Temperaturvergleich: Prognose vs. Ist-Daten")
    st.write("Hier siehst du die Abweichungen zwischen den Prognosedaten und den tatsächlichen Messwerten.")

    df = load_data()

    if not df.empty:


        st.subheader("📈 Temperaturverlauf (Prognose vs. Ist)")
        fig = px.line(
            df,
            x="timestamp",
            y=["Prognose (°C)", "Ist-Temperatur (°C)"],
            title="Temperaturverlauf",
            labels={"value": "Temperatur (°C)", "variable": "Daten"},
        )
        st.plotly_chart(fig)

        st.subheader("📊 Abweichungen in Prozent (Balkendiagramm)")
        fig_pct = px.bar(
            df,
            x="timestamp",
            y="Abweichung (%)",
            title="Abweichung in %",
            labels={"Abweichung (%)": "Abweichung (%)"},
        )
        st.plotly_chart(fig_pct)

        st.subheader("📉 Abweichungen (absolut)")
        fig_abs = px.line(
            df,
            x="timestamp",
            y="Abweichung (°C)",
            title="Abweichung in °C",
            labels={"Abweichung (°C)": "Abweichung (°C)"},
        )
        st.plotly_chart(fig_abs)

        st.subheader("📋 Daten")
        st.dataframe(df)

    else:
        st.warning("⚠️ Keine Daten für den Vergleich gefunden. Führe zuerst die Skripte für den Datenabruf aus!")

if __name__ == "__main__":
    main()