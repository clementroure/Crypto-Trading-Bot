# -*- coding: utf-8 -*-
"""Statistiaque d'Arbitrage.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/10o6LtMOtQB7YbzdPiCb2DFhuMYXerR_h

# Statistical arbitrage on cryptocurrencies
By Roure Clement, Rodrigues Thomas et Sirot Antoine

### In this project we have priced the 10 cryptocurrencies listed below in order to perform a statistical arbitrage on them in order to obtain a thoughtful trading algorithm:
"""

token_list = ['BTC', 'ETH', 'BNB', 'SOL', 'MATIC', 'SHIB', 'DOGE', 'ADA', 'ETC', 'AVAX']

"""All imports necessary for the project:"""

import requests
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels
import itertools
import seaborn as sns


from numpy import cumsum, log, polyfit, sqrt, std, subtract
from numpy.random import randn
from datetime import datetime
from pandas import json_normalize
from statsmodels.tsa.stattools import adfuller
import statsmodels.api as sm

"""First we needed to retrieve the prices of these 10 crypto-currencies over the last 4 months (500 values). For this we used the Binance API which allows us to retrieve all the prices without any problem. Then we stored them in a different json file for each cryptocurrency.

The function dataOfTokenPair uses the Binance API with a pair of crypto-currencies and a candle duration.

The implementFiles function calls the previous function and will enter the data into the files.
"""

def dataOfTokenPair(pair, duration):
    d = requests.get('https://data.binance.com/api/v3/klines?symbol='+pair+'&interval='+duration).json()    
    L2=[]
    L3=[]
    for i in range (len(d)):
        L2.append(datetime.fromtimestamp(d[i][0]/1000).strftime("%Y-%m-%d %I:%M:%S"))
        L2.append(d[i][1])
        L3.append(L2)
        L2=[]


    data = []
    for period in L3:
        time_period_start = period[0]
        price_open = float(period[1])

        time_period_start = time_period_start[:10] + ' ' + time_period_start[11:19]

        data.append({
            "time_period_start": time_period_start,
            "price_open": price_open
        })
    return data

def implementFiles():
    for token in token_list: # Run over the token list
        x = dataOfTokenPair(token +'USDT', '6h')
        with open('{}.json'.format(token), 'w') as outfile:
            json.dump(x, outfile)
            
implementFiles()

"""After that we created our DataFrame with all our values in order to be able to compare the evolution of the different cryptocurrencies:"""

datetime_index = pd.date_range('2023-02-09 08:00:00', '2023-02-05 04:00:00', freq='4H')
df = pd.DataFrame(index = datetime_index)

for token in token_list: # Run over the token list
    with open('{}.json'.format(token)) as json_data: 
        full_data = json_normalize(json.load(json_data)) 
        price_data = full_data['price_open']
        date = full_data['time_period_start']
        formatted_date = []
        for i in date: 
            formatted_date.append(pd.to_datetime(i[0:4] + '-' + i[5:7] + '-' + i[8:10] + ' ' + i[11:13] + ':00:00'))
        tokendf = pd.DataFrame(index = list(formatted_date)) 
        tokendf['{}'.format(token)] = price_data.values 
        df = pd.concat([df, tokendf], axis=1, sort=False) 
        

df.describe()

"""In order to better visualize our dataset we normalized the values and displayed the price curves of each cryptocurrency :"""

normalized_df=(df-df.min())/(df.max()-df.min()) 
normalized_df.plot(figsize=(25,12), title='Normalized Price Series between 2022-09-02 and 2023-01-05');

"""## Augmented Dickey-Fuller Test

In order to a better understanding of the cointegration we created a table with every cointegration using the Augmented Dickey-Fuller Test :
"""

t_results_table = pd.DataFrame(columns=token_list, index=token_list)
p_results_table = pd.DataFrame(columns=token_list, index=token_list) 

for row in token_list:
    for column in token_list:

        if row == column: 
            t_results_table[column][row] = np.nan
            p_results_table[column][row] = np.nan
            
        else: 
            regression = sm.OLS(df[row], sm.add_constant(df[column])).fit().params 
            residual = df[row]-regression[1]*df[column]-regression[0] 
            adf_results = adfuller(residual) 
            t_results_table[column][row] = adf_results[0] 
            p_results_table[column][row] = adf_results[1]

t_results_table.head(len(token_list))

""" We will now look for token pairs that have important cointegration and mean-reversion :"""

