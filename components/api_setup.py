import streamlit as st
from database.db import Database
from binance.client import Client
from binance.exceptions import BinanceAPIException

def validate_api_keys(api_key, api_secret):
    """验证API密钥有效性"""
    if not api_key or not api_secret:
        return False, "API密钥和密钥不能为空"

    try:
        client = Client(api_key, api_secret)
        # 测试API连接并检查权限
        account = client.get_account()
        futures_account = client.futures_account_balance()
        return True, "API验证成功"
    except BinanceAPIException as e:
        error_messages = {
            -2015: "API密钥无效或权限不足，请确保已启用读取权限",
            -1022: "API签名无效，请检查密钥是否正确",
            -1102: "必需参数无效，请重新检查输入",
            -2014: "服务器拒绝访问，请检查IP白名单设置",
            -1021: "请求超时，请检查网络连接"
        }
        return False, error_messages.get(e.code, f"API错误 ({e.code}): {e.message}")
    except Exception as e:
        return False, f"连接错误: {str(e)}"

def validate_investment_amount(amount):
    """验证投资金额"""
    if amount is None:
        return False, "投资金额不能为空"
    try:
        amount = float(amount)
        if amount < 0:
            return False, "投资金额不能为负数"
        if amount > 1000000000:
            return False, "投资金额不能超过10亿"
        return True, None
    except ValueError:
        return False, "请输入有效的数字"

def render_api_setup(session_id):
    st.header("⚙️ API设置")

    # 添加API设置说明
    with st.expander("📖 使用说明", expanded=False):
        st.markdown("""
        ### 获取币安API密钥的步骤：
        1. 登录您的币安账户
        2. 进入 [API管理页面](https://www.binance.com/cn/my/settings/api-management)
        3. 点击"创建API"按钮
        4. 完成安全验证
        5. 设置API权限：
           - ✓ 只启用读取权限（重要！其他权限请勿开启）
           - ✓ 确保现货和合约交易的读取权限已启用
        6. 复制并保存好API密钥和密钥

        ### 📢 重要提示：
        - 请勿泄露您的API密钥
        - 建议定期更新API密钥以确保安全
        - 如遇问题，请检查网络连接或尝试重新生成API密钥
        """)

    db = Database()
    config = None

    try:
        config = db.get_latest_config(session_id)
    except Exception as e:
        st.warning("""
        ### ⚠️ 无法连接数据库
        
        请检查：
        1. 数据库服务是否正常运行
        2. 网络连接是否稳定
        
        您可以：
        - 刷新页面重试
        - 重新启动应用
        - 联系技术支持
        """)

    # 添加重置按钮
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 重置设置", use_container_width=True, help="清除所有现有配置和历史数据，重新开始设置"):
            try:
                db.clear_config(session_id)
                st.success("""
                ### ✅ 重置成功！
                
                所有配置和历史数据已清除。
                """)
                st.rerun()
            except Exception as e:
                st.error(f"""
                ### ❌ 重置失败
                
                错误信息：{str(e)}
                
                请尝试：
                1. 刷新页面
                2. 检查数据库连接
                3. 联系技术支持
                """)

    with st.form("api_setup_form", clear_on_submit=False):
        # API密钥输入
        st.subheader("API配置", divider="gray")
        api_key = st.text_input(
            "API Key",
            type="password",
            value=config['api_key'] if config else "",
            help="请输入您的币安API Key，注意保护密钥安全"
        )
        
        api_secret = st.text_input(
            "API Secret",
            type="password",
            value=config['api_secret'] if config else "",
            help="请输入您的币安API Secret，注意保护密钥安全"
        )

        # 投资金额输入
        st.subheader("投资配置", divider="gray")
        try:
            default_investment = float(config['total_investment']) if config and config['total_investment'] else 0.0
        except (TypeError, ValueError, KeyError):
            default_investment = 0.0

        total_investment = st.number_input(
            "初始投资金额 (USDT)",
            value=default_investment,
            min_value=0.0,
            help="请输入您的总初始投资金额（现货+合约）",
            format="%.2f"
        )

        submitted = st.form_submit_button("保存设置", use_container_width=True)
        
        if submitted:
            with st.status("正在验证设置...", expanded=True) as status:
                # 验证API密钥
                api_valid, api_message = validate_api_keys(api_key, api_secret)
                if not api_valid:
                    status.error("API验证失败")
                    st.error(f"""
                    ### ❌ API验证错误
                    
                    {api_message}
                    
                    请检查：
                    1. API密钥是否正确
                    2. API权限是否配置正确
                    3. 网络连接是否正常
                    """)
                    return

                # 验证投资金额
                amount_valid, amount_message = validate_investment_amount(total_investment)
                if not amount_valid:
                    status.error("金额验证失败")
                    st.error(f"""
                    ### ❌ 投资金额错误
                    
                    {amount_message}
                    
                    请输入有效的投资金额。
                    """)
                    return

                # 保存设置
                try:
                    db.save_config(api_key, api_secret, total_investment, session_id)
                    status.update(label="✅ 设置保存成功！", state="complete")
                    st.success("""
                    ### ✅ 配置更新成功！
                    
                    系统将在3秒后自动刷新...
                    """)
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    status.error("保存失败")
                    st.error(f"""
                    ### ❌ 数据库错误
                    
                    错误信息：{str(e)}
                    
                    请检查：
                    1. 数据库连接是否正常
                    2. 输入数据是否有效
                    
                    建议操作：
                    - 刷新页面重试
                    - 检查网络连接
                    - 联系技术支持
                    """)
