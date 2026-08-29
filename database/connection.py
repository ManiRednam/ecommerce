import os
import mysql.connector as SQLC


def get_db_config():
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', 'mani999'),
        'database': os.getenv('DB_NAME', 'ecommerce1'),
        'use_pure': True,
    }


def ensure_database_exists():
    config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', 'mani999'),
        'use_pure': True,
    }
    conn = SQLC.connect(**config)
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {os.getenv('DB_NAME', 'ecommerce1')}")
    cursor.close()
    conn.close()


# database configuration
def databaseConfig():
    db_config = SQLC.connect(**get_db_config())
    return db_config