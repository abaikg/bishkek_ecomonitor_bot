# database/db.py
import sqlite3
import logging

logger = logging.getLogger(__name__)

DATABASE_NAME = "subscriptions.db"

def init_db():
    """Инициализирует базу данных, создавая таблицу подписок, если она не существует."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            location_name TEXT,
            aqi_threshold INTEGER,
            last_notified_aqi INTEGER,
            is_active INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована.")

def add_subscription(user_id: int, chat_id: int, latitude: float, longitude: float, location_name: str, aqi_threshold: int = None):
    """Добавляет новую подписку или обновляет существующую."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO subscriptions 
            (user_id, chat_id, latitude, longitude, location_name, aqi_threshold, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, chat_id, latitude, longitude, location_name, aqi_threshold, 1))
        conn.commit()
        logger.info(f"Подписка для пользователя {user_id} обновлена/добавлена.")
        return True
    except sqlite3.Error as e:
        logger.error(f"Ошибка при добавлении/обновлении подписки для {user_id}: {e}")
        return False
    finally:
        conn.close()

def remove_subscription(user_id: int):
    """Удаляет подписку для пользователя."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
        conn.commit()
        logger.info(f"Подписка для пользователя {user_id} удалена.")
        return True
    except sqlite3.Error as e:
        logger.error(f"Ошибка при удалении подписки для {user_id}: {e}")
        return False
    finally:
        conn.close()

def get_subscription(user_id: int):
    """Получает подписку для конкретного пользователя."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subscriptions WHERE user_id = ?", (user_id,))
    sub = cursor.fetchone()
    conn.close()
    if sub:
        # Возвращаем словарь для удобства доступа
        return {
            "user_id": sub[0],
            "chat_id": sub[1],
            "latitude": sub[2],
            "longitude": sub[3],
            "location_name": sub[4],
            "aqi_threshold": sub[5],
            "last_notified_aqi": sub[6],
            "is_active": bool(sub[7])
        }
    return None

def get_all_active_subscriptions():
    """Получает все активные подписки."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subscriptions WHERE is_active = 1")
    subscriptions = []
    for sub in cursor.fetchall():
        subscriptions.append({
            "user_id": sub[0],
            "chat_id": sub[1],
            "latitude": sub[2],
            "longitude": sub[3],
            "location_name": sub[4],
            "aqi_threshold": sub[5],
            "last_notified_aqi": sub[6],
            "is_active": bool(sub[7])
        })
    conn.close()
    return subscriptions

def update_last_notified_aqi(user_id: int, aqi: int):
    """Обновляет последний известный AQI, о котором было уведомлено."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE subscriptions SET last_notified_aqi = ? WHERE user_id = ?", (aqi, user_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Ошибка при обновлении last_notified_aqi для {user_id}: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
