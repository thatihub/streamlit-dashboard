
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="RSI + Price Dashboard (Upload File)", layout="wide")
REFRESH_INTERVAL = 60
st_autorefresh(interval=REFRESH_INTERVAL * 1000, limit=None, key="dashboardrefresh")

st.markdown(
    """
    <style>
    .main { background-color: #121212; color: #E0E0E0; }
    .stButton>button { background-color: #333 !important; color: #EEE !important; }
    </style>
    """, unsafe_allow_html=True)

plt.style.use('dark_background')

uploaded_file = st.file_uploader("📂 Upload your ticker .txt file", type="txt")

if uploaded_file is not None:
    content = uploaded_file.read().decode('utf-8')
    TICKERS = [line.strip() for line in content.splitlines() if line.strip()]
    st.success(f"✅ Loaded {len(TICKERS)} tickers from uploaded file.")
else:
    st.error("❌ Please upload a .txt file with tickers to continue.")
    st.stop()

MAX_HISTORY = 100

def calculate_rsi(data, period=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def clear_session():
    for key in ['rsi5_list', 'rsi15_list', 'price_list']:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.session_cleared = True

st.sidebar.button("🧹 Clear Session", on_click=clear_session)
if st.session_state.get('session_cleared', False):
    st.success("✅ Session cleared.")
    st.session_state.session_cleared = False

if 'rsi5_list' not in st.session_state:
    st.session_state.rsi5_list = []
if 'rsi15_list' not in st.session_state:
    st.session_state.rsi15_list = []
if 'price_list' not in st.session_state:
    st.session_state.price_list = []

st.header(f"🌙 RSI + Average Price Dashboard (Uploaded File)")

avg_rsi_5m, avg_rsi_15m, avg_prices, compact_alerts = [], [], [], []

for ticker in TICKERS:
    data_5m = yf.download(ticker, interval='5m', period='1d', progress=False)
    data_15m = yf.download(ticker, interval='15m', period='5d', progress=False)

    rsi_5m = float(calculate_rsi(data_5m).dropna().iloc[-1]) if not calculate_rsi(data_5m).dropna().empty else np.nan
    rsi_15m = float(calculate_rsi(data_15m).dropna().iloc[-1]) if not calculate_rsi(data_15m).dropna().empty else np.nan
    price = float(data_5m['Close'].dropna().iloc[-1]) if not data_5m['Close'].dropna().empty else np.nan

    avg_rsi_5m.append(rsi_5m)
    avg_rsi_15m.append(rsi_15m)
    avg_prices.append(price)

    if rsi_5m >= 70 and rsi_15m >= 70:
        tag = "🟢 S-L"
    elif rsi_5m <= 30 and rsi_15m <= 30:
        tag = "🔴 S-P"
    else:
        tag = "🟡 Neutral"
    compact_alerts.append(f"{ticker} ({rsi_5m:.1f} / {rsi_15m:.1f}) → {tag}")

overall_5m = pd.Series(avg_rsi_5m).mean(skipna=True)
overall_15m = pd.Series(avg_rsi_15m).mean(skipna=True)
avg_price = pd.Series(avg_prices).mean(skipna=True)

if overall_5m >= 70 and overall_15m >= 70:
    overall_tag = "🟢 S-L"
elif overall_5m <= 30 and overall_15m <= 30:
    overall_tag = "🔴 S-P"
else:
    overall_tag = "🟡 Neutral"

st.session_state.rsi5_list.append(overall_5m)
st.session_state.rsi15_list.append(overall_15m)
st.session_state.price_list.append(avg_price)

if len(st.session_state.rsi5_list) > MAX_HISTORY:
    st.session_state.rsi5_list = st.session_state.rsi5_list[-MAX_HISTORY:]
    st.session_state.rsi15_list = st.session_state.rsi15_list[-MAX_HISTORY:]
    st.session_state.price_list = st.session_state.price_list[-MAX_HISTORY:]

if overall_5m > 50 and overall_15m > 50:
    signal = "🟢 Bullish"
elif overall_5m < 50 and overall_15m < 50:
    signal = "🔴 Bearish"
elif (overall_5m > 60 and overall_15m < 40) or (overall_5m < 40 and overall_15m > 60):
    signal = "🟡 Divergent"
else:
    signal = "🟡 Neutral"

st.markdown(f"<div style='background-color:#222;padding:15px;border-radius:10px;font-size:20px;text-align:center;margin-bottom:15px;font-weight:bold;color:#FFF;'>Signal Summary: {signal}</div>", unsafe_allow_html=True)
st.markdown("### 📋 Ticker RSI Summary")
for alert in compact_alerts:
    st.markdown(f"- {alert}")

st.markdown(f"### 🌎 Overall Average\nALL ({overall_5m:.1f} / {overall_15m:.1f}) → {overall_tag}")

df = pd.DataFrame({
    '5m_RSI': st.session_state.rsi5_list,
    '15m_RSI': st.session_state.rsi15_list,
    'Avg_Price': st.session_state.price_list
})

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
ax1.plot(df['5m_RSI'], label='Avg 5m RSI', color='#00BFFF')
ax1.plot(df['15m_RSI'], label='Avg 15m RSI', color='#FF69B4')
ax1.axhline(70, color='red', linestyle=':', label='Overbought (70)')
ax1.axhline(30, color='lime', linestyle=':', label='Oversold (30)')
ax1.set_ylim(0, 100)
ax1.set_ylabel('RSI Value')
ax1.legend(facecolor='#222', edgecolor='none', fontsize=9)
ax1.grid(True, color='#444')
ax1.set_facecolor('#121212')

ax2.plot(df['Avg_Price'], label='Avg Price', color='orange')
ax2.set_ylabel('Average Price ($)')
ax2.set_xlabel('Refresh Cycles')
ax2.legend(facecolor='#222', edgecolor='none', fontsize=9)
ax2.grid(True, color='#444')
ax2.set_facecolor('#121212')

st.pyplot(fig)
