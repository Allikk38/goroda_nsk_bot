import sqlite3
import json
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

DB_NAME = 'user_data.db'

def init_database():
    """Инициализация базы данных"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Создаем таблицу пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                phone TEXT,
                consent_given INTEGER DEFAULT 0,
                consent_date TEXT,
                consent_ip TEXT,
                data TEXT,  -- JSON с остальными данными
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        # Создаем таблицу логов действий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        raise

def save_user_data(user_id: int, data: Dict[str, Any]):
    """Сохраняет или обновляет данные пользователя"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Проверяем, существует ли пользователь
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()
        
        now = datetime.now().isoformat()
        
        # Преобразуем данные в JSON, исключая служебные поля
        data_to_save = {k: v for k, v in data.items() 
                       if k not in ['consent', 'consent_date', 'consent_ip']}
        data_json = json.dumps(data_to_save)
        
        if exists:
            # Обновляем
            cursor.execute('''
                UPDATE users 
                SET data = ?, updated_at = ?, name = ?, phone = ?
                WHERE user_id = ?
            ''', (
                data_json,
                now,
                data.get('name', ''),
                data.get('phone', ''),
                user_id
            ))
        else:
            # Создаем нового пользователя
            cursor.execute('''
                INSERT INTO users (user_id, name, phone, data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                data.get('name', ''),
                data.get('phone', ''),
                data_json,
                now,
                now
            ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения данных пользователя {user_id}: {e}")
        return False

def save_consent(user_id: int, consent: bool = True, ip: str = None):
    """Сохраняет согласие пользователя"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # Проверяем, существует ли пользователь
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute('''
                UPDATE users 
                SET consent_given = ?, consent_date = ?, consent_ip = ?, updated_at = ?
                WHERE user_id = ?
            ''', (1 if consent else 0, now, ip or '', now, user_id))
        else:
            cursor.execute('''
                INSERT INTO users (user_id, consent_given, consent_date, consent_ip, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, 1 if consent else 0, now, ip or '', now, now))
        
        conn.commit()
        conn.close()
        
        # Логируем действие
        log_user_action(user_id, f"consent_{'given' if consent else 'revoked'}")
        logger.info(f"✅ Согласие {'дано' if consent else 'отозвано'} для пользователя {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения согласия: {e}")
        return False

def get_user_consent(user_id: int) -> bool:
    """Проверяет наличие согласия у пользователя"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT consent_given FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return bool(result[0]) if result else False
    except Exception as e:
        logger.error(f"❌ Ошибка проверки согласия: {e}")
        return False

def get_user_data(user_id: int) -> Optional[Dict[str, Any]]:
    """Получает все данные пользователя"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, name, phone, consent_given, consent_date, data
            FROM users WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            user_data = {
                'user_id': result[0],
                'name': result[1] or '',
                'phone': result[2] or '',
                'consent_given': bool(result[3]),
                'consent_date': result[4] or '',
            }
            # Добавляем остальные данные из JSON
            if result[5]:
                try:
                    extra_data = json.loads(result[5])
                    user_data.update(extra_data)
                except:
                    pass
            return user_data
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка получения данных пользователя: {e}")
        return None

def delete_user_data(user_id: int) -> bool:
    """Удаляет все данные пользователя"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM user_actions WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        log_user_action(user_id, "data_deleted")
        logger.info(f"✅ Данные пользователя {user_id} удалены")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка удаления данных: {e}")
        return False

def log_user_action(user_id: int, action: str):
    """Логирует действие пользователя"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_actions (user_id, action, timestamp)
            VALUES (?, ?, ?)
        ''', (user_id, action, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"❌ Ошибка логирования действия: {e}")

def cleanup_old_data(days: int = 1095):  # 3 года
    """Очищает старые данные пользователей без активного согласия"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Удаляем пользователей без согласия, у которых данные старше cutoff_date
        cursor.execute('''
            DELETE FROM users 
            WHERE consent_given = 0 
            AND updated_at < ?
        ''', (cutoff_date,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted > 0:
            logger.info(f"✅ Очищено {deleted} записей пользователей без согласия")
        return deleted
    except Exception as e:
        logger.error(f"❌ Ошибка очистки данных: {e}")
        return 0
