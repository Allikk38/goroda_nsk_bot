import telebot
import logging
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import threading
import time
import os
import json

from config import (
    BOT_TOKEN, ADMIN_IDS, logger, 
    CONSENT_TEXT, PRIVACY_TEXT, MAIN_MENU_TEXT, HELP_TEXT
)
from database import (
    init_database, save_user_data, save_consent, 
    get_user_consent, get_user_data, delete_user_data,
    log_user_action, cleanup_old_data, get_all_users_with_consent,
    get_statistics, export_consents_to_json, get_backup_history
)
from keyboards import *
from states import state_manager

# --- СОЗДАНИЕ БОТА ---
bot = telebot.TeleBot(BOT_TOKEN)

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
init_database()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

def safe_delete_message(user_id: int, message_id: int):
    """Безопасно удаляет сообщение"""
    try:
        if message_id:
            bot.delete_message(user_id, message_id)
    except Exception as e:
        logger.debug(f"Не удалось удалить сообщение {message_id}: {e}")

def remove_keyboard(user_id: int):
    """Убирает клавиатуру у пользователя без отправки лишних сообщений"""
    try:
        bot.send_message(
            user_id,
            "",  # Пустое сообщение для скрытия клавиатуры
            reply_markup=ReplyKeyboardRemove()
        )
        # Удаляем это пустое сообщение, чтобы не засорять чат
        # Но нужно получить message_id, для этого используем другой подход
    except Exception as e:
        logger.debug(f"Не удалось скрыть клавиатуру: {e}")

def remove_keyboard_silent(user_id: int):
    """Убирает клавиатуру без отправки видимого сообщения"""
    try:
        # Отправляем пустое сообщение и сразу удаляем его
        msg = bot.send_message(
            user_id,
            ".",
            reply_markup=ReplyKeyboardRemove()
        )
        # Удаляем это служебное сообщение
        safe_delete_message(user_id, msg.message_id)
    except Exception as e:
        logger.debug(f"Не удалось скрыть клавиатуру: {e}")

def send_main_menu(message):
    """Отправляет главное меню с Reply клавиатурой"""
    user_id = message.chat.id if hasattr(message, 'chat') else message
    
    if hasattr(message, 'chat'):
        user_id = message.chat.id
    
    # Убираем старую клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    bot.send_message(
        user_id,
        MAIN_MENU_TEXT,
        reply_markup=get_main_menu_keyboard()
    )

def show_main_menu_inline(user_id, first_name=None):
    """Показывает главное меню (встроенное)"""
    if not first_name:
        try:
            user = bot.get_chat(user_id)
            first_name = user.first_name or "Пользователь"
        except:
            first_name = "Пользователь"
    
    # Убираем старую клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    # Очищаем состояние
    state_manager.clear_state(user_id)
    
    welcome_msg = bot.send_message(
        user_id,
        f"Здравствуйте, {first_name} | Новостройки.\n"
        "Я помощник канала «Города»\n"
        "- Мой сервис помогает жителям Новосибирска и других регионов РФ "
        "в подборе самых интересных объектов недвижимости\n\n"
        "- Ответьте на мои вопросы о ваших пожеланиях, и мы сможем подобрать лучший вариант"
    )
    
    question_msg = bot.send_message(
        user_id,
        "Ответьте, пожалуйста, что вас интересует?",
        reply_markup=get_main_inline_keyboard()
    )
    
    # Сохраняем ID сообщений для очистки
    state_manager.delete_message_ids(user_id, welcome_msg.message_id, question_msg.message_id)

# ==================== ОБРАБОТЧИК КОМАНД ====================

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    
    # Убираем старую клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    state_manager.clear_state(user_id)
    
    # Проверяем, есть ли уже согласие в базе
    if get_user_consent(user_id):
        send_main_menu(message)
        return
    
    # Показываем запрос согласия
    msg = bot.send_message(
        user_id,
        CONSENT_TEXT,
        reply_markup=get_consent_keyboard(),
        disable_web_page_preview=True
    )
    state_manager.delete_message_ids(user_id, msg.message_id)

@bot.message_handler(commands=['menu'])
def handle_menu(message):
    """Показать главное меню"""
    user_id = message.chat.id
    
    if not get_user_consent(user_id):
        remove_keyboard_silent(user_id)
        bot.send_message(
            user_id,
            "⚠️ Для работы бота необходимо дать согласие на обработку данных.\n"
            "Напишите /start для начала."
        )
        return
    
    send_main_menu(message)

@bot.message_handler(commands=['help'])
def handle_help(message):
    """Показать справку"""
    user_id = message.chat.id
    bot.send_message(user_id, HELP_TEXT)

@bot.message_handler(commands=['privacy'])
def handle_privacy(message):
    """Показать политику конфиденциальности"""
    user_id = message.chat.id
    
    # Проверяем, есть ли согласие
    has_consent = get_user_consent(user_id)
    
    try:
        if has_consent:
            # Если согласие есть - показываем с главным меню
            bot.send_message(
                user_id,
                PRIVACY_TEXT,
                disable_web_page_preview=True,
                reply_markup=get_main_menu_keyboard()
            )
        else:
            # Если согласия нет - показываем с кнопкой "Назад к согласию"
            bot.send_message(
                user_id,
                PRIVACY_TEXT,
                disable_web_page_preview=True,
                reply_markup=get_back_to_consent_keyboard()
            )
        logger.info(f"✅ Команда /privacy выполнена для пользователя {user_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка в /privacy: {e}")
        bot.send_message(
            user_id,
            "⚠️ Произошла ошибка при загрузке политики конфиденциальности. Попробуйте позже."
        )

