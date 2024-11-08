import os
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime, timedelta

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
                    total_investment DECIMAL,
                    session_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Balance history table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS balance_history (
                    id SERIAL PRIMARY KEY,
                    spot_value DECIMAL NOT NULL,
                    futures_value DECIMAL NOT NULL,
                    total_value DECIMAL NOT NULL,
                    session_id VARCHAR(255),
                    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            ''')
        self.conn.commit()

    def save_config(self, api_key, api_secret, total_investment, session_id):
        """Save user configuration with session_id"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_config (api_key, api_secret, total_investment, session_id)
                    VALUES (%s, %s, %s, %s)
                """, (api_key, api_secret, total_investment, session_id))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"保存配置失败: {str(e)}")

    def get_latest_config(self, session_id):
        """Get the latest user configuration for a specific session"""
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT * FROM user_config 
                    WHERE session_id = %s
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (session_id,))
                return cur.fetchone()
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

    def save_balance_history(self, spot_value, futures_value, session_id):
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO balance_history (spot_value, futures_value, total_value, session_id, recorded_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (spot_value, futures_value, spot_value + futures_value, session_id))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving balance history: {str(e)}")
            self.conn.rollback()

    def get_balance_history(self, session_id, hours=None):
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                query = """
                    SELECT 
                        COALESCE(spot_value, 0) as spot_value,
                        COALESCE(futures_value, 0) as futures_value,
                        COALESCE(total_value, 0) as total_value,
                        recorded_at AT TIME ZONE 'UTC' as recorded_at
                    FROM balance_history 
                    WHERE spot_value IS NOT NULL 
                        AND futures_value IS NOT NULL 
                        AND total_value IS NOT NULL 
                        AND recorded_at IS NOT NULL
                        AND session_id = %s
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
                        formatted_result.append(row_dict)
                    else:
                        print(f"Invalid timestamp format: {row_dict['recorded_at']}")
                        continue
                
                return formatted_result

        except Exception as e:
            print(f"Error retrieving balance history: {str(e)}")
            return []
