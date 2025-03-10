'''
pandas ta review 
https://github.com/twopirllc/pandas-ta
'''

import panddas_ta as ta
import pandas as pd

data = pd.read_csv(
    '/Users/tc/Dropbox/dev/github/solana-sniper-course/ETH-USD1m30.csv')

# 1. Simple Moving Average (SMA)
data['SMA_10'] = ta.sma(data['close'], length=10)

# 2. Exponential Moving Average (EMA)
data['EMA_10'] = ta.ema(data['close'], length=10)

# 3. Relative Strength Index (RSI)
data['RSI_14'] = ta.rsi(data['close'], length=14)

# 5. Moving Average Convergence Divergence (MACD)
data[['MACD_line', 'MACD_signal', 'MACD_hist']] = ta.macd(data['close'],
                                                          fast=12,
                                                          slow=26,
                                                          signal=9)

# 6. Average True Range (ATR)
data['ATR_14'] = ta.atr(data['high'], data['low'], data['close'], length=14)

# 7. Stochastic Oscillator
data[['STOCH_k', 'STOCH_d']] = ta.stoch(data['high'],
                                        data['low'],
                                        data['close'],
                                        k=14,
                                        d=3)

# 8. Commodity Channel Index (CCI)
data['CCI_20'] = ta.cci(data['high'], data['low'], data['close'], length=20)

# 10. OBV (On-Balance Volume)
data['OBV'] = ta.obv(data['close'], data['volume'])

print(data)

# Help about this, 'ta', extension
help(data.ta)