@bot.message_handler(commands=['revoke'])
def handle_revoke(message):
    """Отзыв согласия"""
    user_id = message.chat.id
    
    if not get_user_consent(user_id):
        bot.send_message(
            user_id,
            "❌ У вас нет активного согласия на обработку данных.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    bot.send_message(
        user_id,
        "⚠️ ВЫ ДЕЙСТВИТЕЛЬНО ХОТИТЕ ОТОЗВАТЬ СОГЛАСИЕ НА ОБРАБОТКУ ПЕРСОНАЛЬНЫХ ДАННЫХ?\n\n"
        "После отзыва:\n"
        "• Все ваши данные будут удалены\n"
        "• Мы не сможем предоставлять вам услуги\n"
        "• Вы сможете начать заново через /start\n\n"
        "Подтвердите действие:",
        reply_markup=get_revoke_consent_keyboard()
    )

@bot.message_handler(commands=['mydata'])
def handle_my_data(message):
    """Показать данные пользователя"""
    user_id = message.chat.id
    
    if not get_user_consent(user_id):
        bot.send_message(
            user_id,
            "❌ У вас нет активного согласия. Напишите /start для начала.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    user_info = get_user_data(user_id)
    if not user_info:
        bot.send_message(
            user_id,
            "❌ Ваши данные не найдены в системе.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Формируем отчет
    report = "📋 ВАШИ ДАННЫЕ В СИСТЕМЕ:\n\n"
    
    fields = {
        'name': '👤 Имя',
        'phone': '📞 Телефон',
        'interest': '🏠 Интерес',
        'budget_limit': '💰 Бюджет до',
        'rooms': '🛏 Комнаты',
        'district': '📍 Район',
        'property_type': '🏠 Тип объекта',
        'sell_area': '📐 Площадь',
        'sell_floor': '🏢 Этаж',
        'condition': '🔧 Состояние',
        'sell_price': '💰 Стоимость',
        'urgency': '⏰ Срочность'
    }
    
    has_data = False
    for key, label in fields.items():
        if key in user_info and user_info[key]:
            value = user_info[key]
            if key == 'phone' and len(str(value)) >= 10:
                value = str(value)[:5] + '****' + str(value)[-3:]
            report += f"{label}: {value}\n"
            has_data = True
    
    if not has_data:
        report += "Данные не заполнены\n"
    
    report += f"\n📌 СОГЛАСИЕ: {'✅ Да' if user_info.get('consent_given') else '❌ Нет'}"
    if user_info.get('consent_date'):
        report += f"\n📅 ДАТА СОГЛАСИЯ: {user_info['consent_date'][:10]}"
    
    bot.send_message(user_id, report, reply_markup=get_main_menu_keyboard())

@bot.message_handler(commands=['delete_my_data'])
def handle_delete_data(message):
    """Удаление всех данных пользователя"""
    user_id = message.chat.id
    
    if not get_user_consent(user_id):
        bot.send_message(
            user_id,
            "❌ У вас нет данных в системе.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    bot.send_message(
        user_id,
        "⚠️ ВНИМАНИЕ! Вы собираетесь удалить ВСЕ свои данные из системы.\n\n"
        "Это действие НЕЛЬЗЯ будет отменить.\n\n"
        "Подтвердите удаление:",
        reply_markup=get_delete_data_keyboard()
    )

@bot.message_handler(commands=['admin'])
def handle_admin(message):
    """Панель администратора"""
    user_id = message.chat.id
    
    if not is_admin(user_id):
        bot.send_message(user_id, "⛔ У вас нет доступа к этой команде.")
        return
    
    if not get_user_consent(user_id):
        bot.send_message(
            user_id,
            "⚠️ Вы должны дать согласие на обработку данных.\n"
            "Напишите /start для начала."
        )
        return
    
    # Убираем старую клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    bot.send_message(
        user_id,
        "👨‍💼 ПАНЕЛЬ АДМИНИСТРАТОРА\n\n"
        "Выберите действие:",
        reply_markup=get_admin_menu_keyboard()
    )

# ==================== ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ (МЕНЮ) ====================

@bot.message_handler(func=lambda message: message.text == "🏠 Главное меню")
def handle_main_menu_button(message):
    user_id = message.chat.id
    if not get_user_consent(user_id):
        remove_keyboard_silent(user_id)
        bot.send_message(
            user_id,
            "⚠️ Для работы бота необходимо дать согласие на обработку данных.\n"
            "Напишите /start для начала."
        )
        return
    send_main_menu(message)

@bot.message_handler(func=lambda message: message.text == "📄 Мои данные")
def handle_my_data_button(message):
    handle_my_data(message)

@bot.message_handler(func=lambda message: message.text == "🔒 Политика конфиденциальности")
def handle_privacy_button(message):
    handle_privacy(message)

@bot.message_handler(func=lambda message: message.text == "❌ Отозвать согласие")
def handle_revoke_button(message):
    handle_revoke(message)

@bot.message_handler(func=lambda message: message.text == "🗑 Удалить данные")
def handle_delete_button(message):
    handle_delete_data(message)

@bot.message_handler(func=lambda message: message.text == "🔄 Начать заново")
def handle_restart(message):
    user_id = message.chat.id
    
    # Убираем клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    # Удаляем все данные и состояние
    if get_user_consent(user_id):
        delete_user_data(user_id)
    state_manager.clear_state(user_id)
    
    bot.send_message(
        user_id,
        "🔄 Начинаем заново!"
    )
    handle_start(message)

@bot.message_handler(func=lambda message: message.text == "🔙 Назад")
def handle_back_button(message):
    """Обработка кнопки 'Назад' в Reply клавиатуре"""
    user_id = message.chat.id
    # Возвращаемся в главное меню
    if get_user_consent(user_id):
        send_main_menu(message)
    else:
        remove_keyboard_silent(user_id)
        bot.send_message(
            user_id,
            "⚠️ Напишите /start для начала работы."
        )

# ==================== АДМИН-ФУНКЦИИ ====================

@bot.message_handler(func=lambda message: message.text == "📊 Статистика" and is_admin(message.chat.id))
def handle_admin_stats(message):
    user_id = message.chat.id
    stats = get_statistics()
    
    report = (
        "📊 СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ\n\n"
        f"👥 Всего пользователей: {stats['total']}\n"
        f"✅ С активным согласием: {stats['with_consent']}\n"
        f"❌ Без согласия: {stats['without_consent']}\n"
        f"📈 Активны за неделю: {stats['active_last_week']}\n"
    )
    
    bot.send_message(user_id, report, reply_markup=get_admin_menu_keyboard())

@bot.message_handler(func=lambda message: message.text == "📋 Список согласий" and is_admin(message.chat.id))
def handle_admin_consents(message):
    user_id = message.chat.id
    users = get_all_users_with_consent()
    
    if not users:
        bot.send_message(
            user_id,
            "📋 Нет пользователей с активным согласием.",
            reply_markup=get_admin_menu_keyboard()
        )
        return
    
    # Отправляем список (максимум 10 пользователей в одном сообщении)
    total = len(users)
    page_size = 10
    total_pages = (total + page_size - 1) // page_size
    
    for page in range(total_pages):
        start = page * page_size
        end = min(start + page_size, total)
        
        report = f"📋 СПИСОК СОГЛАСИЙ (стр. {page+1}/{total_pages})\n\n"
        for user in users[start:end]:
            report += (
                f"🆔 {user['user_id']}\n"
                f"👤 {user['name']}\n"
                f"📞 {user['phone']}\n"
                f"📅 {user['consent_date'][:10] if user['consent_date'] != 'Не указано' else '—'}\n"
                f"{'─' * 20}\n"
            )
        
        bot.send_message(user_id, report, reply_markup=get_admin_menu_keyboard())

@bot.message_handler(func=lambda message: message.text == "💾 Создать бэкап" and is_admin(message.chat.id))
def handle_admin_backup(message):
    user_id = message.chat.id
    bot.send_message(user_id, "⏳ Создаю бэкап согласий...")
    
    filename = export_consents_to_json()
    
    if filename and os.path.exists(filename):
        # Отправляем файл
        with open(filename, 'rb') as f:
            bot.send_document(
                user_id,
                f,
                caption=f"✅ Бэкап создан: {os.path.basename(filename)}",
                reply_markup=get_admin_menu_keyboard()
            )
        logger.info(f"📤 Бэкап отправлен админу {user_id}")
    else:
        bot.send_message(
            user_id,
            "❌ Не удалось создать бэкап. Проверьте логи.",
            reply_markup=get_admin_menu_keyboard()
        )

@bot.message_handler(func=lambda message: message.text == "📦 История бэкапов" and is_admin(message.chat.id))
def handle_admin_backup_history(message):
    user_id = message.chat.id
    backups = get_backup_history()
    
    if not backups:
        bot.send_message(
            user_id,
            "📦 История бэкапов пуста.",
            reply_markup=get_admin_menu_keyboard()
        )
        return
    
    report = "📦 ИСТОРИЯ БЭКАПОВ\n\n"
    for backup in backups[:10]:  # Показываем последние 10
        report += (
            f"📄 {os.path.basename(backup['filename'])}\n"
            f"📅 {backup['created_at'][:19]}\n"
            f"📊 {backup['records_count']} записей\n"
            f"✅ {backup['status']}\n"
            f"{'─' * 20}\n"
        )
    
    bot.send_message(user_id, report, reply_markup=get_admin_menu_keyboard())

@bot.message_handler(func=lambda message: message.text == "🔙 Выход из админ-панели" and is_admin(message.chat.id))
def handle_admin_exit(message):
    user_id = message.chat.id
    send_main_menu(message)

# ==================== ОБРАБОТЧИК INLINE КНОПОК ====================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data
    
    # ==================== ОБРАБОТКА СОГЛАСИЯ ====================
    if data == "consent_agree":
        save_consent(user_id, True)
        
        # Удаляем сообщение с согласием
        safe_delete_message(user_id, call.message.message_id)
        
        bot.send_message(
            user_id,
            "✅ СПАСИБО! ВАШЕ СОГЛАСИЕ ПОЛУЧЕНО.\n\n"
            "Теперь мы можем обрабатывать ваши данные для подбора лучших вариантов."
        )
        
        # Показываем главное меню
        show_main_menu_inline(user_id, call.from_user.first_name)
        return
    
    elif data == "consent_disagree":
        safe_delete_message(user_id, call.message.message_id)
        
        # Убираем клавиатуру без отправки сообщения
        remove_keyboard_silent(user_id)
        
        bot.send_message(
            user_id,
            "❌ МЫ НЕ МОЖЕМ ПРОДОЛЖАТЬ РАБОТУ БЕЗ ВАШЕГО СОГЛАСИЯ.\n\n"
            "Мы уважаем ваше право на конфиденциальность.\n"
            "Если передумаете, просто напишите /start заново."
        )
        state_manager.clear_state(user_id)
        return
    
    # ==================== ОБРАБОТКА ВОЗВРАТА К СОГЛАСИЮ ====================
    elif data == "back_to_consent":
        safe_delete_message(user_id, call.message.message_id)
        
        # Показываем заново экран согласия
        msg = bot.send_message(
            user_id,
            CONSENT_TEXT,
            reply_markup=get_consent_keyboard(),
            disable_web_page_preview=True
        )
        state_manager.delete_message_ids(user_id, msg.message_id)
        return
    
    # ==================== ОБРАБОТКА ОТЗЫВА СОГЛАСИЯ ====================
    elif data == "revoke_confirm":
        save_consent(user_id, False)
        delete_user_data(user_id)
        state_manager.clear_state(user_id)
        
        safe_delete_message(user_id, call.message.message_id)
        
        # Убираем клавиатуру без отправки сообщения
        remove_keyboard_silent(user_id)
        
        bot.send_message(
            user_id,
            "✅ ВАШЕ СОГЛАСИЕ ОТОЗВАНО. ВСЕ ДАННЫЕ УДАЛЕНЫ.\n\n"
            "Если захотите воспользоваться услугами снова, напишите /start."
        )
        return
    
    elif data == "revoke_cancel":
        safe_delete_message(user_id, call.message.message_id)
        bot.send_message(
            user_id,
            "✅ Отзыв согласия отменен. Ваши данные сохранены.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # ==================== ОБРАБОТКА УДАЛЕНИЯ ДАННЫХ ====================
    elif data == "delete_confirm":
        if delete_user_data(user_id):
            state_manager.clear_state(user_id)
            safe_delete_message(user_id, call.message.message_id)
            
            # Убираем клавиатуру без отправки сообщения
            remove_keyboard_silent(user_id)
            
            bot.send_message(
                user_id,
                "✅ ВСЕ ВАШИ ДАННЫЕ УСПЕШНО УДАЛЕНЫ.\n\n"
                "Если захотите воспользоваться услугами снова, напишите /start."
            )
        else:
            bot.send_message(
                user_id,
                "❌ Произошла ошибка при удалении данных. Попробуйте позже.",
                reply_markup=get_main_menu_keyboard()
            )
        return
    
    elif data == "delete_cancel":
        safe_delete_message(user_id, call.message.message_id)
        bot.send_message(
            user_id,
            "✅ Удаление данных отменено.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # ==================== НАВИГАЦИЯ (КНОПКА НАЗАД) ====================
    elif data == "back" or data == "back_to_menu":
        safe_delete_message(user_id, call.message.message_id)
        # Возвращаемся на предыдущий шаг
        prev_step = state_manager.pop_step(user_id)
        if prev_step:
            # Восстанавливаем предыдущий шаг
            restore_previous_step(user_id, prev_step)
        else:
            # Если нет истории, показываем главное меню
            show_main_menu_inline(user_id)
        return
    
    elif data == "main_menu":
        safe_delete_message(user_id, call.message.message_id)
        show_main_menu_inline(user_id, call.from_user.first_name)
        return
    
    # ==================== ОБРАБОТКА НАВИГАЦИОННЫХ BACK ====================
    elif data == "back_to_interest":
        safe_delete_message(user_id, call.message.message_id)
        state_manager.pop_step(user_id)
        show_main_menu_inline(user_id, call.from_user.first_name)
        return
    
    elif data == "back_to_rooms":
        safe_delete_message(user_id, call.message.message_id)
        state_manager.pop_step(user_id)
        ask_rooms(user_id)
        return
    
    elif data == "back_to_district":
        safe_delete_message(user_id, call.message.message_id)
        state_manager.pop_step(user_id)
        ask_district(user_id)
        return
    
    elif data == "back_to_property":
        safe_delete_message(user_id, call.message.message_id)
        state_manager.pop_step(user_id)
        ask_property_type(user_id)
        return
    
    elif data == "back_to_sell_district":
        safe_delete_message(user_id, call.message.message_id)
        state_manager.pop_step(user_id)
        ask_sell_district(user_id)
        return
    
    elif data == "back_to_sell_price":
        safe_delete_message(user_id, call.message.message_id)
        state_manager.pop_step(user_id)
        ask_sell_price(user_id)
        return
    
    elif data == "back_to_name":
        safe_delete_message(user_id, call.message.message_id)
        state_manager.pop_step(user_id)
        ask_name(user_id)
        return
    
    elif data == "back_to_contact":
        safe_delete_message(user_id, call.message.message_id)
        state_manager.pop_step(user_id)
        ask_contact(user_id)
        return
    
    # ==================== ДАЛЬНЕЙШАЯ ОБРАБОТКА (ПРОВЕРКА СОГЛАСИЯ) ====================
    if not get_user_consent(user_id):
        remove_keyboard_silent(user_id)
        bot.send_message(
            user_id,
            "⚠️ Для продолжения работы необходимо дать согласие на обработку данных.\n"
            "Напишите /start для начала."
        )
        return
    
    # Удаляем старое сообщение
    safe_delete_message(user_id, call.message.message_id)
    
    # ==================== ВЕТКИ ИНТЕРЕСОВ ====================
    if data == "interest_self":
        state_manager.push_step(user_id, "interest_self")
        state_manager.set_data(user_id, 'interest', "Квартира для себя")
        ask_budget(user_id)
    
    elif data == "interest_invest":
        state_manager.push_step(user_id, "interest_invest")
        state_manager.set_data(user_id, 'interest', "Инвестиционная квартира")
        ask_budget(user_id)
    
    elif data == "interest_sell":
        state_manager.push_step(user_id, "interest_sell")
        state_manager.set_data(user_id, 'interest', "Хочу разместить свой объект")
        ask_property_type(user_id)
    
    elif data == "interest_watch":
        state_manager.push_step(user_id, "interest_watch")
        state_manager.set_data(user_id, 'interest', "Просто смотрю")
        
        # Сохраняем данные
        save_user_data(user_id, state_manager.get_all_data(user_id))
        log_user_action(user_id, "application_sent")
        
        # Убираем inline клавиатуру без отправки сообщения
        remove_keyboard_silent(user_id)
        
        bot.send_message(
            user_id,
            "✅ Отлично! Мы будем держать вас в курсе новых интересных предложений.\n"
            "Подпишитесь на наш канал, чтобы не пропустить обновления!",
            reply_markup=get_main_menu_keyboard()
        )
        state_manager.clear_state(user_id)
    
    # ==================== ВОПРОСЫ ДЛЯ ПОКУПКИ ====================
    elif data.startswith("rooms_"):
        rooms = data.split("_")[1]
        state_manager.set_data(user_id, 'rooms', rooms)
        state_manager.push_step(user_id, "rooms")
        ask_district(user_id)
    
    elif data.startswith("district_"):
        district = data.split("_")[1]
        if district == "other":
            safe_delete_message(user_id, call.message.message_id)
            # Убираем inline клавиатуру, показываем Reply с кнопкой "Назад"
            remove_keyboard_silent(user_id)
            msg = bot.send_message(
                user_id,
                "✏️ Напишите ваш вариант района:\n(или нажмите /cancel для отмены)",
                reply_markup=get_back_with_main_menu_reply()
            )
            bot.register_next_step_handler(msg, handle_district_manual)
        else:
            district_names = {
                "central": "Центральный",
                "railway": "Железнодорожный",
                "october": "Октябрьский",
                "soviet": "Советский",
                "lenin": "Ленинский",
                "kirov": "Кировский",
                "pervomay": "Первомайский",
                "dzerzhinsky": "Дзержинский",
                "zaeltsovsky": "Заельцовский",
                "kalinin": "Калининский"
            }
            state_manager.set_data(user_id, 'district', district_names.get(district, district))
            state_manager.push_step(user_id, "district")
            ask_mortgage(user_id)
    
    elif data == "yes":
        state_manager.set_data(user_id, 'mortgage', "Да")
        state_manager.push_step(user_id, "mortgage")
        ask_name(user_id)
    
    elif data == "no":
        state_manager.set_data(user_id, 'mortgage', "Нет")
        state_manager.push_step(user_id, "mortgage")
        ask_name(user_id)
    
    # ==================== ВОПРОСЫ ДЛЯ ПРОДАЖИ ====================
    elif data.startswith("prop_"):
        property_type = data.split("_")[1]
        property_names = {
            "apartment": "Квартира",
            "house": "Дом/Коттедж",
            "commercial": "Коммерческая недвижимость",
            "land": "Земельный участок",
            "other": "Другое"
        }
        state_manager.set_data(user_id, 'property_type', property_names.get(property_type, property_type))
        state_manager.push_step(user_id, "property_type")
        
        if property_type == "apartment":
            ask_sell_rooms(user_id)
        else:
            ask_sell_area(user_id)
    
    elif data.startswith("sell_rooms_"):
        rooms = data.split("_")[2]
        state_manager.set_data(user_id, 'sell_rooms', rooms)
        state_manager.push_step(user_id, "sell_rooms")
        ask_sell_area(user_id)
    
    elif data.startswith("condition_"):
        condition = data.split("_")[1]
        condition_names = {
            "bad": "Требует ремонта",
            "normal": "Косметический ремонт",
            "good": "Евроремонт",
            "no_finish": "Новостройка без отделки",
            "with_finish": "Новостройка с отделкой"
        }
        state_manager.set_data(user_id, 'condition', condition_names.get(condition, condition))
        state_manager.push_step(user_id, "condition")
        ask_sell_price(user_id)
    
    elif data.startswith("urgency_"):
        urgency = data.split("_")[1]
        urgency_names = {
            "very": "Срочно (до 1 месяца)",
            "soon": "В ближайшее время (1-3 месяца)",
            "medium": "В течение 3-6 месяцев",
            "no": "Нет срочности (более 6 месяцев)"
        }
        state_manager.set_data(user_id, 'urgency', urgency_names.get(urgency, urgency))
        state_manager.push_step(user_id, "urgency")
        ask_sell_phone(user_id)
    
    # ==================== КОНТАКТЫ ====================
    elif data == "share_contact":
        state_manager.push_step(user_id, "share_contact")
        msg = bot.send_message(
            user_id,
            "📱 Вы действительно хотите поделиться своим номером телефона?",
            reply_markup=get_confirm_contact_keyboard()
        )
        state_manager.delete_message_ids(user_id, msg.message_id)
    
    elif data == "confirm_contact_yes":
        safe_delete_message(user_id, call.message.message_id)
        
        # Показываем клавиатуру с кнопкой "Отправить контакт"
        msg = bot.send_message(
            user_id,
            "📱 Нажмите кнопку ниже, чтобы поделиться номером телефона:",
            reply_markup=get_contact_request_keyboard()
        )
        bot.register_next_step_handler(msg, handle_contact)
        state_manager.push_step(user_id, "confirm_contact")
    
    elif data == "confirm_contact_no":
        safe_delete_message(user_id, call.message.message_id)
        ask_contact(user_id)
    
    elif data == "manual_phone":
        safe_delete_message(user_id, call.message.message_id)
        # Убираем inline клавиатуру, показываем Reply с кнопкой "Назад"
        remove_keyboard_silent(user_id)
        msg = bot.send_message(
            user_id,
            "✏️ Введите ваш номер телефона в формате +7XXXXXXXXXX:",
            reply_markup=get_back_with_main_menu_reply()
        )
        bot.register_next_step_handler(msg, handle_manual_phone)

# ==================== ФУНКЦИИ ДЛЯ ПОКУПКИ ====================

def ask_budget(user_id):
    safe_delete_question_message(user_id)
    
    # Убираем старую клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    msg = bot.send_message(
        user_id,
        "💰 Выше какой стоимости объекты не предлагать?\n"
        "(Введите сумму в рублях)",
        reply_markup=get_back_with_main_menu_reply()
    )
    state_manager.delete_message_ids(user_id, msg.message_id)
    bot.register_next_step_handler(msg, handle_budget_limit)

def handle_budget_limit(message):
    user_id = message.chat.id
    
    if message.text == "🔙 Назад" or message.text == "🏠 Главное меню":
        handle_navigation_commands(message)
        return
    
    if message.text == "/cancel":
        show_main_menu_inline(user_id)
        return
    
    state_manager.set_data(user_id, 'budget_limit', message.text)
    state_manager.push_step(user_id, "budget_limit")
    ask_rooms(user_id)

def ask_rooms(user_id):
    safe_delete_question_message(user_id)
    
    # Убираем Reply клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    msg = bot.send_message(
        user_id,
        "🛏 Сколько комнат вы хотите в будущей квартире?",
        reply_markup=get_rooms_inline_keyboard()
    )
    state_manager.delete_message_ids(user_id, msg.message_id)

def ask_district(user_id):
    safe_delete_question_message(user_id)
    
    # Убираем Reply клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    msg = bot.send_message(
        user_id,
        "📍 Выберите предпочтительный район:",
        reply_markup=get_district_inline_keyboard()
    )
    state_manager.delete_message_ids(user_id, msg.message_id)

