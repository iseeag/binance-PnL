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
            if st.button("⚙️ 前往设置", use_container_width=True, key="goto_settings_error"):
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
    """Display wallet information for multiple APIs"""
    api_name = config.get('api_name', 'default')
    
    # API状态指示器
    with st.status(f"正在连接币安API ({api_name})...", expanded=True) as status:
        # 首先检查API权限
        try:
            if not check_api_permissions(binance_service):
                status.error(f"API '{api_name}' 验证失败")
                # Don't return, show retry options
                st.error(f"""
                ### ❌ API '{api_name}' 验证失败
                
                此API可能无法正常工作。您可以：
                1. 检查API设置
                2. 重新验证连接
                3. 暂时忽略此API继续使用其他API
                """)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("⚙️ 检查设置", key=f"check_settings_{api_name}", use_container_width=True):
                        st.session_state.current_tab = "⚙️ 设置"
                        st.rerun()
                with col2:
                    if st.button("🔄 重新验证", key=f"revalidate_{api_name}", use_container_width=True):
                        st.rerun()
                with col3:
                    if st.button("⏭️ 继续", key=f"continue_{api_name}", use_container_width=True):
                        return
                return
        except Exception as e:
            status.error(f"API '{api_name}' 验证过程出错")
            st.error(f"验证过程发生错误: {str(e)}")
            return
        
        status.update(label="正在获取钱包数据...", state="running")
        
        try:
            # 获取所有钱包价值
            with st.spinner("获取钱包数据..."):
                wallet_values = binance_service.get_all_wallet_values()
            
            # 计算总值
            spot_value = to_float(wallet_values.get('spot', 0))
            futures_value = to_float(wallet_values.get('futures', 0))
            coin_futures_value = to_float(wallet_values.get('coin_futures', 0))
            cross_margin_value = to_float(wallet_values.get('cross_margin', 0))
            isolated_margin_value = to_float(wallet_values.get('isolated_margin', 0))
            total_value = sum([spot_value, futures_value, coin_futures_value, 
                             cross_margin_value, isolated_margin_value])
            
            status.update(label="✅ 数据获取成功", state="complete")
            
            # 计算收益
            initial_investment = to_float(config['total_investment'])
            profit_amount = total_value - initial_investment
            profit_rate = calculate_profit_rate(total_value, initial_investment)

            # 显示数据
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "初始投资",
                    format_currency(initial_investment)
                )
            with col2:
                st.metric(
                    "当前总资产",
                    format_currency(total_value)
                )
            with col3:
                st.metric(
                    "收益",
                    format_currency(profit_amount)
                )
            with col4:
                st.metric(
                    "收益率",
                    format_percentage(profit_rate)
                )
            
            # 添加分割线增强视觉层次
            st.divider()
            
            # 显示资产分布
            dist_col1, dist_col2, dist_col3, dist_col4, dist_col5 = st.columns(5)
            
            with dist_col1:
                st.metric("现货", format_currency(spot_value))
            
            with dist_col2:
                st.metric("U本位合约", format_currency(futures_value))
            
            with dist_col3:
                st.metric("币本位合约", format_currency(coin_futures_value))
            
            with dist_col4:
                st.metric("全仓杠杆", format_currency(cross_margin_value))
            
            with dist_col5:
                st.metric("逐仓杠杆", format_currency(isolated_margin_value))
            
            # 刷新按钮已移除
                
        except BinanceAPIException as e:
            status.error("获取数据失败")
            error_messages = {
                -2015: f"API '{config.get('api_name', 'default')}' 密钥无效或权限不足",
                -1021: f"API '{config.get('api_name', 'default')}' 请求超时，请稍后重试",
                -1022: f"API '{config.get('api_name', 'default')}' 签名无效，请检查设置",
                -1102: f"API '{config.get('api_name', 'default')}' 参数错误，请联系技术支持"
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
