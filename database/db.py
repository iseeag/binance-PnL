import os
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime, timedelta
from utils.calculations import to_float

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.environ['PGHOST'],
            database=os.environ['PGDATABASE'],
            user=os.environ['PGUSER'],
            password=os.environ['PGPASSWORD'],
            port=os.environ['PGPORT']
        )
        self._create_tables()

    def _create_tables(self):
        with self.conn.cursor() as cur:
            # User config table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_config (
                    id SERIAL PRIMARY KEY,
                    api_key VARCHAR(255),
                    api_secret VARCHAR(255),
                    api_name VARCHAR(50) DEFAULT 'default',
                    total_investment DECIMAL,
                    session_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Balance history table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS balance_history (
                    id SERIAL PRIMARY KEY,
                    spot_value DECIMAL NOT NULL DEFAULT 0,
                    futures_value DECIMAL NOT NULL DEFAULT 0,
                    coin_futures_value DECIMAL NOT NULL DEFAULT 0,
                    cross_margin_value DECIMAL NOT NULL DEFAULT 0,
                    isolated_margin_value DECIMAL NOT NULL DEFAULT 0,
                    total_value DECIMAL NOT NULL,
                    wallet_type VARCHAR(20) DEFAULT 'spot',
                    session_id VARCHAR(255),
                    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            ''')
            
            # Create indexes for better performance
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_config_session_api 
                ON user_config(session_id, api_name);
                
                CREATE INDEX IF NOT EXISTS idx_balance_history_session_type 
                ON balance_history(session_id, wallet_type);
            ''')
        self.conn.commit()

    def save_config(self, api_key, api_secret, total_investment, session_id, api_name='default'):
        """Save user configuration with session_id and api_name"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_config (api_key, api_secret, total_investment, session_id, api_name)
                    VALUES (%s, %s, %s, %s, %s)
                """, (api_key, api_secret, total_investment, session_id, api_name))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"保存配置失败: {str(e)}")

    def get_latest_config(self, session_id, api_name='default'):
        """Get specific API configuration for a session"""
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT * FROM user_config 
                    WHERE session_id = %s AND api_name = %s
                """, (session_id, api_name))
                return cur.fetchone()
        except Exception as e:
            raise Exception(f"获取配置失败: {str(e)}")
            
    def get_all_configs(self, session_id):
        """Get all API configurations for a session"""
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT * FROM user_config 
                    WHERE session_id = %s
                    ORDER BY api_name
                """, (session_id,))
                return cur.fetchall()
        except Exception as e:
            raise Exception(f"获取配置失败: {str(e)}")

    def clear_config(self, session_id):
        """Clear user configurations and balance history for a specific session"""
        try:
            with self.conn.cursor() as cur:
                # Clear user config for the session
                cur.execute("DELETE FROM user_config WHERE session_id = %s", (session_id,))
                # Clear balance history for the session
                cur.execute("DELETE FROM balance_history WHERE session_id = %s", (session_id,))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"清除配置失败: {str(e)}")

    def save_balance_history(self, wallet_values, session_id, wallet_type='spot', api_name='default'):
        """
        Save balance history with support for multiple wallet types
        wallet_values: dict containing values for different wallet types
        """
        try:
            # Ensure all values are properly converted to float
            spot_value = to_float(wallet_values.get('spot', 0))
            futures_value = to_float(wallet_values.get('futures', 0))
            coin_futures_value = to_float(wallet_values.get('coin_futures', 0))
            cross_margin_value = to_float(wallet_values.get('cross_margin', 0))
            isolated_margin_value = to_float(wallet_values.get('isolated_margin', 0))
            
            total_value = sum([
                spot_value, futures_value, coin_futures_value,
                cross_margin_value, isolated_margin_value
            ])
            
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO balance_history 
                    (spot_value, futures_value, coin_futures_value, cross_margin_value, 
                     isolated_margin_value, total_value, wallet_type, session_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    spot_value, futures_value, coin_futures_value,
                    cross_margin_value, isolated_margin_value,
                    total_value, wallet_type, session_id
                ))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving balance history: {str(e)}")
            self.conn.rollback()
            raise

    def get_balance_history(self, session_id, hours=None):
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                query = """
                    SELECT 
                        COALESCE(spot_value, 0) as spot_value,
                        COALESCE(futures_value, 0) as futures_value,
                        COALESCE(coin_futures_value, 0) as coin_futures_value,
                        COALESCE(total_value, 0) as total_value,
                        recorded_at AT TIME ZONE 'UTC' as recorded_at
                    FROM balance_history 
                    WHERE session_id = %s
                """
                
                if hours:
                    query += " AND recorded_at >= NOW() - interval '%s hours'"
                    cur.execute(query + " ORDER BY recorded_at ASC", (session_id, hours))
                else:
                    cur.execute(query + " ORDER BY recorded_at ASC", (session_id,))
                
                result = cur.fetchall()
                if not result:
                    return []
                
                formatted_result = []
                for row in result:
                    row_dict = dict(row)
                    if row_dict['recorded_at'] and isinstance(row_dict['recorded_at'], datetime):
                        # Convert decimal values to float
                        row_dict['spot_value'] = to_float(row_dict['spot_value'])
                        row_dict['futures_value'] = to_float(row_dict['futures_value'])
                        row_dict['coin_futures_value'] = to_float(row_dict['coin_futures_value'])
                        row_dict['total_value'] = to_float(row_dict['total_value'])
                        formatted_result.append(row_dict)
                    else:
                        print(f"Invalid timestamp format: {row_dict['recorded_at']}")
                        continue
                
                return formatted_result

        except Exception as e:
            print(f"Error retrieving balance history: {str(e)}")
            return []