def handle_district_manual(message):
    user_id = message.chat.id
    
    if message.text == "🔙 Назад" or message.text == "🏠 Главное меню":
        handle_navigation_commands(message)
        return
    
    if message.text == "/cancel":
        show_main_menu_inline(user_id)
        return
    
    state_manager.set_data(user_id, 'district', message.text)
    state_manager.push_step(user_id, "district_manual")
    ask_mortgage(user_id)

def ask_mortgage(user_id):
    safe_delete_question_message(user_id)
    
    # Убираем Reply клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    msg = bot.send_message(
        user_id,
        "🏦 Нужна ли вам ипотека?",
        reply_markup=get_yes_no_inline_keyboard()
    )
    state_manager.delete_message_ids(user_id, msg.message_id)

# ==================== ФУНКЦИИ ДЛЯ ПРОДАЖИ ====================

def ask_property_type(user_id):
    safe_delete_question_message(user_id)
    
    # Убираем Reply клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    msg = bot.send_message(
        user_id,
        "🏠 Какой тип недвижимости вы хотите продать?",
        reply_markup=get_property_type_keyboard()
    )
    state_manager.delete_message_ids(user_id, msg.message_id)

def ask_sell_rooms(user_id):
    safe_delete_question_message(user_id)
    
    # Убираем Reply клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    msg = bot.send_message(
        user_id,
        "🛏 Сколько комнат в вашей квартире?",
        reply_markup=get_sell_rooms_keyboard()
    )
    state_manager.delete_message_ids(user_id, msg.message_id)