def tstat(cell):
    if cell < adf_results[4]['1%']:
        ret = 1
    elif cell < adf_results[4]['5%']:
        ret = 2
    else:
        ret = np.nan
    return ret

def convp(cell):
    if cell < 0.05:
        ret = 1
    else:
        ret = np.nan
    return ret

tstat_table = t_results_table.applymap(tstat)
pvalue_table = p_results_table.applymap(convp)

results_table = pd.DataFrame(tstat_table.values*pvalue_table.values, columns=tstat_table.columns, index=tstat_table.index)

fig = plt.figure(figsize=(12,7))
ax = sns.heatmap(results_table.values.astype(float), xticklabels = tstat_table.columns, yticklabels = tstat_table.columns, annot = True)

"""We can see that the pair with 2 has a result completed the Augmented Dickey-Fuller Test with a risk of 5% and those with 1 has completed it with 1% risk. These are the pairs that are most strongely cointegrated. From now on we have 14 combinaisons of pair possible.

## Hurst Exponent
"""

#Hurst Exponent
from numpy import cumsum, log, polyfit, sqrt, std, subtract
from numpy.random import randn

def hurst(ts):
    # Create the range of lag values
    lags = range(2, 100)

    # Calculate the array of the variances of the lagged differences
    tau = [sqrt(std(subtract(ts[lag:], ts[:-lag]))) for lag in lags]

    # Use a linear fit to estimate the Hurst Exponent
    poly = polyfit(log(lags), log(tau), 1)

    # Return the Hurst exponent from the polyfit output
    return poly[0]*2.0

Hurst_results_table = pd.DataFrame(columns=token_list, index=token_list)

for row in token_list:
    for column in token_list:
        if row == column:
            Hurst_results_table[column][row] = np.nan
        else:
            regression = sm.OLS(df[row], sm.add_constant(df[column])).fit().params    
            residual = df[row]-regression[1]*df[column]-regression[0]
            hurst_results = hurst(residual)
            Hurst_results_table[column][row] = hurst_results

fig = plt.figure(figsize=(12,7))
ax = sns.heatmap(Hurst_results_table.values.astype(float), xticklabels = Hurst_results_table.columns, yticklabels = Hurst_results_table.columns, annot = True)

"""## Interpretation :

Here the values ain't coherent because they are all really close to 0. This can be a problem in our algorithm but we tried other codes, ohter methods and nothings works. We let an example that we tried below.
"""

import itertools

# Initialize the results dataframe where we will store the Hurst exponents for each pair of tokens
hurst_results = pd.DataFrame(columns=token_list, index=token_list)

# Get every possible combination of tokens
combinations = list(itertools.combinations(df.columns, 2))

# Loop over the combinations
for row in combinations:
    # Calculate Hurst exponent for the pair of tokens
    hurst_exponent = hurst(df[list(row)].mean(axis=1))
    # Store the Hurst exponent in the results dataframe
    hurst_results.loc[row[0], row[1]] = hurst_exponent
    hurst_results.loc[row[1], row[0]] = hurst_exponent

# Print the results dataframe
print(hurst_results)

"""After working on this project we only had results from the Augmented Dickey-Fuller State so we will try to trade from the supossed cointegration gave by him. We will take 3 pairs with 99% or sucess which are : SOL/BTC, MATIC/SOL, DOGE/MATIC """

normalized_df=(df-df.min())/(df.max()-df.min()) 
subset_df = normalized_df.loc[:, ['SOL', 'BTC']]
subset_df.plot(figsize=(25,12), title = 'Prices of SOL and BTC');

normalized_df=(df-df.min())/(df.max()-df.min()) 
subset_df = normalized_df.loc[:, ['MATIC', 'SOL']]
subset_df.plot(figsize=(25,12), title = 'Prices of MATIC and SOL');

normalized_df=(df-df.min())/(df.max()-df.min()) 
subset_df = normalized_df.loc[:, ['DOGE', 'MATIC']]
subset_df.plot(figsize=(25,12), title = 'Prices of DOGE and MATIC')

"""These three pairs are mean reverting series so we will try to trade with them :"""

pip install cbpro

# TRADING - Coinabse Pro

import cbpro
import base64
import json
from time import sleep

key = '41c17b9fc24eb1620f2c840e2c96ad91'
secret = 'GlbLbVMpIaR96nXGOUAuNweQcPrsqd19gsyqvki+5WfpQRKhcEgGbcl0y284Qp4LjmMuMM9bjAtlgUZGSadTUQ=='
passphrase = '4ahxvl8cz2z'

