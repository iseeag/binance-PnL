import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.calculations import to_float, calculate_profit_rate
from datetime import datetime
import pytz

def render_profit_charts(total_value, config, balance_history):
    st.header("📈 收益趋势分析")
    
    try:
        # Data validation
        if not balance_history or len(balance_history) == 0:
            st.info("暂无历史数据，随着时间推移将会显示资产趋势图")
            return

        # Validate data structure
        required_columns = [
            'spot_value', 'futures_value', 'coin_futures_value',
            'cross_margin_value', 'isolated_margin_value',
            'total_value', 'recorded_at'
        ]
        if not all(isinstance(entry, dict) for entry in balance_history):
            st.error("数据格式错误：历史数据格式不正确")
            return
        
        missing_columns = [col for col in required_columns if not all(col in entry for entry in balance_history)]
        if missing_columns:
            print(f"Missing columns in balance history: {missing_columns}")
            # Initialize missing columns with 0
            for entry in balance_history:
                for col in missing_columns:
                    entry[col] = 0.0

        # Convert to DataFrame with proper timestamp handling
        df = pd.DataFrame(balance_history)
        
        # Ensure recorded_at is datetime
        if not pd.api.types.is_datetime64_any_dtype(df['recorded_at']):
            try:
                df['recorded_at'] = pd.to_datetime(df['recorded_at'], utc=True)
            except Exception as e:
                st.error(f"时间戳转换错误: {str(e)}")
                return
        
        # Convert numeric columns with validation
        numeric_columns = [
            'spot_value', 'futures_value', 'coin_futures_value',
            'cross_margin_value', 'isolated_margin_value', 'total_value'
        ]
        for col in numeric_columns:
            try:
                df[col] = df[col].apply(lambda x: to_float(x) if x is not None else 0.0)
            except Exception as e:
                st.error(f"数值转换错误 ({col}): {str(e)}")
                print(f"Error converting {col}: {str(e)}")
                return

        # 获取并验证total_investment
        try:
            total_investment = config.get('total_investment')
            if total_investment is None:
                st.warning("未设置初始投资金额，请先在设置页面填写投资金额")
                return
            total_investment = to_float(total_investment)
            if total_investment <= 0:
                st.warning("初始投资金额必须大于0")
                return
        except Exception as e:
            st.error(f"投资金额计算错误: {str(e)}")
            return
            
        # 计算profit rate前确保数值有效
        df['profit_rate'] = df.apply(
            lambda row: calculate_profit_rate(row['total_value'], total_investment), 
            axis=1
        )
        
        # Create trend chart
        fig = go.Figure()
        
        # Add profit rate line with datetime handling
        fig.add_trace(go.Scatter(
            x=df['recorded_at'],
            y=df['profit_rate'],
            name="收益率",
            line=dict(color='rgba(100, 181, 246, 1)', width=2),
            hovertemplate='时间: %{x}<br>收益率: %{y:.2f}%<extra></extra>'
        ))
        
        # Update layout with proper time formatting
        fig.update_layout(
            xaxis_title='时间',
            yaxis_title='收益率 (%)',
            height=500,
            hovermode='x unified',
            showlegend=False,
            yaxis=dict(
                tickformat='.2f',
                ticksuffix='%',
                gridcolor='rgba(0,0,0,0.1)',
                zerolinecolor='rgba(0,0,0,0.2)'
            ),
            xaxis=dict(
                type='date',
                tickformat='%Y-%m-%d %H:%M',
                gridcolor='rgba(0,0,0,0.1)',
                tickangle=-45
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(t=20, b=40)
        )
        
        # Add gridlines
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display current profit rate with validation
        try:
            if total_value is not None:
                current_profit_rate = calculate_profit_rate(to_float(total_value), total_investment)
                st.metric("当前收益率", f"{current_profit_rate:.2f}%")
        except Exception as e:
            st.error(f"当前收益率计算错误: {str(e)}")
            
    except Exception as e:
        st.error(f"图表渲染错误: {str(e)}")
        print(f"Error details: {str(e)}")