def ask_sell_area(user_id):
    safe_delete_question_message(user_id)
    
    # Убираем Reply клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    msg = bot.send_message(
        user_id,
        "📐 Какая общая площадь вашего объекта? (в кв.м)\n"
        "Введите число:",
        reply_markup=get_back_with_main_menu_reply()
    )
    state_manager.delete_message_ids(user_id, msg.message_id)
    bot.register_next_step_handler(msg, handle_sell_area)

def handle_sell_area(message):
    user_id = message.chat.id
    
    if message.text == "🔙 Назад" or message.text == "🏠 Главное меню":
        handle_navigation_commands(message)
        return
    
    if message.text == "/cancel":
        show_main_menu_inline(user_id)
        return
    
    state_manager.set_data(user_id, 'sell_area', message.text)
    state_manager.push_step(user_id, "sell_area")
    ask_sell_floor(user_id)

def ask_sell_floor(user_id):
    safe_delete_question_message(user_id)
    
    # Убираем Reply клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    msg = bot.send_message(
        user_id,
        "🏢 На каком этаже находится объект и сколько этажей в доме?\n"
        "Например: 3/9 или 1/5",
        reply_markup=get_back_with_main_menu_reply()
    )
    state_manager.delete_message_ids(user_id, msg.message_id)
    bot.register_next_step_handler(msg, handle_sell_floor)

