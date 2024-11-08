from binance.client import Client
import pandas as pd
from datetime import datetime

class BinanceService:
    def __init__(self, api_key, api_secret):
        self.client = Client(api_key, api_secret)

    def get_spot_balance(self):
        account = self.client.get_account()
        balances = pd.DataFrame(account['balances'])
        balances['free'] = pd.to_numeric(balances['free'])
        balances['locked'] = pd.to_numeric(balances['locked'])
        balances['total'] = balances['free'] + balances['locked']
        return balances[balances['total'] > 0]

    def get_futures_balance(self):
        futures_account = self.client.futures_account_balance()
        return pd.DataFrame(futures_account)

    def get_current_prices(self, symbols):
        prices = self.client.get_symbol_ticker()
        return {item['symbol']: float(item['price']) for item in prices}

    def calculate_total_value(self, balances, prices):
        total_usdt = 0
        for _, balance in balances.iterrows():
            symbol = balance['asset']
            if symbol == 'USDT':
                total_usdt += float(balance['total'])
            else:
                symbol_pair = f"{symbol}USDT"
                if symbol_pair in prices:
                    total_usdt += float(balance['total']) * prices[symbol_pair]
        return total_usdt
