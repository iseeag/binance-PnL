from binance.client import Client
import pandas as pd
from datetime import datetime

class BinanceService:
    def __init__(self, api_key, api_secret):
        self.client = Client(api_key, api_secret)

    def get_spot_balance(self):
        """获取现货账户余额"""
        account = self.client.get_account()
        balances = pd.DataFrame(account['balances'])
        balances['free'] = pd.to_numeric(balances['free'])
        balances['locked'] = pd.to_numeric(balances['locked'])
        balances['total'] = balances['free'] + balances['locked']
        return balances[balances['total'] > 0]

    def get_futures_balance(self):
        """获取U本位合约账户余额"""
        # Get account balance
        futures_account_balance = self.client.futures_account_balance()
        balance_df = pd.DataFrame(futures_account_balance)
        
        # Get futures account info including positions
        futures_account = self.client.futures_account()
        positions = futures_account['positions']
        
        # Calculate total unrealized profit
        total_unrealized_profit = sum(float(position['unrealizedProfit']) for position in positions)
        
        # Add unrealized profit to the balance dataframe
        if not balance_df.empty and 'balance' in balance_df.columns:
            balance_df.loc[balance_df['asset'] == 'USDT', 'balance'] = \
                float(balance_df.loc[balance_df['asset'] == 'USDT', 'balance'].iloc[0]) + total_unrealized_profit
            
        return balance_df

    def get_coin_futures_balance(self):
        """获取币本位合约账户余额"""
        coin_futures_account = self.client.futures_coin_account_balance()
        return pd.DataFrame(coin_futures_account)

    def get_cross_margin_balance(self):
        """获取全仓杠杆账户余额"""
        try:
            margin_account = self.client.get_margin_account()
            balances = pd.DataFrame(margin_account['userAssets'])
            balances['free'] = pd.to_numeric(balances['free'])
            balances['locked'] = pd.to_numeric(balances['locked'])
            balances['borrowed'] = pd.to_numeric(balances['borrowed'])
            balances['interest'] = pd.to_numeric(balances['interest'])
            balances['netAsset'] = pd.to_numeric(balances['netAsset'])
            return balances[balances['netAsset'] > 0]
        except Exception as e:
            print(f"获取全仓杠杆账户余额失败: {str(e)}")
            return pd.DataFrame()

    def get_isolated_margin_balance(self):
        """获取逐仓杠杆账户余额"""
        try:
            isolated_margin_accounts = self.client.get_isolated_margin_account()
            if not isinstance(isolated_margin_accounts, dict) or 'assets' not in isolated_margin_accounts:
                return pd.DataFrame()

            all_balances = []
            for account in isolated_margin_accounts['assets']:
                if account.get('enabled', False):  # 只处理已启用的账户
                    base_asset = account.get('baseAsset', {})
                    quote_asset = account.get('quoteAsset', {})
                    
                    # 计算基础资产净值
                    base_net_asset = float(base_asset.get('netAsset', 0))
                    if base_net_asset > 0:
                        symbol_pair = f"{base_asset.get('asset')}USDT"
                        try:
                            price = float(self.client.get_symbol_ticker(symbol=symbol_pair)['price'])
                            base_value = base_net_asset * price
                        except:
                            base_value = 0
                    else:
                        base_value = 0
                    
                    # 计算报价资产净值（如果是USDT则直接使用）
                    quote_net_asset = float(quote_asset.get('netAsset', 0))
                    quote_value = quote_net_asset if quote_asset.get('asset') == 'USDT' else 0
                    
                    total_value = base_value + quote_value
                    if total_value > 0:
                        all_balances.append({
                            'symbol': account.get('symbol', 'UNKNOWN'),
                            'netAsset': total_value
                        })

            return pd.DataFrame(all_balances)
        except Exception as e:
            print(f"获取逐仓杠杆账户余额失败: {str(e)}")
            return pd.DataFrame()

    def get_current_prices(self, symbols):
        """获取当前价格信息"""
        prices = self.client.get_symbol_ticker()
        return {item['symbol']: float(item['price']) for item in prices}

    def calculate_total_value(self, balances, prices, balance_type='spot'):
        """计算特定类型账户的总价值"""
        total_usdt = 0
        
        if balance_type == 'spot':
            for _, balance in balances.iterrows():
                symbol = balance['asset']
                if symbol == 'USDT':
                    total_usdt += float(balance['total'])
                else:
                    symbol_pair = f"{symbol}USDT"
                    if symbol_pair in prices:
                        total_usdt += float(balance['total']) * prices[symbol_pair]
                        
        elif balance_type == 'cross_margin':
            for _, balance in balances.iterrows():
                symbol = balance['asset']
                if symbol == 'USDT':
                    total_usdt += float(balance['netAsset'])
                else:
                    symbol_pair = f"{symbol}USDT"
                    if symbol_pair in prices:
                        total_usdt += float(balance['netAsset']) * prices[symbol_pair]
                        
        elif balance_type == 'isolated_margin':
            # 由于已经在get_isolated_margin_balance中转换为USDT，直接累加
            total_usdt = balances['netAsset'].sum() if not balances.empty else 0
                    
        elif balance_type in ['futures', 'coin_futures']:
            for _, balance in balances.iterrows():
                if balance['asset'] == 'USDT':
                    total_usdt += float(balance['balance'])
                else:
                    symbol_pair = f"{balance['asset']}USDT"
                    if symbol_pair in prices:
                        total_usdt += float(balance['balance']) * prices[symbol_pair]
                        
        return total_usdt

    def get_all_wallet_values(self):
        """获取所有钱包类型的价值"""
        try:
            prices = self.get_current_prices([])
            
            # 获取各类型账户余额
            spot_balances = self.get_spot_balance()
            futures_balances = self.get_futures_balance()
            coin_futures_balances = self.get_coin_futures_balance()
            cross_margin_balances = self.get_cross_margin_balance()
            isolated_margin_balances = self.get_isolated_margin_balance()
            
            # 计算各类型账户价值
            wallet_values = {
                'spot': self.calculate_total_value(spot_balances, prices, 'spot'),
                'futures': self.calculate_total_value(futures_balances, prices, 'futures'),
                'coin_futures': self.calculate_total_value(coin_futures_balances, prices, 'coin_futures'),
                'cross_margin': self.calculate_total_value(cross_margin_balances, prices, 'cross_margin'),
                'isolated_margin': self.calculate_total_value(isolated_margin_balances, prices, 'isolated_margin')
            }
            
            return wallet_values
        except Exception as e:
            print(f"获取钱包价值失败: {str(e)}")
            return {}
