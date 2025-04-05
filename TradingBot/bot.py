import os
import time
import json
from datetime import datetime, timedelta
import pandas as pd
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

app = Flask(__name__)
CORS(app)

# Configuration
BINANCE_API_URL = "https://api.binance.com/api/v3"
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

class ScalpingBot:
    def __init__(self, initial_balance=100):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.eth_balance = 0
        self.trades = []
        self.current_trade = None
        self.strategy_name = "EMA8_21_RSI_MACD_BB"

    def get_historical_data(self, days=30, interval='5m'):
        """Fetch historical data from Binance"""
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int(datetime.now() - timedelta(days=days)).timestamp() * 1000
        
        all_data = []
        while start_time < end_time:
            url = f"{BINANCE_API_URL}/klines"
            params = {
                'symbol': 'ETHUSDT',
                'interval': interval,
                'limit': 1000,
                'startTime': start_time
            }
            response = requests.get(url, params=params)
            data = response.json()
            if not data:
                break
            all_data.extend(data)
            start_time = data[-1][0] + 1
        
        df = pd.DataFrame(all_data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, axis=1)
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        return df

    def calculate_indicators(self, df):
        """Calculate technical indicators"""
        df['ema_8'] = EMAIndicator(close=df['close'], window=8).ema_indicator()
        df['ema_21'] = EMAIndicator(close=df['close'], window=21).ema_indicator()
        df['rsi'] = RSIIndicator(close=df['close'], window=14).rsi()
        
        macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        
        bb = BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()
        return df

    def generate_signal(self, row, prev_row):
        """More flexible signal generation"""
        # Buy when majority of conditions are met
        buy_score = sum([
            row['ema_8'] > row['ema_21'],
            row['rsi'] < 65,  # More flexible RSI
            row['macd'] > row['macd_signal'],
            row['close'] > row['bb_middle'],
            prev_row['macd'] <= prev_row['macd_signal']
        ])
        
        # Sell when majority of conditions are met
        sell_score = sum([
            row['ema_8'] < row['ema_21'],
            row['rsi'] > 35,  # More flexible RSI
            row['macd'] < row['macd_signal'],
            row['close'] < row['bb_middle'],
            prev_row['macd'] >= prev_row['macd_signal']
        ])
    
    # Require at least 4/5 conditions
        if buy_score >= 4:
            return 'buy'
        elif sell_score >= 4:
            return 'sell'
        return 'hold'

    def execute_trade(self, signal, price, timestamp):
        """Execute trade with proper datetime handling"""
        if signal == 'buy' and self.current_trade is None:
            self.eth_balance = self.balance / price
            self.balance = 0
            self.current_trade = {
                'entry_price': price,
                'entry_time': pd.to_datetime(timestamp) if isinstance(timestamp, str) else timestamp,
                'position_size': self.eth_balance
            }
            return True
        
        elif signal == 'sell' and self.current_trade is not None:
            self.balance = self.eth_balance * price
            profit = self.balance - self.initial_balance
            
            self.trades.append({
                **self.current_trade,
                'exit_price': price,
                'exit_time': pd.to_datetime(timestamp) if isinstance(timestamp, str) else timestamp,
                'profit': profit,
                'profit_pct': (profit / self.initial_balance) * 100
            })
            
            self.eth_balance = 0
            self.current_trade = None
            return True
        
        return False

    def generate_results(self):
        """Generate results with serializable datetimes"""
        results = {
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'total_profit': sum(trade['profit'] for trade in self.trades),
            'profit_pct': (self.balance - self.initial_balance) / self.initial_balance * 100,
            'num_trades': len(self.trades),
            'win_rate': (sum(1 for t in self.trades if t['profit'] > 0) / len(self.trades) * 100 if self.trades else 0),
            'trades': self.trades.copy(),
            'strategy_name': self.strategy_name,
            'timestamp': datetime.now().isoformat()
        }
        
        # Ensure all datetimes are strings
        for trade in results['trades']:
            for time_key in ['entry_time', 'exit_time']:
                if time_key in trade and trade[time_key] is not None:
                    if isinstance(trade[time_key], (pd.Timestamp, datetime)):
                        trade[time_key] = trade[time_key].isoformat()
        
        return results

    def backtest(self, days=30):
        """Backtest strategy on historical data"""
        df = self.get_historical_data(days)
        df = self.calculate_indicators(df)
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            signal = self.generate_signal(row, prev_row)
            self.execute_trade(signal, row['close'], row['open_time'])
        
        # Finalize any open position
        if self.current_trade is not None:
            self.execute_trade('sell', df.iloc[-1]['close'], df.iloc[-1]['open_time'])
        
        return self.generate_results()

    def generate_results(self):
        """Generate backtest results"""
        total_profit = sum(trade['profit'] for trade in self.trades)
        profit_pct = (total_profit / self.initial_balance) * 100
        num_trades = len(self.trades)
        win_rate = (sum(1 for t in self.trades if t['profit'] > 0) / num_trades * 100) if num_trades > 0 else 0
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'total_profit': total_profit,
            'profit_pct': profit_pct,
            'num_trades': num_trades,
            'win_rate': win_rate,
            'trades': self.trades,
            'strategy': self.strategy_name,
            'timestamp': datetime.now().isoformat()
        }

    def save_results(self, results, filename_prefix):
        """Save results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{RESULTS_DIR}/{filename_prefix}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        return filename
    
@app.route('/debug/conditions', methods=['GET'])
def debug_conditions():
    """Endpoint to check current market conditions"""
    try:
        bot = ScalpingBot(100)
        df = bot.get_historical_data(days=3)  # Check last 3 days
        df = bot.calculate_indicators(df)
        
        signals = []
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # Convert datetime to string for JSON serialization
            time_str = row['open_time'].isoformat() if pd.notnull(row['open_time']) else None
            
            buy_score = sum([
                row['ema_8'] > row['ema_21'],
                row['rsi'] < 65,
                row['macd'] > row['macd_signal'],
                row['close'] > row['bb_middle']
            ])
            
            sell_score = sum([
                row['ema_8'] < row['ema_21'],
                row['rsi'] > 35,
                row['macd'] < row['macd_signal'],
                row['close'] < row['bb_middle']
            ])
            
            signals.append({
                'time': time_str,
                'price': float(row['close']),
                'ema_8': float(row['ema_8']),
                'ema_21': float(row['ema_21']),
                'rsi': float(row['rsi']),
                'macd': float(row['macd']),
                'macd_signal': float(row['macd_signal']),
                'bb_middle': float(row['bb_middle']),
                'buy_score': buy_score,
                'sell_score': sell_score,
                'signal': 'buy' if buy_score >= 3 else 'sell' if sell_score >= 3 else 'hold'
            })
        
        return jsonify({
            'success': True,
            'data_points': len(df),
            'signals': signals[-20:],  # Last 20 data points
            'current_conditions': signals[-1] if signals else None
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data_points': 0,
            'signals': []
        }), 500
    
@app.route('/backtest', methods=['POST'])
def run_backtest():
    try:
        data = request.json or {}
        initial_balance = float(data.get('initial_balance', 100))
        days = int(data.get('days', 30))
        
        bot = ScalpingBot(initial_balance)
        results = bot.backtest(days)
        filename = bot.save_results(results, "backtest")
        
        # Convert datetime objects to strings
        if 'trades' in results:
            for trade in results['trades']:
                if 'entry_time' in trade:
                    trade['entry_time'] = trade['entry_time'].isoformat() if pd.notnull(trade['entry_time']) else None
                if 'exit_time' in trade:
                    trade['exit_time'] = trade['exit_time'].isoformat() if pd.notnull(trade['exit_time']) else None
        
        return jsonify({
            'success': True,
            'results': results,
            'file': filename
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'results': {
                'initial_balance': 100,
                'final_balance': 100,
                'total_profit': 0,
                'profit_pct': 0,
                'num_trades': 0,
                'win_rate': 0,
                'trades': [],
                'strategy': 'EMA8_21_RSI_MACD_BB'
            },
            'file': None
        }), 500

@app.route('/live', methods=['POST'])
def run_live():
    try:
        data = request.json or {}
        initial_balance = float(data.get('initial_balance', 100))
        
        bot = ScalpingBot(initial_balance)
        df = bot.get_historical_data(days=1, interval='5m')
        df = bot.calculate_indicators(df)
        
        signal = bot.generate_signal(df.iloc[-1], df.iloc[-2])
        price = float(df.iloc[-1]['close'])
        timestamp = datetime.now().isoformat()
        
        executed = bot.execute_trade(signal, price, timestamp)
        
        response = {
            'success': True,
            'signal': signal,
            'price': price,
            'executed': executed,
            'balance': float(bot.balance),
            'eth_balance': float(bot.eth_balance),
            'timestamp': timestamp,
            'results': None,
            'file': None
        }
        
        if executed:
            results = bot.generate_results()
            filename = bot.save_results(results, "live_trade")
            
            # Convert datetime objects
            if 'trades' in results:
                for trade in results['trades']:
                    if 'entry_time' in trade:
                        trade['entry_time'] = trade['entry_time'].isoformat() if pd.notnull(trade['entry_time']) else None
                    if 'exit_time' in trade:
                        trade['exit_time'] = trade['exit_time'].isoformat() if pd.notnull(trade['exit_time']) else None
            
            response.update({
                'results': results,
                'file': filename
            })
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'signal': 'error',
            'price': 0,
            'executed': False,
            'balance': float(data.get('initial_balance', 100)),
            'eth_balance': 0,
            'timestamp': datetime.now().isoformat(),
            'results': None,
            'file': None
        }), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)