def handle_sell_floor(message):
    user_id = message.chat.id
    
    if message.text == "🔙 Назад" or message.text == "🏠 Главное меню":
        handle_navigation_commands(message)
        return
    
    if message.text == "/cancel":
        show_main_menu_inline(user_id)
        return
    
    state_manager.set_data(user_id, 'sell_floor', message.text)
    state_manager.push_step(user_id, "sell_floor")
    ask_sell_district(user_id)

def ask_sell_district(user_id):
    safe_delete_question_message(user_id)
    
    # Убираем Reply клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    msg = bot.send_message(
        user_id,
        "📍 В каком районе находится ваш объект?",
        reply_markup=get_district_inline_keyboard()
    )
    state_manager.delete_message_ids(user_id, msg.message_id)

def ask_sell_condition(user_id):
    safe_delete_question_message(user_id)
    
    # Убираем Reply клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    msg = bot.send_message(
        user_id,
        "🔧 Какое состояние у объекта?",
        reply_markup=get_condition_keyboard()
    )
    state_manager.delete_message_ids(user_id, msg.message_id)

def ask_sell_price(user_id):
    safe_delete_question_message(user_id)
    
    # Убираем Reply клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    msg = bot.send_message(
        user_id,
        "💰 Какую стоимость вы хотите указать?\n"
        "Введите сумму в рублях:",
        reply_markup=get_back_with_main_menu_reply()
    )
    state_manager.delete_message_ids(user_id, msg.message_id)
    bot.register_next_step_handler(msg, handle_sell_price)

