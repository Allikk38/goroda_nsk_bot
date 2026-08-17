import telebot
import logging
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

from config import (
    BOT_TOKEN, ADMIN_IDS, logger, 
    CONSENT_TEXT, PRIVACY_TEXT
)
from database import (
    init_database, save_user_data, save_consent, 
    get_user_consent, get_user_data, delete_user_data,
    log_user_action, cleanup_old_data
)
from keyboards import *

# --- СОЗДАНИЕ БОТА ---
bot = telebot.TeleBot(BOT_TOKEN)

# --- ХРАНИЛИЩЕ ДАННЫХ ПОЛЬЗОВАТЕЛЕЙ (временное) ---
user_data = {}

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
init_database()

# --- ОБРАБОТЧИК КОМАНД ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    user_data[user_id] = {}
    
    # Проверяем, есть ли уже согласие в базе
    if get_user_consent(user_id):
        show_main_menu(message)
        return
    
    # Показываем запрос согласия
    msg = bot.send_message(
        user_id,
        CONSENT_TEXT,
        reply_markup=get_consent_keyboard(),
        disable_web_page_preview=True
    )
    user_data[user_id]['consent_msg_id'] = msg.message_id

@bot.message_handler(commands=['privacy'])
def handle_privacy(message):
    """Показать политику конфиденциальности"""
    try:
        bot.send_message(
            message.chat.id,
            PRIVACY_TEXT,
            disable_web_page_preview=True
        )
        logger.info(f"✅ Команда /privacy выполнена для пользователя {message.chat.id}")
    except Exception as e:
        logger.error(f"❌ Ошибка в /privacy: {e}")
        bot.send_message(
            message.chat.id,
            "⚠️ Произошла ошибка при загрузке политики конфиденциальности. Попробуйте позже."
        )

