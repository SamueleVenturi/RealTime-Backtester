import ccxt
from datetime import datetime
import pandas as pd
import yfinance as yf
import global_vars
import pandas as pd
import asyncio
import requests
import os
import pandas_market_calendars as mcal

update_last_bar_task = None  

def update_bars(df, limit):
    if limit == 1 and not global_vars.chart_data.empty:
        if global_vars.chart_data.index[-1] == df.index[0]:
            global_vars.chart_data.iloc[-1] = df.iloc[0]
        else:
            global_vars.chart_data = pd.concat([global_vars.chart_data, df])
            global_vars.wait_event.set()
    else:
        global_vars.chart_data = df
        global_vars.wait_event.set()   

async def update_last_bar(df, symbol, timeframe, limit, chart):
    global update_last_bar_task
    for idx, row in df.iterrows():
        if idx == global_vars.chart_data.index[-1]:
            if row['Volume'] != 0:
                global_vars.chart_data.iloc[-1] = df.loc[idx]

                if global_vars.chart_data.index[-1] == df.index[-1]:
                    last_time = datetime.strptime(global_vars.chart_data.index[-1], '%Y-%m-%d %H:%M')
                    current_time = datetime.now()

                    if (current_time - last_time).seconds >= 60:
                        print("Requesting empty candle")
                        await asyncio.sleep(1)
                        fetch_data_from_yf(symbol, timeframe, limit, chart)

                global_vars.chart_data = pd.concat([global_vars.chart_data, df.iloc[[-1]]])
                global_vars.wait_event.set()
                chart.set(global_vars.chart_data)   
                break
            else:
                print("Requesting previous minute candle")
                await asyncio.sleep(1)
                fetch_data_from_yf(symbol, timeframe, limit, chart)   

def order_data(data, type, limit, symbol=None, timeframe=None, chart=None):
    global update_last_bar_task
    if type:
        standard = {
            'Datetime': [datetime.fromtimestamp(bar[0] / 1000).strftime('%Y-%m-%d %H:%M') for bar in data],
            'Open': [bar[1] for bar in data],
            'High': [bar[2] for bar in data],
            'Low': [bar[3] for bar in data],
            'Close': [bar[4] for bar in data],
            'Volume': [bar[5] for bar in data]
        }
        df = pd.DataFrame(standard)
        df.set_index('Datetime', inplace=True)
    else:
        if limit == 1:
            data = data.tail(5)
        else:
            data = data.tail(limit)
        df = data.copy()
        df.index = df.index.tz_convert('Europe/Rome')
        df.index = df.index.strftime('%Y-%m-%d %H:%M')  

    if limit == 1:
        if update_last_bar_task is not None:
            update_last_bar_task.cancel()
        if type:
            update_bars(df, limit)
        else:      
            update_last_bar_task = asyncio.create_task(update_last_bar(df, symbol, timeframe, limit, chart))
    else:
        update_bars(df, limit)

def fetch_data_from_binance(symbol, timeframe, limit):
    if timeframe != "2m":
        try:
            exchange = ccxt.binance()
            data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            order_data(data, True, limit) 
        except Exception as e:
            print(f"An error occurred with binance: {e}")
            return None
    else:
        return None

def fetch_data_from_yf(symbol, timeframe, limit, chart):
    if timeframe != '3m':
        try:
            stock = yf.Ticker(symbol)
            data = stock.history(period='5d', interval=timeframe, prepost=False)
            order_data(data, False, limit, symbol, timeframe, chart)
        except Exception as e:
            print(f"An error occurred with yahoofinance: {e}")
            return None
    else:
        return None

def get_all_crypto_symbols():
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    
    popular_symbols = {
        'BTC/USDT': 1,
        'ETH/USDT': 2,
        'BNB/USDT': 3,
        'XRP/USDT': 4,
        'ADA/USDT': 5,
        'SOL/USDT': 6,
        'DOGE/USDT': 7,
        'MATIC/USDT': 8,
        'DOT/USDT': 9,
        'LINK/USDT': 10,
    }
    
    all_symbols = [market for market in markets if '/' in market]
    normalized_symbols = set(symbol.upper() for symbol in all_symbols)
    
    def get_priority(symbol):
        return popular_symbols.get(symbol, float('inf'))

    prioritized_symbols = sorted(
        normalized_symbols,
        key=get_priority
    )
    
    return prioritized_symbols

def get_market_calendar(symbol):
    try:
        if symbol.endswith('.L'):
            return mcal.get_calendar('LSE')
        elif symbol.endswith('.PA'):
            return mcal.get_calendar('Euronext')
        elif symbol.endswith('.DE'):
            return mcal.get_calendar('XETR')
        elif symbol.endswith('.MI'):
            return mcal.get_calendar('XMIL')
        elif symbol.isupper():
            return mcal.get_calendar('NYSE')
        elif symbol.endswith('.SS'):
            return mcal.get_calendar('SSE')
        elif symbol.endswith('.SZ'):
            return mcal.get_calendar('SZSE')
        elif symbol.endswith('.BO'):
            return mcal.get_calendar('NSE')
        elif symbol.endswith('.HK'):
            return mcal.get_calendar('HKEX')
        elif symbol.endswith('.AX'):
            return mcal.get_calendar('ASX')
        elif symbol.endswith('.TO'):
            return mcal.get_calendar('TSX')
        else:
            return None
    except Exception as e:
        print(f"An error occurred in get_market_calendar: {e}")

def send_telegram_message(message, send_photo=False):
    bot_token = 'your_bot_token'
    chat_id = 'your_chat_id'
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    
    if send_photo:
        url = f'https://api.telegram.org/bot{bot_token}/sendPhoto'
        screenshot_path = os.path.join("screenshots", "screenshot.png")
        os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
        screenshot_data = global_vars.chart.screenshot()
        
        with open(screenshot_path, "wb") as f:
            f.write(screenshot_data)
        
        try:
            with open(screenshot_path, 'rb') as image_file:
                response = requests.post(url, data={'chat_id': chat_id, 'caption': message}, files={'photo': image_file})
                response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while sending message and image: {e}")
    else:
        try:
            response = requests.post(url, data={'chat_id': chat_id, 'text': message})
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while sending message: {e}")
