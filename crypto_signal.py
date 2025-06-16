import ccxt
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request, abort
import os

app = Flask(__name__)

SECRET_TOKEN = "u82Ds7BxrT2p4F9vKQy8FvPe"

def fetch_top_volume_pairs(limit=10):
    binance = ccxt.binance()
    tickers = binance.fetch_tickers()
    filtered = []

    for t in tickers.values():
        if 'symbol' in t and '/USDT' in t['symbol'] and isinstance(t.get('quoteVolume'), (int, float)):
            filtered.append(t)

    sorted_pairs = sorted(filtered, key=lambda x: x['quoteVolume'], reverse=True)
    return [t['symbol'] for t in sorted_pairs[:limit]]

def get_ema_bb_signals(pair):
    binance = ccxt.binance()
    ohlcv = binance.fetch_ohlcv(pair, timeframe='1h', limit=210)
    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])

    if len(df) < 201:
        return None

    df['ema200'] = df['close'].ewm(span=200).mean()
    df['bb_mid'] = df['close'].rolling(window=200).mean()
    df['bb_std'] = df['close'].rolling(window=200).std()
    df['bb_upper'] = df['bb_mid'] + (2 * df['bb_std'])
    df['bb_lower'] = df['bb_mid'] - (2 * df['bb_std'])

    last = df.iloc[-1]
    crossed_ema = (last['close'] > last['ema200']) != (df.iloc[-2]['close'] > df.iloc[-2]['ema200'])
    near_bb = last['close'] >= last['bb_upper'] or last['close'] <= last['bb_lower']

    if crossed_ema or near_bb:
        return {
            'pair': pair,
            'price': last['close'],
            'ema200': last['ema200'],
            'crossed_ema': crossed_ema,
            'near_bb': near_bb
        }
    return None

@app.route('/')
def check_signals():
    token = request.args.get('token')
    if token != SECRET_TOKEN:
        abort(401)

    results = []
    top_pairs = fetch_top_volume_pairs()
    for pair in top_pairs:
        try:
            result = get_ema_bb_signals(pair)
            if result:
                results.append(result)
        except Exception as e:
            print(f"Error processing {pair}: {e}")
    return jsonify(results)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