@bot.message_handler(commands=['revoke'])
def handle_revoke(message):
    """Отзыв согласия"""
    user_id = message.chat.id
    
    if not get_user_consent(user_id):
        bot.send_message(
            user_id,
            "❌ У вас нет активного согласия на обработку данных."
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
    
    user_info = get_user_data(user_id)
    if not user_info:
        bot.send_message(
            user_id,
            "❌ Ваши данные не найдены. Возможно, вы не давали согласие."
        )
        return
    
    # Формируем отчет
    report = "📋 ВАШИ ДАННЫЕ В СИСТЕМЕ:\n\n"
    
    # Показываем только то, что есть
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
            # Маскируем телефон
            if key == 'phone' and len(str(value)) >= 10:
                value = str(value)[:5] + '****' + str(value)[-3:]
            report += f"{label}: {value}\n"
            has_data = True
    
    if not has_data:
        report += "Данные не заполнены\n"
    
    # Добавляем информацию о согласии
    report += f"\n📌 СОГЛАСИЕ: {'✅ Да' if user_info.get('consent_given') else '❌ Нет'}"
    if user_info.get('consent_date'):
        report += f"\n📅 ДАТА СОГЛАСИЯ: {user_info['consent_date'][:10]}"
    
    bot.send_message(user_id, report)

@bot.message_handler(commands=['delete_my_data'])
def handle_delete_data(message):
    """Удаление всех данных пользователя"""
    user_id = message.chat.id
    
    if not get_user_consent(user_id):
        bot.send_message(
            user_id,
            "❌ У вас нет данных в системе."
        )
        return
    
    # Удаляем данные из базы
    if delete_user_data(user_id):
        # Удаляем из временного хранилища
        if user_id in user_data:
            user_data.pop(user_id, None)
        
        bot.send_message(
            user_id,
            "✅ ВСЕ ВАШИ ДАННЫЕ УСПЕШНО УДАЛЕНЫ.\n\n"
            "Если захотите воспользоваться услугами снова, напишите /start."
        )
    else:
        bot.send_message(
            user_id,
            "❌ Произошла ошибка при удалении данных. Попробуйте позже."
        )

# --- ФУНКЦИЯ ПОКАЗА ГЛАВНОГО МЕНЮ ---

def show_main_menu(message):
    """Показывает главное меню после получения согласия"""
    user_id = message.chat.id
    
    welcome_msg = bot.send_message(
        user_id,
        f"Здравствуйте, {message.from_user.first_name} | Новостройки.\n"
        "Я помощник канала «Города»\n"
        "- Мой сервис помогает жителям Новосибирска и других регионов РФ "
        "в подборе самых интересных объектов недвижимости\n\n"
        "- Ответьте на мои вопросы о ваших пожеланиях, и мы сможем подобрать лучший вариант"
    )
    
    user_data[user_id]['welcome_msg_id'] = welcome_msg.message_id
    
    question_msg = bot.send_message(
        user_id,
        "Ответьте, пожалуйста, что вас интересует?",
        reply_markup=get_main_inline_keyboard()
    )
    user_data[user_id]['question_msg_id'] = question_msg.message_id

# --- ОБРАБОТЧИК INLINE КНОПОК ---

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data
    
    # --- ОБРАБОТКА СОГЛАСИЯ ---
    if data == "consent_agree":
        # Сохраняем согласие в базу
        save_consent(user_id, True)
        
        try:
            bot.delete_message(user_id, user_data[user_id]['consent_msg_id'])
            del user_data[user_id]['consent_msg_id']
        except:
            pass
        
        # Отправляем подтверждение
        bot.send_message(
            user_id,
            "✅ СПАСИБО! ВАШЕ СОГЛАСИЕ ПОЛУЧЕНО.\n\n"
            "Теперь мы можем обрабатывать ваши данные для подбора лучших вариантов."
        )
        
        # Показываем главное меню
        class FakeMessage:
            def __init__(self, user_id, first_name):
                self.chat = type('obj', (object,), {'id': user_id})
                self.from_user = type('obj', (object,), {'first_name': first_name})
        
        first_name = call.from_user.first_name or "Пользователь"
        fake_msg = FakeMessage(user_id, first_name)
        show_main_menu(fake_msg)
        
    elif data == "consent_disagree":
        try:
            bot.delete_message(user_id, user_data[user_id]['consent_msg_id'])
            del user_data[user_id]['consent_msg_id']
        except:
            pass
        
        bot.send_message(
            user_id,
            "❌ МЫ НЕ МОЖЕМ ПРОДОЛЖАТЬ РАБОТУ БЕЗ ВАШЕГО СОГЛАСИЯ.\n\n"
            "Мы уважаем ваше право на конфиденциальность.\n"
            "Если передумаете, просто напишите /start заново."
        )
        user_data.pop(user_id, None)
        return
    
    # --- ОБРАБОТКА ОТЗЫВА СОГЛАСИЯ ---
    elif data == "revoke_confirm":
        # Отзываем согласие и удаляем данные
        save_consent(user_id, False)
        delete_user_data(user_id)
        
        if user_id in user_data:
            user_data.pop(user_id, None)
        
        bot.send_message(
            user_id,
            "✅ ВАШЕ СОГЛАСИЕ ОТОЗВАНО. ВСЕ ДАННЫЕ УДАЛЕНЫ.\n\n"
            "Если захотите воспользоваться услугами снова, напишите /start."
        )
        return
        
    elif data == "revoke_cancel":
        bot.send_message(
            user_id,
            "✅ Отзыв согласия отменен. Ваши данные сохранены."
        )
        return
    
    # --- ДАЛЬНЕЙШАЯ ОБРАБОТКА ТОЛЬКО С СОГЛАСИЕМ ---
    # Проверяем наличие согласия
    if not get_user_consent(user_id):
        bot.send_message(
            user_id,
            "⚠️ Для продолжения работы необходимо дать согласие на обработку данных.\n"
            "Напишите /start для начала."
        )
        return
    
    try:
        bot.delete_message(user_id, call.message.message_id)
    except Exception as e:
        logger.error(f"Не удалось удалить сообщение: {e}")
    
    if user_id in user_data and 'welcome_msg_id' in user_data[user_id]:
        try:
            bot.delete_message(user_id, user_data[user_id]['welcome_msg_id'])
            del user_data[user_id]['welcome_msg_id']
        except:
            pass
    
    # --- Ветка "Квартира для себя" ---
    if data == "interest_self":
        user_data[user_id]['interest'] = "Квартира для себя"
        ask_budget(user_id)
    
    # --- Ветка "Инвестиционная квартира" ---
    elif data == "interest_invest":
        user_data[user_id]['interest'] = "Инвестиционная квартира"
        ask_budget(user_id)
    
    # --- Ветка "Продажа недвижимости" ---
    elif data == "interest_sell":
        user_data[user_id]['interest'] = "Хочу разместить свой объект"
        ask_property_type(user_id)
    
    # --- Ветка "Просто смотрю" ---
    elif data == "interest_watch":
        user_data[user_id]['interest'] = "Просто смотрю"
        bot.send_message(
            user_id,
            "✅ Отлично! Мы будем держать вас в курсе новых интересных предложений.\n"
            "Подпишитесь на наш канал, чтобы не пропустить обновления!"
        )
        user_data.pop(user_id, None)
    
    # --- Вопросы для покупки ---
    elif data.startswith("rooms_"):
        rooms = data.split("_")[1]
        user_data[user_id]['rooms'] = rooms
        ask_district(user_id)
    
    elif data.startswith("district_"):
        district = data.split("_")[1]
        if district == "other":
            msg = bot.send_message(user_id, "Напишите ваш вариант района:")
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
            user_data[user_id]['district'] = district_names.get(district, district)
            ask_mortgage(user_id)
    
    elif data == "yes":
        user_data[user_id]['mortgage'] = "Да"
        ask_name(user_id)
    
    elif data == "no":
        user_data[user_id]['mortgage'] = "Нет"
        ask_name(user_id)
    
    # --- Вопросы для продажи ---
    elif data.startswith("prop_"):
        property_type = data.split("_")[1]
        property_names = {
            "apartment": "Квартира",
            "house": "Дом/Коттедж",
            "commercial": "Коммерческая недвижимость",
            "land": "Земельный участок",
            "other": "Другое"
        }
        user_data[user_id]['property_type'] = property_names.get(property_type, property_type)
        
        if property_type == "apartment":
            ask_sell_rooms(user_id)
        else:
            ask_sell_area(user_id)
    
    elif data.startswith("sell_rooms_"):
        rooms = data.split("_")[2]
        user_data[user_id]['sell_rooms'] = rooms
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
        user_data[user_id]['condition'] = condition_names.get(condition, condition)
        ask_sell_urgency(user_id)
    
    elif data.startswith("urgency_"):
        urgency = data.split("_")[1]
        urgency_names = {
            "very": "Срочно (до 1 месяца)",
            "soon": "В ближайшее время (1-3 месяца)",
            "medium": "В течение 3-6 месяцев",
            "no": "Нет срочности (более 6 месяцев)"
        }
        user_data[user_id]['urgency'] = urgency_names.get(urgency, urgency)
        ask_sell_phone(user_id)
    
    # --- Контакты ---
    elif data == "share_contact":
        msg = bot.send_message(
            user_id,
            "Вы действительно хотите поделиться своим номером телефона?",
            reply_markup=get_confirm_contact_keyboard()
        )
        user_data[user_id]['question_msg_id'] = msg.message_id
    
    elif data == "confirm_contact_yes":
        try:
            bot.delete_message(user_id, call.message.message_id)
        except:
            pass
        
        request_contact_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        contact_button = KeyboardButton("📱 Отправить контакт", request_contact=True)
        request_contact_keyboard.add(contact_button)
        
        msg = bot.send_message(
            user_id,
            "Нажмите кнопку ниже, чтобы поделиться номером телефона:",
            reply_markup=request_contact_keyboard
        )
        bot.register_next_step_handler(msg, handle_contact)
    
    elif data == "confirm_contact_no":
        try:
            bot.delete_message(user_id, call.message.message_id)
        except:
            pass
        
        msg = bot.send_message(
            user_id,
            "Выберите способ отправки номера:",
            reply_markup=get_contact_inline_keyboard()
        )
        user_data[user_id]['question_msg_id'] = msg.message_id
    
    elif data == "manual_phone":
        msg = bot.send_message(
            user_id,
            "Введите ваш номер телефона в формате +7XXXXXXXXXX:"
        )
        bot.register_next_step_handler(msg, handle_manual_phone)

# --- ФУНКЦИИ ДЛЯ ПОКУПКИ ---

def ask_budget(user_id):
    if user_id in user_data and 'question_msg_id' in user_data[user_id]:
        try:
            bot.delete_message(user_id, user_data[user_id]['question_msg_id'])
            del user_data[user_id]['question_msg_id']
        except:
            pass
    
    msg = bot.send_message(user_id, "Выше какой стоимости объекты не предлагать?\n(Введите сумму в рублях)")
    bot.register_next_step_handler(msg, handle_budget_limit)

def handle_budget_limit(message):
    user_id = message.chat.id
    user_data[user_id]['budget_limit'] = message.text
    
    msg = bot.send_message(
        user_id,
        "Сколько комнат вы хотите в будущей квартире?",
        reply_markup=get_rooms_inline_keyboard()
    )
    user_data[user_id]['question_msg_id'] = msg.message_id

def ask_district(user_id):
    if user_id in user_data and 'question_msg_id' in user_data[user_id]:
        try:
            bot.delete_message(user_id, user_data[user_id]['question_msg_id'])
            del user_data[user_id]['question_msg_id']
        except:
            pass
    
    msg = bot.send_message(
        user_id,
        "Выберите предпочтительный район:",
        reply_markup=get_district_inline_keyboard()
    )
    user_data[user_id]['question_msg_id'] = msg.message_id

def handle_district_manual(message):
    user_id = message.chat.id
    user_data[user_id]['district'] = message.text
    
    if user_id in user_data and 'question_msg_id' in user_data[user_id]:
        try:
            bot.delete_message(user_id, user_data[user_id]['question_msg_id'])
            del user_data[user_id]['question_msg_id']
        except:
            pass
    
    ask_mortgage(user_id)

def ask_mortgage(user_id):
    if user_id in user_data and 'question_msg_id' in user_data[user_id]:
        try:
            bot.delete_message(user_id, user_data[user_id]['question_msg_id'])
            del user_data[user_id]['question_msg_id']
        except:
            pass
    
    msg = bot.send_message(
        user_id,
        "Нужна ли вам ипотека?",
        reply_markup=get_yes_no_inline_keyboard()
    )
    user_data[user_id]['question_msg_id'] = msg.message_id

# --- ФУНКЦИИ ДЛЯ ПРОДАЖИ ---

def ask_property_type(user_id):
    """Вопрос 1: Тип недвижимости"""
    if user_id in user_data and 'question_msg_id' in user_data[user_id]:
        try:
            bot.delete_message(user_id, user_data[user_id]['question_msg_id'])
            del user_data[user_id]['question_msg_id']
        except:
            pass
    
    msg = bot.send_message(
        user_id,
        "Какой тип недвижимости вы хотите продать?",
        reply_markup=get_property_type_keyboard()
    )
    user_data[user_id]['question_msg_id'] = msg.message_id

def ask_sell_rooms(user_id):
    """Вопрос 2: Количество комнат (для квартиры)"""
    if user_id in user_data and 'question_msg_id' in user_data[user_id]:
        try:
            bot.delete_message(user_id, user_data[user_id]['question_msg_id'])
            del user_data[user_id]['question_msg_id']
        except:
            pass
    
    keyboard = InlineKeyboardMarkup(row_width=3)
    buttons = []
    for i in range(1, 6):
        buttons.append(InlineKeyboardButton(str(i), callback_data=f"sell_rooms_{i}"))
    buttons.append(InlineKeyboardButton("6+", callback_data="sell_rooms_6"))
    buttons.append(InlineKeyboardButton("Студия", callback_data="sell_rooms_studio"))
    keyboard.add(*buttons)
    
    msg = bot.send_message(
        user_id,
        "Сколько комнат в вашей квартире?",
        reply_markup=keyboard
    )
    user_data[user_id]['question_msg_id'] = msg.message_id

def ask_sell_area(user_id):
    """Вопрос 3: Общая площадь"""
    if user_id in user_data and 'question_msg_id' in user_data[user_id]:
        try:
            bot.delete_message(user_id, user_data[user_id]['question_msg_id'])
            del user_data[user_id]['question_msg_id']
        except:
            pass
    
    msg = bot.send_message(
        user_id,
        "Какая общая площадь вашего объекта? (в кв.м)\n"
        "Введите число:"
    )
    bot.register_next_step_handler(msg, handle_sell_area)

def handle_sell_area(message):
    user_id = message.chat.id
    user_data[user_id]['sell_area'] = message.text
    ask_sell_floor(message)

def ask_sell_floor(message):
    """Вопрос 4: Этаж и этажность"""
    user_id = message.chat.id
    
    msg = bot.send_message(
        user_id,
        "На каком этаже находится объект и сколько этажей в доме?\n"
        "Например: 3/9 или 1/5"
    )
    bot.register_next_step_handler(msg, handle_sell_floor)

def handle_sell_floor(message):
    user_id = message.chat.id
    user_data[user_id]['sell_floor'] = message.text
    ask_sell_district(user_id)

def ask_sell_district(user_id):
    """Вопрос 5: Район"""
    if user_id in user_data and 'question_msg_id' in user_data[user_id]:
        try:
            bot.delete_message(user_id, user_data[user_id]['question_msg_id'])
            del user_data[user_id]['question_msg_id']
        except:
            pass
    
    msg = bot.send_message(
        user_id,
        "В каком районе находится ваш объект?",
        reply_markup=get_district_inline_keyboard()
    )
    user_data[user_id]['question_msg_id'] = msg.message_id

def ask_sell_condition(user_id):
    """Вопрос 6: Состояние"""
    if user_id in user_data and 'question_msg_id' in user_data[user_id]:
        try:
            bot.delete_message(user_id, user_data[user_id]['question_msg_id'])
            del user_data[user_id]['question_msg_id']
        except:
            pass
    
    msg = bot.send_message(
        user_id,
        "Какое состояние у объекта?",
        reply_markup=get_condition_keyboard()
    )
    user_data[user_id]['question_msg_id'] = msg.message_id

def ask_sell_price(user_id):
    """Вопрос 7: Стоимость"""
    if user_id in user_data and 'question_msg_id' in user_data[user_id]:
        try:
            bot.delete_message(user_id, user_data[user_id]['question_msg_id'])
            del user_data[user_id]['question_msg_id']
        except:
            pass
    
    msg = bot.send_message(
        user_id,
        "Какую стоимость вы хотите указать?\n"
        "Введите сумму в рублях:"
    )
    bot.register_next_step_handler(msg, handle_sell_price)

def handle_sell_price(message):
    user_id = message.chat.id
    user_data[user_id]['sell_price'] = message.text
    ask_sell_urgency(user_id)

def ask_sell_urgency(user_id):
    """Вопрос 8: Срочность продажи"""
    if user_id in user_data and 'question_msg_id' in user_data[user_id]:
        try:
            bot.delete_message(user_id, user_data[user_id]['question_msg_id'])
            del user_data[user_id]['question_msg_id']
        except:
            pass
    
    msg = bot.send_message(
        user_id,
        "Насколько срочно вы хотите продать?",
        reply_markup=get_urgency_keyboard()
    )
    user_data[user_id]['question_msg_id'] = msg.message_id

def ask_sell_phone(user_id):
    """Вопрос 9: Контакт для связи"""
    if user_id in user_data and 'question_msg_id' in user_data[user_id]:
        try:
            bot.delete_message(user_id, user_data[user_id]['question_msg_id'])
            del user_data[user_id]['question_msg_id']
        except:
            pass
    
    msg = bot.send_message(
        user_id,
        "Как с вами связаться?",
        reply_markup=get_contact_inline_keyboard()
    )
    user_data[user_id]['question_msg_id'] = msg.message_id

# --- ОБЩИЕ ФУНКЦИИ ---

def ask_name(user_id):
    """Запрос имени (для покупки)"""
    if user_id in user_data and 'question_msg_id' in user_data[user_id]:
        try:
            bot.delete_message(user_id, user_data[user_id]['question_msg_id'])
            del user_data[user_id]['question_msg_id']
        except:
            pass
    
    msg = bot.send_message(user_id, "Как Вас зовут?")
    bot.register_next_step_handler(msg, handle_name)

def handle_name(message):
    user_id = message.chat.id
    user_data[user_id]['name'] = message.text
    
    msg = bot.send_message(
        user_id,
        "Как вы хотите поделиться номером телефона?",
        reply_markup=get_contact_inline_keyboard()
    )
    user_data[user_id]['question_msg_id'] = msg.message_id

# --- ОБРАБОТЧИКИ КОНТАКТОВ ---

def handle_contact(message):
    user_id = message.chat.id
    
    if message.contact:
        user_data[user_id]['phone'] = message.contact.phone_number
        send_application(user_id, message)
    else:
        bot.send_message(
            user_id,
            "Пожалуйста, используйте кнопку '📱 Отправить контакт' для отправки номера."
        )

def handle_manual_phone(message):
    user_id = message.chat.id
    user_data[user_id]['phone'] = message.text
    send_application(user_id, message)

def send_application(user_id, message):
    """Отправляет заявку всем администраторам и завершает диалог"""
    
    # Проверяем наличие согласия в базе
    if not get_user_consent(user_id):
        bot.send_message(
            user_id,
            "⚠️ Не найдено согласие на обработку данных. Пожалуйста, начните заново с /start"
        )
        user_data.pop(user_id, None)
        return
    
    interest = user_data[user_id].get('interest', '—')
    
    # Формируем сообщение в зависимости от типа заявки
    if interest == "Хочу разместить свой объект":
        # Заявка на продажу
        answer = (
            "📝 НОВАЯ ЗАЯВКА НА ПРОДАЖУ!\n\n"
            f"👤 Имя: {user_data[user_id].get('name', '—')}\n"
            f"📞 Телефон: {user_data[user_id].get('phone', '—')}\n"
            f"🏠 Тип: {user_data[user_id].get('property_type', '—')}\n"
            f"🛏 Комнаты: {user_data[user_id].get('sell_rooms', '—')}\n"
            f"📐 Площадь: {user_data[user_id].get('sell_area', '—')} кв.м\n"
            f"🏢 Этаж: {user_data[user_id].get('sell_floor', '—')}\n"
            f"📍 Район: {user_data[user_id].get('district', '—')}\n"
            f"🔧 Состояние: {user_data[user_id].get('condition', '—')}\n"
            f"💰 Стоимость: {user_data[user_id].get('sell_price', '—')} ₽\n"
            f"⏰ Срочность: {user_data[user_id].get('urgency', '—')}\n"
            f"🆔 User ID: {user_id}\n"
            f"👤 Username: @{message.from_user.username or 'нет'}\n"
            f"✅ СОГЛАСИЕ НА ОБРАБОТКУ ДАННЫХ: получено"
        )
    else:
        # Заявка на покупку
        answer = (
            "📝 НОВАЯ ЗАЯВКА НА ПОКУПКУ!\n\n"
            f"👤 Имя: {user_data[user_id].get('name', '—')}\n"
            f"📞 Телефон: {user_data[user_id].get('phone', '—')}\n"
            f"🏠 Интерес: {user_data[user_id].get('interest', '—')}\n"
            f"💰 Бюджет до: {user_data[user_id].get('budget_limit', '—')} ₽\n"
            f"🛏 Комнаты: {user_data[user_id].get('rooms', '—')}\n"
            f"📍 Район: {user_data[user_id].get('district', '—')}\n"
            f"🏦 Ипотека: {user_data[user_id].get('mortgage', '—')}\n"
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
    save_user_data(user_id, user_data[user_id])
    log_user_action(user_id, "application_sent")
    
    # Проверяем, удалось ли отправить хотя бы одному
    if success_count == 0:
        bot.send_message(
            user_id,
            "⚠️ Произошла техническая ошибка. Пожалуйста, попробуйте позже."
        )
        user_data.pop(user_id, None)
        return
    
    bot.send_message(
        user_id,
        "✅ СПАСИБО! Ваши данные переданы нашему специалисту.\n"
        "Ожидайте звонка или сообщения в ближайшее время.\n\n"
        "📌 ВАЖНЫЕ КОМАНДЫ:\n"
        "/privacy - политика конфиденциальности\n"
        "/mydata - посмотреть свои данные\n"
        "/revoke - отозвать согласие\n"
        "/delete_my_data - удалить все данные",
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
    )
    
    user_data.pop(user_id, None)

# --- ОБРАБОТЧИК ВСЕХ ОСТАЛЬНЫХ СООБЩЕНИЙ ---

@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    user_id = message.chat.id
    
    if user_id in user_data:
        # Проверяем, есть ли согласие
        if not get_user_consent(user_id):
            bot.send_message(
                user_id,
                "⚠️ Для работы бота необходимо дать согласие на обработку данных.\n"
                "Напишите /start для начала."
            )
            return
        
        bot.send_message(
            user_id,
            "⚠️ Пожалуйста, используйте кнопки для ответа."
        )
    else:
        bot.send_message(
            user_id,
            "⚠️ Напишите /start чтобы начать."
        )

# --- ЗАПУСК БОТА ---

if __name__ == '__main__':
    print("🚀 Бот запущен и работает через Long Polling...")
    print(f"📋 Токен: {BOT_TOKEN[:10]}...")
    print(f"👤 Администраторы: {ADMIN_IDS}")
    print("📌 Доступные команды:")
    print("  /start - начать работу")
    print("  /privacy - политика конфиденциальности")
    print("  /mydata - посмотреть свои данные")
    print("  /revoke - отозвать согласие")
    print("  /delete_my_data - удалить все данные")
    
    # Периодическая очистка старых данных (в фоне)
    import threading
    import time
    
    def cleanup_scheduler():
        while True:
            try:
                time.sleep(30 * 24 * 60 * 60)  # Раз в месяц
                deleted = cleanup_old_data()
                if deleted > 0:
                    logger.info(f"🧹 Очищено {deleted} старых записей")
            except Exception as e:
                logger.error(f"❌ Ошибка в планировщике очистки: {e}")
    
    # Запускаем очистку в фоновом потоке
    cleanup_thread = threading.Thread(target=cleanup_scheduler, daemon=True)
    cleanup_thread.start()
    
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