def handle_sell_price(message):
    user_id = message.chat.id
    
    if message.text == "🔙 Назад" or message.text == "🏠 Главное меню":
        handle_navigation_commands(message)
        return
    
    if message.text == "/cancel":
        show_main_menu_inline(user_id)
        return
    
    state_manager.set_data(user_id, 'sell_price', message.text)
    state_manager.push_step(user_id, "sell_price")
    ask_sell_urgency(user_id)

def ask_sell_urgency(user_id):
    safe_delete_question_message(user_id)
    
    # Убираем Reply клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    msg = bot.send_message(
        user_id,
        "⏰ Насколько срочно вы хотите продать?",
        reply_markup=get_urgency_keyboard()
    )
    state_manager.delete_message_ids(user_id, msg.message_id)

def ask_sell_phone(user_id):
    ask_contact(user_id)

# ==================== ОБЩИЕ ФУНКЦИИ ====================

def ask_name(user_id):
    safe_delete_question_message(user_id)
    
    # Убираем Reply клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    msg = bot.send_message(
        user_id,
        "👤 Как Вас зовут?",
        reply_markup=get_back_with_main_menu_reply()
    )
    state_manager.delete_message_ids(user_id, msg.message_id)
    bot.register_next_step_handler(msg, handle_name)

