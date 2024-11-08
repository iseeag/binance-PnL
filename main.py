import streamlit as st
import uuid
from database.db import Database
from services.binance_service import BinanceService
from components.api_setup import render_api_setup
from components.wallet_display import render_wallet_display
from components.charts import render_profit_charts

st.set_page_config(
    page_title="币安钱包追踪器",
    page_icon="💰",
    layout="wide"
)

def initialize_session():
    """Initialize or get existing session ID"""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    return st.session_state.session_id

def main():
    st.title("币安钱包追踪器 🚀")
    
    # Initialize database connection
    try:
        db = Database()
    except Exception as e:
        st.error("数据库连接失败")
        return
        
    # Initialize session
    session_id = initialize_session()
    
    config = None
    try:
        config = db.get_latest_config(session_id)
    except Exception as e:
        st.error(f"无法连接数据库：{str(e)}")
    
    # Create tabs
    tab1, tab2 = st.tabs(["📊 资产概览", "⚙️ 设置"])
    
    with tab2:
        render_api_setup(session_id)
    
    with tab1:
        if not config:
            st.warning("请先设置API密钥和初始投资金额")
            return
            
        try:
            binance_service = BinanceService(config['api_key'], config['api_secret'])
            
            # Add refresh button
            if st.button("🔄 刷新数据"):
                st.rerun()
            
            # Display wallet information
            render_wallet_display(binance_service, config)
            
            # Get latest data for charts
            try:
                spot_balances = binance_service.get_spot_balance()
                futures_balances = binance_service.get_futures_balance()
                prices = binance_service.get_current_prices([])
                
                spot_value = binance_service.calculate_total_value(spot_balances, prices)
                futures_value = float(futures_balances[futures_balances['asset'] == 'USDT']['balance'].iloc[0])
                
                # Save current balance to history
                try:
                    db.save_balance_history(spot_value, futures_value, session_id)
                    
                    # Get balance history and display charts
                    balance_history = db.get_balance_history(session_id)
                    render_profit_charts(spot_value, futures_value, config, balance_history)
                except Exception as e:
                    st.error(f"保存或获取历史数据失败：{str(e)}")
                    
            except Exception as e:
                st.error("获取账户数据失败，请检查API设置和网络连接")
                
        except Exception as e:
            st.error("API连接失败，请检查设置")
            return

if __name__ == "__main__":
    main()
