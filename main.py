import streamlit as st
import uuid
from database.db import Database
from services.binance_service import BinanceService
from components.api_setup import render_api_setup
from components.wallet_display import render_wallet_display
from binance.exceptions import BinanceAPIException
from utils.calculations import calculate_profit_rate, format_currency, format_percentage, to_float

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
    
    configs = None
    try:
        configs = db.get_all_configs(session_id)
    except Exception as e:
        st.error(f"无法连接数据库：{str(e)}")
    
    # Create tabs
    tab1, tab2 = st.tabs(["📊 资产概览", "⚙️ 设置"])
    
    with tab2:
        render_api_setup(session_id)
    
    with tab1:
        if not configs:
            st.warning("请先设置API密钥和初始投资金额")
            return
            
        try:
            # Initialize and calculate aggregated wallet values
            total_wallet_values = {
                'spot': 0.0,
                'futures': 0.0,
                'coin_futures': 0.0,
                'cross_margin': 0.0,
                'isolated_margin': 0.0
            }
            
            # Process each API configuration first to calculate totals
            for config in configs:
                try:
                    binance_service = BinanceService(config['api_key'], config['api_secret'])
                    wallet_values = binance_service.get_all_wallet_values()
                    
                    # Aggregate values
                    for wallet_type in total_wallet_values:
                        total_wallet_values[wallet_type] += float(wallet_values.get(wallet_type, 0))
                        
                    # Save individual API balance history
                    db.save_balance_history(wallet_values, session_id, api_name=config['api_name'])
                except Exception as e:
                    st.error(f"API '{config['api_name']}' 连接失败: {str(e)}")
                    continue
            
            # Add refresh button to top right
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🔄 刷新数据", key="refresh_all_data", use_container_width=True):
                    st.rerun()
            
            # Display aggregated total overview
            st.markdown("# 💰 总资产概览")
            st.divider()
            
            total_investment = sum(float(config['total_investment']) for config in configs)
            total_value = sum(float(value) for value in total_wallet_values.values())
            
            # Calculate profits
            total_profit_amount = total_value - total_investment
            total_profit_rate = calculate_profit_rate(total_value, total_investment)

            # Display in columns
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总初始投资", format_currency(total_investment))
            with col2:
                st.metric("总资产", format_currency(total_value))
            with col3:
                st.metric("总收益", format_currency(total_profit_amount))
            with col4:
                st.metric("总收益率", format_percentage(total_profit_rate))
            
            # Display wallet type distribution in a more compact format
            wallet_cols = st.columns(5)
            wallet_types = {
                "现货": 'spot',
                "U本位合约": 'futures',
                "币本位合约": 'coin_futures',
                "全仓杠杆": 'cross_margin',
                "逐仓杠杆": 'isolated_margin'
            }
            
            for i, (label, key) in enumerate(wallet_types.items()):
                with wallet_cols[i]:
                    st.metric(label, format_currency(total_wallet_values[key]))
            
            st.divider()
            
            # Display individual API wallets
            for config in configs:
                try:
                    binance_service = BinanceService(config['api_key'], config['api_secret'])
                    st.subheader(f"📊 {config['api_name']}")
                    render_wallet_display(binance_service, config)
                    st.divider()  # Add divider between API sections
                except BinanceAPIException as e:
                    error_messages = {
                        -2015: "API权限无效",
                        -1021: "请求超时",
                        -1022: "签名无效",
                        -1102: "参数错误"
                    }
                    error_msg = error_messages.get(e.code, f"币安API错误 (代码: {e.code})")
                    st.error(f"API '{config['api_name']}' 连接失败: {error_msg}\n{e.message}")
                except Exception as e:
                    st.error(f"API '{config['api_name']}' 连接失败: {str(e)}")
                    
        except Exception as e:
            st.error(f"获取API配置失败: {str(e)}")

if __name__ == "__main__":
    main()