def handle_name(message):
    user_id = message.chat.id
    
    if message.text == "🔙 Назад" or message.text == "🏠 Главное меню":
        handle_navigation_commands(message)
        return
    
    if message.text == "/cancel":
        show_main_menu_inline(user_id)
        return
    
    state_manager.set_data(user_id, 'name', message.text)
    state_manager.push_step(user_id, "name")
    ask_contact(user_id)

def ask_contact(user_id):
    safe_delete_question_message(user_id)
    
    # Убираем Reply клавиатуру без отправки сообщения
    remove_keyboard_silent(user_id)
    
    msg = bot.send_message(
        user_id,
        "📞 Как вы хотите поделиться номером телефона?",
        reply_markup=get_contact_inline_keyboard()
    )
    state_manager.delete_message_ids(user_id, msg.message_id)

def safe_delete_question_message(user_id):
    """Удаляет предыдущее сообщение с вопросом"""
    for msg_id in state_manager.get_messages(user_id):
        safe_delete_message(user_id, msg_id)
    state_manager.clear_messages(user_id)

def handle_navigation_commands(message):
    """Обрабатывает навигационные команды из текстовых сообщений"""
    user_id = message.chat.id
    
    if message.text == "🔙 Назад":
        # Возвращаемся на предыдущий шаг
        prev_step = state_manager.pop_step(user_id)
        if prev_step:
            restore_previous_step(user_id, prev_step)
        else:
            show_main_menu_inline(user_id)
    elif message.text == "🏠 Главное меню":
        show_main_menu_inline(user_id)

def restore_previous_step(user_id, step_info):
    """Восстанавливает предыдущий шаг"""
    step = step_info['step']
    
    if step == "interest_self" or step == "interest_invest" or step == "interest_sell":
        show_main_menu_inline(user_id)
    elif step == "budget_limit":
        ask_budget(user_id)
    elif step == "rooms":
        ask_rooms(user_id)
    elif step == "district" or step == "district_manual":
        ask_district(user_id)
    elif step == "mortgage":
        ask_mortgage(user_id)
    elif step == "name":
        ask_name(user_id)
    elif step == "property_type":
        ask_property_type(user_id)
    elif step == "sell_rooms":
        ask_sell_rooms(user_id)
    elif step == "sell_area":
        ask_sell_area(user_id)
    elif step == "sell_floor":
        ask_sell_floor(user_id)
    elif step == "sell_district":
        ask_sell_district(user_id)
    elif step == "condition":
        ask_sell_condition(user_id)
    elif step == "sell_price":
        ask_sell_price(user_id)
    elif step == "urgency":
        ask_sell_urgency(user_id)
    elif step == "share_contact" or step == "confirm_contact":
        ask_contact(user_id)
    else:
        show_main_menu_inline(user_id)

# ==================== ОБРАБОТЧИКИ КОНТАКТОВ ====================

def handle_contact(message):
    user_id = message.chat.id
    
    if message.text == "🔙 Назад":
        ask_contact(user_id)
        return
    
    if message.text == "/cancel":
        show_main_menu_inline(user_id)
        return
    
    if message.contact:
        state_manager.set_data(user_id, 'phone', message.contact.phone_number)
        state_manager.push_step(user_id, "phone")
        send_application(user_id, message)
    else:
        bot.send_message(
            user_id,
            "⚠️ Пожалуйста, используйте кнопку '📱 Отправить контакт' для отправки номера.",
            reply_markup=get_contact_request_keyboard()
        )

def handle_manual_phone(message):
    user_id = message.chat.id
    
    if message.text == "🔙 Назад":
        ask_contact(user_id)
        return
    
    if message.text == "/cancel":
        show_main_menu_inline(user_id)
        return
    
    state_manager.set_data(user_id, 'phone', message.text)
    state_manager.push_step(user_id, "phone")
    send_application(user_id, message)

