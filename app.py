from flask import Flask, render_template, jsonify, request
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import traceback

app = Flask(__name__)

# Your Nifty50 stock list (without .NS suffix)
NIFTY50_SYMBOLS = [
    'HDFCBANK', 'RELIANCE', 'ICICIBANK', 'ETERNAL', 'SBIN',
    'INFY', 'BHARTIARTL', 'AXISBANK', 'EICHERMOT', 'TRENT',
    'TCS', 'M&M', 'INDIGO', 'ITC', 'HINDALCO',
    'SUNPHARMA', 'ADANIENT', 'BAJFINANCE', 'MARUTI', 'JIOFIN',
    'SHRIRAMFIN', 'LT', 'KOTAKBANK', 'ONGC', 'ASIANPAINT',
    'BEL', 'HCLTECH', 'TITAN', 'TMPV', 'TATASTEEL',
    'WIPRO', 'NTPC', 'SBILIFE', 'APOLLOHOSP', 'DRREDDY',
    'TECHM', 'BAJAJ-AUTO', 'HINDUNILVR', 'POWERGRID', 'NESTLEIND',
    'HDFCLIFE', 'ADANIPORTS', 'MAXHEALTH', 'CIPLA', 'BAJAJFINSV',
    'COALINDIA', 'TATACONSUM', 'ULTRACEMCO', 'JSWSTEEL', 'GRASIM'
]

def analyze_stock(symbol):
    """
    Analyze a single stock
    Returns: dict with signal and data
    """
    try:
        # Add .NS suffix for NSE stocks
        symbol_nse = symbol + '.NS'
        print(f"Analyzing {symbol_nse}...")
        
        # Download data - get 1 year data
        stock = yf.Ticker(symbol_nse)
        df = stock.history(period="1y")
        
        if df.empty or len(df) < 50:
            return {
                'symbol': symbol,
                'signal': 'Insufficient Data',
                'current_price': None,
                'high_52w': None,
                'low_52w': None,
                'ma_50': None,
                'ma_100': None,
                'ma_200': None,
                'above_ma_50': False,
                'above_ma_100': False,
                'above_ma_200': False,
                'pct_above_ma_50': None,
                'pct_above_ma_100': None,
                'pct_above_ma_200': None,
                'cum_avg_last_10': None,
                'cum_avg_trend': None
            }
        
        # Get basic data
        current_price = float(df['Close'].iloc[-1])
        high_52w = float(df['High'].max())
        low_52w = float(df['Low'].min())
        
        # Calculate MAs
        prices = df['Close'].values
        ma_50 = float(np.mean(prices[-50:])) if len(prices) >= 50 else None
        ma_100 = float(np.mean(prices[-100:])) if len(prices) >= 100 else None
        ma_200 = float(np.mean(prices[-200:])) if len(prices) >= 200 else None
        
        # Calculate cumulative averages from highest high
        high_idx = df['High'].idxmax()
        prices_from_high = df.loc[high_idx:]['Close'].values
        
        cum_avg_last_10 = None
        cum_avg_trend = None
        trend_strong = False
        increasing_count = 0
        
        if len(prices_from_high) >= 10:
            cum_avg = []
            running_sum = 0
            for i, price in enumerate(prices_from_high, 1):
                running_sum += price
                cum_avg.append(running_sum / i)
            
            # Get last 10 cumulative averages
            cum_avg_last_10 = [float(x) for x in cum_avg[-10:]]
            
            # Check for consistent increases (9 comparisons)
            increasing_count = sum(1 for i in range(1, 10) if cum_avg_last_10[i] > cum_avg_last_10[i-1])
            trend_strong = (increasing_count == 9)
            
            # Create trend string showing increases
            trend_arrows = []
            for i in range(1, 10):
                if cum_avg_last_10[i] > cum_avg_last_10[i-1]:
                    trend_arrows.append('↑')
                else:
                    trend_arrows.append('↓')
            cum_avg_trend = f"{increasing_count}/9 increasing " + ''.join(trend_arrows)
        else:
            cum_avg_last_10 = None
            cum_avg_trend = "Insufficient data for trend analysis"
        
        # Check if price is above all MAs
        price_above_all = all([
            current_price > ma_50 if ma_50 else False,
            current_price > ma_100 if ma_100 else False,
            current_price > ma_200 if ma_200 else False
        ])
        
        # Determine signal
        if trend_strong and price_above_all and all([ma_50, ma_100, ma_200]):
            signal = 'Buy/Average Out'
        elif trend_strong:
            signal = 'Strong Trend (Wait for MA Breakout)'
        elif price_above_all:
            signal = 'Price Above All MAs (Check Trend)'
        else:
            signal = 'Avoid/Hold'
        
        return {
            'symbol': symbol,
            'signal': signal,
            'current_price': current_price,
            'high_52w': high_52w,
            'low_52w': low_52w,
            'ma_50': ma_50,
            'ma_100': ma_100,
            'ma_200': ma_200,
            'above_ma_50': current_price > ma_50 if ma_50 else False,
            'above_ma_100': current_price > ma_100 if ma_100 else False,
            'above_ma_200': current_price > ma_200 if ma_200 else False,
            'pct_above_ma_50': ((current_price - ma_50) / ma_50 * 100) if ma_50 else None,
            'pct_above_ma_100': ((current_price - ma_100) / ma_100 * 100) if ma_100 else None,
            'pct_above_ma_200': ((current_price - ma_200) / ma_200 * 100) if ma_200 else None,
            'cum_avg_last_10': cum_avg_last_10,
            'cum_avg_trend': cum_avg_trend,
            'increasing_count': increasing_count
        }
        
    except Exception as e:
        print(f"Error analyzing {symbol}: {str(e)}")
        traceback.print_exc()
        return {
            'symbol': symbol,
            'signal': 'Error',
            'current_price': None,
            'high_52w': None,
            'low_52w': None,
            'ma_50': None,
            'ma_100': None,
            'ma_200': None,
            'above_ma_50': False,
            'above_ma_100': False,
            'above_ma_200': False,
            'pct_above_ma_50': None,
            'pct_above_ma_100': None,
            'pct_above_ma_200': None,
            'cum_avg_last_10': None,
            'cum_avg_trend': None,
            'increasing_count': 0
        }

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze all Nifty50 stocks"""
    try:
        results = []
        total = len(NIFTY50_SYMBOLS)
        
        for i, symbol in enumerate(NIFTY50_SYMBOLS, 1):
            print(f"\nProcessing {i}/{total}: {symbol}")
            result = analyze_stock(symbol)
            if result:
                results.append(result)
            time.sleep(0.15)  # Slightly longer delay to avoid rate limiting
        
        # Sort results: Buy signals first, then Strong Trend, then Price Above MAs, then Hold
        signal_order = {
            'Buy/Average Out': 0,
            'Strong Trend (Wait for MA Breakout)': 1,
            'Price Above All MAs (Check Trend)': 2,
            'Avoid/Hold': 3,
            'Insufficient Data': 4,
            'Error': 5
        }
        results.sort(key=lambda x: signal_order.get(x.get('signal', 'Error'), 5))
        
        return jsonify({
            'success': True,
            'total_analyzed': len(results),
            'results': results
        })
        
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    
