import streamlit as st
import pandas as pd
from binance.exceptions import BinanceAPIException
from services.binance_service import BinanceService
from utils.calculations import calculate_profit_rate, format_currency, format_percentage, to_float

def check_api_permissions(binance_service):
    """检查API权限"""
    st.info("正在验证API权限...")
    try:
        # 尝试获取账户信息来验证API权限
        binance_service.client.get_account()
        st.success("✅ API验证成功")
        return True
    except BinanceAPIException as e:
        error_messages = {
            -2015: """
            ### 🚫 API权限验证失败
            
            #### 可能的原因：
            1. **API密钥无效**：密钥可能已过期或被删除
            2. **权限不足**：API未启用必要的权限
            3. **IP限制**：当前IP地址未被允许访问
            
            #### 解决步骤：
            1. 访问[币安API管理页面](https://www.binance.com/cn/my/settings/api-management)
            2. 确保以下权限已启用：
               - ✓ 允许读取账户信息
               - ✓ 允许读取现货和合约数据
            3. 检查IP限制设置：
               - 移除特定IP限制或
               - 添加当前IP到白名单
            
            #### 建议操作：
            1. 如果以上设置正确但仍然失败，建议：
               - 重新生成API密钥
               - 仔细复制新的密钥信息
               - 更新应用设置
            """,
            -1021: "请求超时，正在重试...",
            -1022: "API签名无效，请检查密钥设置",
            -1102: "无效的参数，请联系技术支持"
        }
        st.error(error_messages.get(e.code, f"币安API错误 (代码: {e.code})\n\n{e.message}"))
        
        # 显示操作按钮
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚙️ 前往设置", use_container_width=True, key="goto_settings"):
                st.session_state.current_tab = "⚙️ 设置"
                st.rerun()
        with col2:
            st.button("🔄 重新验证", use_container_width=True, key="revalidate_api", on_click=st.rerun)
        
        return False
    except Exception as e:
        st.error(f"""
        ### ❌ API连接错误
        
        #### 错误信息：
        {str(e)}
        
        #### 建议操作：
        1. 检查网络连接
        2. 确认币安服务器可访问
        3. 如果问题持续，请尝试：
           - 清除浏览器缓存
           - 使用不同的网络连接
           - 联系技术支持
        """)
        st.button("🔄 重试", key="retry_wallet", on_click=st.rerun)
        return False

def render_wallet_display(binance_service, config):
    st.header("💰 钱包概览")
    
    # API状态指示器
    with st.status("正在连接币安API...", expanded=True) as status:
        # 首先检查API权限
        if not check_api_permissions(binance_service):
            status.error("API验证失败")
            return
        
        status.update(label="正在获取钱包数据...", state="running")
        
        try:
            # 获取余额信息
            with st.spinner("获取余额信息..."):
                spot_balances = binance_service.get_spot_balance()
                futures_balances = binance_service.get_futures_balance()
            
            with st.spinner("获取价格数据..."):
                prices = binance_service.get_current_prices([])
            
            # 计算总值
            spot_value = binance_service.calculate_total_value(spot_balances, prices)
            futures_value = float(futures_balances[futures_balances['asset'] == 'USDT']['balance'].iloc[0])
            total_value = to_float(spot_value) + to_float(futures_value)
            
            status.update(label="✅ 数据获取成功", state="complete")
            
            # 显示数据
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "初始投资",
                    format_currency(config['total_investment']),
                    ""
                )
                
            with col2:
                profit_rate = calculate_profit_rate(total_value, config['total_investment'])
                st.metric(
                    "当前总资产",
                    format_currency(total_value),
                    format_percentage(profit_rate)
                )
            
            # 添加刷新按钮
            st.button("🔄 刷新数据", key="refresh_wallet", on_click=st.rerun)
                
        except BinanceAPIException as e:
            status.error("获取数据失败")
            error_messages = {
                -2015: "API密钥无效或权限不足",
                -1021: "请求超时，请稍后重试",
                -1022: "签名无效，请检查API设置",
                -1102: "参数错误，请联系技术支持"
            }
            
            error_msg = error_messages.get(e.code, f"币安API错误 (代码: {e.code})")
            st.error(f"""
            ### ❌ {error_msg}
            
            #### 详细信息：
            {e.message}
            
            #### 建议操作：
            1. 检查API密钥设置
            2. 确认API权限配置
            3. 如果问题持续：
               - 尝试重新生成API密钥
               - 更新应用设置
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                st.button("⚙️ 更新设置", key="goto_settings_error", use_container_width=True, 
                         on_click=lambda: st.session_state.update({"current_tab": "⚙️ 设置"}))
            with col2:
                st.button("🔄 重新加载", key="reload_wallet", use_container_width=True, on_click=st.rerun)
            
        except Exception as e:
            status.error("系统错误")
            st.error(f"""
            ### ❌ 系统错误
            
            #### 错误信息：
            {str(e)}
            
            #### 建议操作：
            1. 刷新页面重试
            2. 检查网络连接
            3. 如果问题持续：
               - 清除浏览器缓存
               - 使用不同的网络连接
               - 联系技术支持
            """)
            st.button("🔄 重试", key="retry_wallet_error", on_click=st.rerun)