def send_application(user_id, message):
    """Отправляет заявку всем администраторам и завершает диалог"""
    
    if not get_user_consent(user_id):
        remove_keyboard_silent(user_id)
        bot.send_message(
            user_id,
            "⚠️ Не найдено согласие на обработку данных. Пожалуйста, начните заново с /start",
            reply_markup=get_main_menu_keyboard()
        )
        state_manager.clear_state(user_id)
        return
    
    user_data = state_manager.get_all_data(user_id)
    interest = user_data.get('interest', '—')
    
    # Формируем сообщение в зависимости от типа заявки
    if interest == "Хочу разместить свой объект":
        answer = (
            "📝 НОВАЯ ЗАЯВКА НА ПРОДАЖУ!\n\n"
            f"👤 Имя: {user_data.get('name', '—')}\n"
            f"📞 Телефон: {user_data.get('phone', '—')}\n"
            f"🏠 Тип: {user_data.get('property_type', '—')}\n"
            f"🛏 Комнаты: {user_data.get('sell_rooms', '—')}\n"
            f"📐 Площадь: {user_data.get('sell_area', '—')} кв.м\n"
            f"🏢 Этаж: {user_data.get('sell_floor', '—')}\n"
            f"📍 Район: {user_data.get('district', '—')}\n"
            f"🔧 Состояние: {user_data.get('condition', '—')}\n"
            f"💰 Стоимость: {user_data.get('sell_price', '—')} ₽\n"
            f"⏰ Срочность: {user_data.get('urgency', '—')}\n"
            f"🆔 User ID: {user_id}\n"
            f"👤 Username: @{message.from_user.username or 'нет'}\n"
            f"✅ СОГЛАСИЕ НА ОБРАБОТКУ ДАННЫХ: получено"
        )
    else:
        answer = (
            "📝 НОВАЯ ЗАЯВКА НА ПОКУПКУ!\n\n"
            f"👤 Имя: {user_data.get('name', '—')}\n"
            f"📞 Телефон: {user_data.get('phone', '—')}\n"
            f"🏠 Интерес: {user_data.get('interest', '—')}\n"
            f"💰 Бюджет до: {user_data.get('budget_limit', '—')} ₽\n"
            f"🛏 Комнаты: {user_data.get('rooms', '—')}\n"
            f"📍 Район: {user_data.get('district', '—')}\n"
            f"🏦 Ипотека: {user_data.get('mortgage', '—')}\n"
            f"🆔 User ID: {user_id}\n"
            f"👤 Username: @{message.from_user.username or 'нет'}\n"
            f"✅ СОГЛАСИЕ НА ОБРАБОТКУ ДАННЫХ: получено"
        )
    
    # Отправляем всем администраторам
    success_count = 0
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, answer)
            success_count += 1
            logger.info(f"✅ Заявка отправлена администратору {admin_id}")
        except Exception as e:
            logger.error(f"❌ Не удалось отправить сообщение администратору {admin_id}: {e}")
    
    # Сохраняем данные в базу
    save_user_data(user_id, user_data)
    log_user_action(user_id, "application_sent")
    
    # Проверяем, удалось ли отправить хотя бы одному
    if success_count == 0:
        remove_keyboard_silent(user_id)
        bot.send_message(
            user_id,
            "⚠️ Произошла техническая ошибка. Пожалуйста, попробуйте позже.",
            reply_markup=get_main_menu_keyboard()
        )
        state_manager.clear_state(user_id)
        return
    
    # Убираем старую клавиатуру (кнопка "Отправить контакт") без отправки сообщения
    remove_keyboard_silent(user_id)
    
    bot.send_message(
        user_id,
        "✅ СПАСИБО! Ваши данные переданы нашему специалисту.\n"
        "Ожидайте звонка или сообщения в ближайшее время.\n\n"
        "📌 ВАЖНЫЕ КОМАНДЫ:\n"
        "/menu - Главное меню\n"
        "/privacy - Политика конфиденциальности\n"
        "/mydata - Мои данные\n"
        "/revoke - Отозвать согласие\n"
        "/delete_my_data - Удалить все данные",
        reply_markup=get_main_menu_keyboard()
    )
    
    state_manager.clear_state(user_id)

# ==================== ОБРАБОТЧИК ВСЕХ ОСТАЛЬНЫХ СООБЩЕНИЙ ====================

@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    user_id = message.chat.id
    
    # Проверяем, не админ ли это с меню
    if is_admin(user_id) and message.text in ["📊 Статистика", "📋 Список согласий", "💾 Создать бэкап", "📦 История бэкапов", "🔙 Выход из админ-панели"]:
        return
    
    # Проверяем навигационные команды
    if message.text in ["🔙 Назад", "🏠 Главное меню"]:
        handle_navigation_commands(message)
        return
    
    if message.text == "/cancel":
        show_main_menu_inline(user_id)
        return
    
    if user_id in state_manager._states:
        if not get_user_consent(user_id):
            remove_keyboard_silent(user_id)
            bot.send_message(
                user_id,
                "⚠️ Для работы бота необходимо дать согласие на обработку данных.\n"
                "Напишите /start для начала."
            )
            return
        
        bot.send_message(
            user_id,
            "⚠️ Пожалуйста, используйте кнопки для ответа.",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        remove_keyboard_silent(user_id)
        bot.send_message(
            user_id,
            "⚠️ Напишите /start чтобы начать."
        )

# ==================== ЗАПУСК БОТА ====================

if __name__ == '__main__':
    print("🚀 Бот запущен и работает через Long Polling...")
    print(f"📋 Токен: {BOT_TOKEN[:10]}...")
    print(f"👤 Администраторы: {ADMIN_IDS}")
    print("📌 Доступные команды:")
    print("  /start - начать работу")
    print("  /menu - главное меню")
    print("  /help - справка")
    print("  /privacy - политика конфиденциальности")
    print("  /mydata - посмотреть свои данные")
    print("  /revoke - отозвать согласие")
    print("  /delete_my_data - удалить все данные")
    print("  /admin - панель администратора")
    
    # Периодическая очистка старых данных (в фоне)
    def cleanup_scheduler():
        while True:
            try:
                time.sleep(30 * 24 * 60 * 60)  # Раз в месяц
                deleted = cleanup_old_data()
                if deleted > 0:
                    logger.info(f"🧹 Очищено {deleted} старых записей")
            except Exception as e:
                logger.error(f"❌ Ошибка в планировщике очистки: {e}")
    
    cleanup_thread = threading.Thread(target=cleanup_scheduler, daemon=True)
    cleanup_thread.start()
    
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")