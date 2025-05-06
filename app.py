import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import zscore
from io import BytesIO
import plotly.express as px

st.set_page_config(page_title="Half-Hour Analyzer", layout="wide")
st.title("Half-Hourly Data Anomaly & Trend Analysis Tool")

uploaded_file = st.file_uploader("Upload Excel or CSV File", type=["xlsx", "xls", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    if 'Timestamp' not in df.columns or 'Value' not in df.columns:
        st.error("File must contain 'Timestamp' and 'Value' columns.")
    else:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        df = df.sort_values('Timestamp')
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
        df.dropna(subset=['Value'], inplace=True)

        df['ZScore'] = zscore(df['Value'].fillna(method='ffill'))
        df['Anomaly'] = abs(df['ZScore']) > 3

        df.set_index('Timestamp', inplace=True)
        df['7d_Rolling'] = df['Value'].rolling('7D').mean()
        df.reset_index(inplace=True)

        df['Date'] = df['Timestamp'].dt.date
        df['DayOfWeek'] = df['Timestamp'].dt.day_name()
        df['IsWeekend'] = df['DayOfWeek'].isin(['Saturday', 'Sunday'])

        st.subheader("📈 Anomaly Visualization")
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(df['Timestamp'], df['Value'], label='Value')
        ax.plot(df['Timestamp'], df['7d_Rolling'], label='7-day Avg', color='green')
        ax.scatter(df.loc[df['Anomaly'], 'Timestamp'], df.loc[df['Anomaly'], 'Value'], color='red', label='Anomaly')
        ax.set_title("Values, Rolling Average & Anomalies")
        ax.set_xlabel("Time")
        ax.set_ylabel("Value")
        ax.legend()
        st.pyplot(fig)

        st.subheader("📊 Trend Summary")
        daily_avg = df.groupby('Date')['Value'].mean()
        weekday_avg = df.groupby('IsWeekend')['Value'].mean()

        st.line_chart(daily_avg.rename("Daily Average"))
        st.write("**Weekday vs Weekend Average:**")
        st.bar_chart(weekday_avg.rename({False: "Weekday", True: "Weekend"}))

        st.subheader("📆 Weekly Comparison Trend")

        df['Week'] = df['Timestamp'].dt.to_period('W').apply(lambda r: r.start_time)
        df['Weekday'] = df['Timestamp'].dt.weekday
        df['HalfHour'] = df['Timestamp'].dt.hour * 2 + df['Timestamp'].dt.minute // 30
        pivot = df.pivot_table(index=['Weekday', 'HalfHour'], columns='Week', values='Value')

        fig2 = plt.figure(figsize=(12, 5))
        for week in pivot.columns:
            plt.plot(pivot.index, pivot[week], label=str(week.date()))
        plt.title("Weekly Half-Hourly Comparison")
        plt.xlabel("Time of Week (Weekday + HalfHour Slot)")
        plt.ylabel("Value")
        plt.legend()
        st.pyplot(fig2)

        st.subheader("📥 Download Anomalies")
        anomaly_df = df[df['Anomaly']][['Timestamp', 'Value', 'ZScore']]
        st.dataframe(anomaly_df)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            anomaly_df.to_excel(writer, index=False, sheet_name='Anomalies')
        st.download_button("Download Anomalies as Excel", data=output.getvalue(), file_name="anomalies.xlsx")
