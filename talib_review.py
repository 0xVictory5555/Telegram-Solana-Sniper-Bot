'''
1st go over this one... TA-Lib... show how to get data in there then do it
talib docs - https://ta-lib.github.io/ta-lib-python/doc_index.html
https://ta-lib.github.io/ta-lib-python/func_groups/overlap_studies.html

'''

import talib as ta 
import pandas as pd


print('hey')
df = pd.read_csv('/Users/tc/Dropbox/dev/github/solana-sniper-course/ETH-USD1m30.csv')

data = pd.read_csv('/Users/tc/Dropbox/dev/github/solana-sniper-course/ETH-USD1m30.csv')

# sma
df['sma'] = ta.SMA(df['close'], timeperiod=20)

# rsi
df['rsi'] = ta.RSI(df['close'], timeperiod=14)

# 2. Exponential Moving Average (EMA)
data['EMA_10'] = ta.EMA(data['close'], timeperiod=10)

# 4. Bollinger Bands
data['BOLL_upper'], data['BOLL_mid'], data['BOLL_lower'] = ta.BBANDS(data['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)

# 5. Moving Average Convergence Divergence (MACD)
data['MACD_line'], data['MACD_signal'], data['MACD_hist'] = ta.MACD(data['close'], fastperiod=12, slowperiod=26, signalperiod=9)

# 6. Average True Range (ATR)
data['ATR_14'] = ta.ATR(data['high'], data['low'], data['close'], timeperiod=14)

# 7. Stochastic Oscillator
data['STOCH_k'], data['STOCH_d'] = ta.STOCH(data['high'], data['low'], data['close'], fastk_period=14, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)

# 8. Commodity Channel Index (CCI)
data['CCI_20'] = ta.CCI(data['high'], data['low'], data['close'], timeperiod=20)

# 9. Parabolic SAR
data['SAR'] = ta.SAR(data['high'], data['low'], acceleration=0.02, maximum=0.2)

# 10. OBV (On-Balance Volume)
data['OBV'] = ta.OBV(data['close'], data['volume'])

# bollinger bands 
df['upper'], df['middle'], df['lower'] = ta.BBANDS(df['close'], timeperiod=20)
print(df.tail(5))

print(data.tail(5))

