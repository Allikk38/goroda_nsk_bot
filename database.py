import sqlite3
import json
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any, List
import os

logger = logging.getLogger(__name__)

DB_NAME = 'user_data.db'
BACKUP_DIR = 'backups'

def init_database():
    """Инициализация базы данных"""
    try:
        # Создаем папку для бэкапов
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                phone TEXT,
                consent_given INTEGER DEFAULT 0,
                consent_date TEXT,
                consent_ip TEXT,
                data TEXT,
                created_at TEXT,
                updated_at TEXT,
                last_activity TEXT
            )
        ''')
        
        # Таблица логов действий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                timestamp TEXT
            )
        ''')
        
        # Таблица для бэкапов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                created_at TEXT,
                records_count INTEGER,
                status TEXT
            )
        ''')
        
        # Создаем индексы
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_consent ON users(consent_given)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_updated ON users(updated_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity)')
        
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
        
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()
        
        now = datetime.now().isoformat()
        
        data_to_save = {k: v for k, v in data.items() 
                       if k not in ['consent', 'consent_date', 'consent_ip']}
        data_json = json.dumps(data_to_save, ensure_ascii=False)
        
        if exists:
            cursor.execute('''
                UPDATE users 
                SET data = ?, updated_at = ?, last_activity = ?, name = ?, phone = ?
                WHERE user_id = ?
            ''', (
                data_json,
                now,
                now,
                data.get('name', ''),
                data.get('phone', ''),
                user_id
            ))
        else:
            cursor.execute('''
                INSERT INTO users (user_id, name, phone, data, created_at, updated_at, last_activity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                data.get('name', ''),
                data.get('phone', ''),
                data_json,
                now,
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
        
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute('''
                UPDATE users 
                SET consent_given = ?, consent_date = ?, consent_ip = ?, updated_at = ?, last_activity = ?
                WHERE user_id = ?
            ''', (1 if consent else 0, now, ip or '', now, now, user_id))
        else:
            cursor.execute('''
                INSERT INTO users (user_id, consent_given, consent_date, consent_ip, created_at, updated_at, last_activity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, 1 if consent else 0, now, ip or '', now, now, now))
        
        conn.commit()
        conn.close()
        
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
            SELECT user_id, name, phone, consent_given, consent_date, data, created_at, updated_at
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
                'created_at': result[6] or '',
                'updated_at': result[7] or ''
            }
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

def get_all_users_with_consent() -> List[Dict[str, Any]]:
    """Получает всех пользователей с активным согласием"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, name, phone, consent_date, created_at, updated_at
            FROM users 
            WHERE consent_given = 1
            ORDER BY consent_date DESC
        ''')
        results = cursor.fetchall()
        conn.close()
        
        users = []
        for row in results:
            users.append({
                'user_id': row[0],
                'name': row[1] or 'Не указано',
                'phone': row[2] or 'Не указано',
                'consent_date': row[3] or 'Не указано',
                'created_at': row[4] or 'Не указано',
                'updated_at': row[5] or 'Не указано'
            })
        return users
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка пользователей: {e}")
        return []

def get_statistics() -> Dict[str, Any]:
    """Получает статистику по пользователям"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE consent_given = 1")
        with_consent = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE consent_given = 0")
        without_consent = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE date(updated_at) >= date('now', '-7 days')")
        active_last_week = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total': total,
            'with_consent': with_consent,
            'without_consent': without_consent,
            'active_last_week': active_last_week
        }
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики: {e}")
        return {'total': 0, 'with_consent': 0, 'without_consent': 0, 'active_last_week': 0}

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

def cleanup_old_data(days: int = 1095) -> int:
    """Очищает старые данные пользователей без активного согласия"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
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

def export_consents_to_json() -> str:
    """Экспортирует все согласия в JSON файл"""
    try:
        users = get_all_users_with_consent()
        
        if not users:
            logger.warning("⚠️ Нет пользователей с согласием для экспорта")
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{BACKUP_DIR}/consents_backup_{timestamp}.json"
        
        data = {
            'export_date': datetime.now().isoformat(),
            'total_records': len(users),
            'users': users
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Сохраняем запись о бэкапе в БД
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO backups (filename, created_at, records_count, status)
            VALUES (?, ?, ?, ?)
        ''', (filename, datetime.now().isoformat(), len(users), 'success'))
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Бэкап создан: {filename} ({len(users)} записей)")
        return filename
    except Exception as e:
        logger.error(f"❌ Ошибка создания бэкапа: {e}")
        return None

def get_backup_history() -> List[Dict[str, Any]]:
    """Получает историю бэкапов"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, filename, created_at, records_count, status
            FROM backups
            ORDER BY created_at DESC
            LIMIT 20
        ''')
        results = cursor.fetchall()
        conn.close()
        
        backups = []
        for row in results:
            backups.append({
                'id': row[0],
                'filename': row[1],
                'created_at': row[2],
                'records_count': row[3],
                'status': row[4]
            })
        return backups
    except Exception as e:
        logger.error(f"❌ Ошибка получения истории бэкапов: {e}")
        return []
