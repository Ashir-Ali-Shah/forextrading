import pandas as pd
import numpy as np
import yfinance as yf
import streamlit as st
from ta.trend import SMAIndicator, EMAIndicator
from ta.momentum import RSIIndicator


class TradingModel:
    def __init__(self, currency_pair, account_balance, risk_percent, stop_loss_pips, pip_value):
        self.currency_pair = currency_pair
        self.account_balance = account_balance
        self.risk_percent = risk_percent
        self.stop_loss_pips = stop_loss_pips
        self.pip_value = pip_value
        self.data = None

    def fetch_data(self, interval="1d", period="1mo"):
        ticker_map = {
            "XAUUSD": "GC=F",
            "EURUSD": "EURUSD=X",
            "GBPUSD": "GBPUSD=X",
            "USDJPY": "JPY=X"
        }
        ticker = ticker_map.get(self.currency_pair, self.currency_pair)
        try:
            self.data = yf.download(ticker, period=period, interval=interval)
            if self.data.empty:
                raise ValueError("No data fetched. Please check the currency pair or network connection.")
            
            # Ensure data['Close'] is a pandas Series (1-dimensional)
            close_prices = self.data['Close'].squeeze()

            # Calculate Indicators
            self.data['SMA'] = SMAIndicator(close_prices, window=14).sma_indicator()
            self.data['EMA'] = EMAIndicator(close_prices, window=14).ema_indicator()
            self.data['RSI'] = RSIIndicator(close_prices, window=14).rsi()

            # Drop rows with NaN values (caused by insufficient data for indicators)
            self.data.dropna(inplace=True)
        except Exception as e:
            raise ValueError(f"Error fetching data: {e}")

    def generate_signal(self):
        if self.data is None or self.data.empty:
            raise ValueError("Data not loaded or insufficient data for generating signals.")
        
        # Extract the last row and ensure scalar values
        last_row = self.data.iloc[-1]
        rsi = float(last_row['RSI'])
        close = float(last_row['Close'])
        sma = float(last_row['SMA'])

        # Generate signals based on conditions
        if rsi < 30 and close > sma:
            take_profit = close + (self.stop_loss_pips * self.pip_value)
            stop_loss = close - (self.stop_loss_pips * self.pip_value)
            return "Buy", close, take_profit, stop_loss
        elif rsi > 70 and close < sma:
            take_profit = close - (self.stop_loss_pips * self.pip_value)
            stop_loss = close + (self.stop_loss_pips * self.pip_value)
            return "Sell", close, take_profit, stop_loss
        else:
            return "Hold", close, None, None

    def calculate_lot_size(self):
        risk_amount = self.account_balance * (self.risk_percent / 100)
        lot_size = risk_amount / (self.stop_loss_pips * self.pip_value)
        return round(lot_size, 2)


# Streamlit App
def main():
    st.title("Forex Trading Signal Generator")

    # Sidebar inputs for user parameters
    st.sidebar.header("User Inputs")
    currency_pair = st.sidebar.selectbox("Select Currency Pair", ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"])
    account_balance = st.sidebar.number_input("Account Balance (USD)", min_value=100.0, value=1000.0)
    risk_percent = st.sidebar.slider("Risk Percentage (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
    stop_loss_pips = st.sidebar.number_input("Stop Loss (in Pips)", min_value=10, value=50)
    pip_value = st.sidebar.number_input("Pip Value (USD)", min_value=0.01, value=10.0)
    interval = st.sidebar.selectbox("Select Data Interval", ["1d", "1h", "5m", "1wk"])

    # Run model when user clicks button
    if st.sidebar.button("Generate Signal"):
        # Initialize the trading model
        model = TradingModel(currency_pair, account_balance, risk_percent, stop_loss_pips, pip_value)

        # Fetch data
        try:
            st.write(f"Fetching data for {currency_pair}...")
            model.fetch_data(interval=interval)

            # Generate signal
            signal, entry_price, take_profit, stop_loss = model.generate_signal()
            st.write(f"**Trade Signal:** {signal}")
            st.write(f"**Entry Price:** {entry_price}")
            if signal != "Hold":
                st.write(f"**Take Profit:** {take_profit}")
                st.write(f"**Stop Loss:** {stop_loss}")

            # Calculate lot size
            lot_size = model.calculate_lot_size()
            st.write(f"**Recommended Lot Size:** {lot_size} lots")

            # Display data and indicators
            st.line_chart(model.data[['Close', 'SMA', 'EMA']])
        except ValueError as e:
            st.error(e)


if __name__ == "__main__":
    main()