# Initialisation
encoded = json.dumps(secret).encode()
b64secret = base64.b64encode(encoded)
client = cbpro.AuthenticatedClient(key=key, b64secret=secret, passphrase=passphrase, api_url="https://api-public.sandbox.pro.coinbase.com/")
c = cbpro.PublicClient()

def open_trade():
  try: 
    if sol < btc:
      try:
          # get current price of BTC-USD
          limit = c.get_product_ticker(product_id='BTC-USD')
      except Exception as e:
          print(f'Error obtaining ticker data: {e}')
          return

      buy_order = client.buy(product_id='SOL-USD', order_type="market", size=sol_amount)
      # sell_order = client.place_limit_order(product_id='BTC-USD', 
      #              side='sell', 
      #              price=float(limit['price']), 
      #              size= btc_amount)
      btcShorting = True

    # sol > btc
    else: 
      try:
          # get current price of SOL-USD
          limit = c.get_product_ticker(product_id='SOL-USD')
      except Exception as e:
          print(f'Error obtaining ticker data: {e}')
          return

      buy_order = client.buy(product_id='BTC-USD', order_type="market", size=btc_amount)
      # sell_order = client.place_limit_order(product_id='SOL-USD', 
      #              side='sell', 
      #              price=float(limit['price']), 
      #              size= sol_amount)
      btcShorting = False

  except Exception as e:
      print(f'Error placing order: {e}')
      return

  # wait for confirmation
  sleep(2)
  print(buy_order)

  try:
      check = buy_order['id']
      check_order = client.get_order(order_id=check)
  except Exception as e:
      print(f'Unable to check order. It might be rejected. {e}')
      return

  if check_order['status'] == 'done':
      print('Order placed successfully')
      print(check_order)
      # we are in a trade now
      isTrading = True
  else:
      print('Order was not matched')
      return

def close_trade():
  if btcShorting:
    # close sol long trade
    buy_order = client.sell(product_id='SOL-USD', order_type="market", size=sol_amount)
    # close btc short trade
    # sell_order = ?
  else:
    # close btc long trade
    buy_order = client.sell(product_id='BTC-USD', order_type="market", size=sol_amount)
    # close sol short trade
    # sell_order = ?

  # wait for confirmation
  sleep(2)
  print(buy_order)
  
  try:
      check = buy_order['id']
      check_order = client.get_order(order_id=check)
  except Exception as e:
      print(f'Unable to check order. It might be rejected. {e}')
  
  if check_order['status'] == 'done':
      print('Order placed successfully')
      print(check_order)
      # Trade closed successfully !
      isTrading = False
  else:
      print('WARNING: Order was not matched. Trades are still open !')
    

# Laisser l'algo tourner
# // Nous n'arrivons pas ?? effectuer d'ordre de short avec l'API de Coinbase Pro car il faut un compte de trading sp??cial pour les futures

# Main loop:
while True:

  # get latest data
  normalized_df=(df-df.min())/(df.max()-df.min()) 
  sol = normalized_df.loc[:, ['SOL']].iloc[-1].values[0]
  btc = normalized_df.loc[:, ['BTC']].iloc[-1].values[0]
  diff = abs(sol - btc)

  btc_amount = 0.001
  sol_amount = 1

  isTrading = False # Do we have an active trade ?
  btcShorting = False # If the trade is active: Are we longing or shorting the btc ?
  refresh_time = 3600 # In seconds

  print("SOL: " + str(round(sol,3)))
  print("BTC: " + str(round(btc,3)))
  print()

  if isTrading == False:
    # trigger treshold to open a trade
    if diff > 0.05:
      # open long + short trades
      open_trade()
    else:
       print("Conditions are not met to open a trade. Keep waiting...")
  else:
    # sol curve and btc curve touch or almost touch each others 
    # => Stop our trades and take profits !
    if diff < 0.001:
      close_trade()
    else:
      print("Conditions are not met to close our trade. Keep waiting...")

  sleep(refresh_time) # Refresh data after a certain time

"""We can't place short orders on Coinbase Pro because we don't have a special Coinbase Futures account and the free api is restricted. 


The bot just place the long order when the 2 normalized prices difference is greater than the defined treshold. And it closes the trade when the normalized  price become equal again.

The bot will buy the cryptocurrency with the lowest normalized price on the Spot market.
"""

# Cancel order -> Emergency quit
client.cancel_order(order_id = "trade-id")