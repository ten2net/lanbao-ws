"""创建自选股管理所需的 DuckDB 表"""
import os
import sys

sys.path.insert(0, 'src')

from lanbao_data import DuckDBStorage


def migrate():
    db_path = os.getenv('FAVOR_DB_PATH', './data/favor.duckdb')
    storage = DuckDBStorage(db_path, read_only=False)
    conn = storage._conn

    # favor_conditions
    conn.execute("CREATE SEQUENCE IF NOT EXISTS favor_condition_id_seq START 1;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS favor_conditions (
            id INTEGER PRIMARY KEY DEFAULT nextval('favor_condition_id_seq'),
            name VARCHAR NOT NULL,
            query VARCHAR NOT NULL,
            description VARCHAR,
            enabled BOOLEAN DEFAULT true,
            priority INTEGER DEFAULT 0,
            max_results INTEGER DEFAULT 15,
            filter_hot_sector BOOLEAN DEFAULT false,
            filter_min_cap_yi DOUBLE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # favor_accounts
    conn.execute("""
        CREATE TABLE IF NOT EXISTS favor_accounts (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            env_prefix VARCHAR,
            target_group VARCHAR DEFAULT '自选股',
            enabled BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # favor_watchlist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS favor_watchlist (
            code VARCHAR NOT NULL,
            name VARCHAR,
            account_id VARCHAR DEFAULT 'default',
            group_name VARCHAR DEFAULT '自选股',
            source_condition VARCHAR,
            signal_type VARCHAR,
            confidence DOUBLE,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (code, account_id, group_name)
        )
    """)

    # favor_pick_logs
    conn.execute("CREATE SEQUENCE IF NOT EXISTS favor_pick_log_id_seq START 1;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS favor_pick_logs (
            id INTEGER PRIMARY KEY DEFAULT nextval('favor_pick_log_id_seq'),
            condition_id INTEGER,
            condition_name VARCHAR,
            picked_count INTEGER,
            filtered_count INTEGER,
            duration_ms INTEGER,
            picked_codes VARCHAR[],
            error_message VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert default account
    conn.execute("""
        INSERT OR IGNORE INTO favor_accounts (id, name, target_group, enabled)
        VALUES ('default', '默认账户', '自选股', true)
    """)

    storage.close()
    print("Favor tables migrated successfully.")


if __name__ == '__main__':
    migrate()
