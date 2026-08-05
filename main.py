import telebot
import logging
import os
from dotenv import load_dotenv
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_IDS = os.getenv('ADMIN_CHAT_IDS')

# --- ПРОВЕРКА ПЕРЕМЕННЫХ ---
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в .env файле")

if not ADMIN_CHAT_IDS:
    raise ValueError("❌ ADMIN_CHAT_IDS не найден в .env файле")

# Парсим ID администраторов (могут быть через запятую или пробел)
try:
    ADMIN_IDS = [int(id.strip()) for id in ADMIN_CHAT_IDS.replace(',', ' ').split() if id.strip()]
    if not ADMIN_IDS:
        raise ValueError("❌ Не найдены ID администраторов")
except ValueError as e:
    raise ValueError(f"❌ ADMIN_CHAT_IDS должен содержать числа, получено: {ADMIN_CHAT_IDS}")

# --- ЛОГИРОВАНИЕ ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- СОЗДАНИЕ БОТА ---
bot = telebot.TeleBot(BOT_TOKEN)

# --- ХРАНИЛИЩЕ ДАННЫХ ПОЛЬЗОВАТЕЛЕЙ ---
user_data = {}

# --- INLINE КНОПКИ ---

def get_main_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🏠 Квартира для себя", callback_data="interest_self"),
        InlineKeyboardButton("💰 Инвестиционная квартира", callback_data="interest_invest"),
        InlineKeyboardButton("📢 Хочу разместить свой объект", callback_data="interest_sell"),
        InlineKeyboardButton("👀 Просто смотрю", callback_data="interest_watch")
    )
    return keyboard

def get_rooms_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=3)
    buttons = []
    for i in range(1, 6):
        buttons.append(InlineKeyboardButton(str(i), callback_data=f"rooms_{i}"))
    buttons.append(InlineKeyboardButton("6+", callback_data="rooms_6"))
    keyboard.add(*buttons)
    return keyboard

def get_district_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🏢 Центральный", callback_data="district_central"),
        InlineKeyboardButton("🏢 Железнодорожный", callback_data="district_railway"),
        InlineKeyboardButton("🏢 Октябрьский", callback_data="district_october"),
        InlineKeyboardButton("🏢 Советский", callback_data="district_soviet"),
        InlineKeyboardButton("🏢 Ленинский", callback_data="district_lenin"),
        InlineKeyboardButton("🏢 Кировский", callback_data="district_kirov"),
        InlineKeyboardButton("🏢 Первомайский", callback_data="district_pervomay"),
        InlineKeyboardButton("🏢 Дзержинский", callback_data="district_dzerzhinsky"),
        InlineKeyboardButton("🏢 Заельцовский", callback_data="district_zaeltsovsky"),
        InlineKeyboardButton("🏢 Калининский", callback_data="district_kalinin"),
        InlineKeyboardButton("✏️ Свой вариант", callback_data="district_other")
    )
    return keyboard

def get_yes_no_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Да", callback_data="yes"),
        InlineKeyboardButton("❌ Нет", callback_data="no")
    )
    return keyboard

def get_property_type_keyboard():
    """Клавиатура для выбора типа недвижимости при продаже"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🏠 Квартира", callback_data="prop_apartment"),
        InlineKeyboardButton("🏡 Дом/Коттедж", callback_data="prop_house"),
        InlineKeyboardButton("🏢 Коммерческая", callback_data="prop_commercial"),
        InlineKeyboardButton("🏗️ Участок", callback_data="prop_land"),
        InlineKeyboardButton("✏️ Другое", callback_data="prop_other")
    )
    return keyboard

def get_condition_keyboard():
    """Клавиатура для выбора состояния объекта"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔨 Требует ремонта", callback_data="condition_bad"),
        InlineKeyboardButton("🛠️ Косметический ремонт", callback_data="condition_normal"),
        InlineKeyboardButton("✨ Евроремонт", callback_data="condition_good"),
        InlineKeyboardButton("🆕 Новостройка без отделки", callback_data="condition_no_finish"),
        InlineKeyboardButton("🏗️ Новостройка с отделкой", callback_data="condition_with_finish")
    )
    return keyboard

def get_urgency_keyboard():
    """Клавиатура для выбора срочности продажи"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("⏰ Срочно (до 1 месяца)", callback_data="urgency_very"),
        InlineKeyboardButton("🕐 В ближайшее время (1-3 месяца)", callback_data="urgency_soon"),
        InlineKeyboardButton("📅 В течение 3-6 месяцев", callback_data="urgency_medium"),
        InlineKeyboardButton("🗓️ Нет срочности (более 6 месяцев)", callback_data="urgency_no")
    )
    return keyboard

def get_contact_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📱 Поделиться номером", callback_data="share_contact"),
        InlineKeyboardButton("✏️ Ввести номер вручную", callback_data="manual_phone")
    )
    return keyboard

def get_confirm_contact_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Да, отправить", callback_data="confirm_contact_yes"),
        InlineKeyboardButton("❌ Нет, отмена", callback_data="confirm_contact_no")
    )
    return keyboard

# --- ОБРАБОТЧИК КОМАНД ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    user_data[user_id] = {}
    
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
        
        # Если квартира, спрашиваем комнаты
        if property_type == "apartment":
            ask_sell_rooms(user_id)
        else:
            # Для других типов сразу спрашиваем площадь
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
    interest = user_data[user_id].get('interest', '—')
    
    # Формируем сообщение в зависимости от типа заявки
    if interest == "Хочу разместить свой объект":
        # Заявка на продажу
        answer = (
            "📝 *Новая заявка на продажу!*\n\n"
            f"👤 *Имя:* {user_data[user_id].get('name', '—')}\n"
            f"📞 *Телефон:* {user_data[user_id].get('phone', '—')}\n"
            f"🏠 *Тип:* {user_data[user_id].get('property_type', '—')}\n"
            f"🛏 *Комнаты:* {user_data[user_id].get('sell_rooms', '—')}\n"
            f"📐 *Площадь:* {user_data[user_id].get('sell_area', '—')} кв.м\n"
            f"🏢 *Этаж:* {user_data[user_id].get('sell_floor', '—')}\n"
            f"📍 *Район:* {user_data[user_id].get('district', '—')}\n"
            f"🔧 *Состояние:* {user_data[user_id].get('condition', '—')}\n"
            f"💰 *Стоимость:* {user_data[user_id].get('sell_price', '—')} ₽\n"
            f"⏰ *Срочность:* {user_data[user_id].get('urgency', '—')}\n"
            f"🆔 *User ID:* `{user_id}`\n"
            f"👤 *Username:* @{message.from_user.username or 'нет'}"
        )
    else:
        # Заявка на покупку
        answer = (
            "📝 *Новая заявка на покупку!*\n\n"
            f"👤 *Имя:* {user_data[user_id].get('name', '—')}\n"
            f"📞 *Телефон:* {user_data[user_id].get('phone', '—')}\n"
            f"🏠 *Интерес:* {user_data[user_id].get('interest', '—')}\n"
            f"💰 *Бюджет до:* {user_data[user_id].get('budget_limit', '—')} ₽\n"
            f"🛏 *Комнаты:* {user_data[user_id].get('rooms', '—')}\n"
            f"📍 *Район:* {user_data[user_id].get('district', '—')}\n"
            f"🏦 *Ипотека:* {user_data[user_id].get('mortgage', '—')}\n"
            f"🆔 *User ID:* `{user_id}`\n"
            f"👤 *Username:* @{message.from_user.username or 'нет'}"
        )
    
    # Отправляем всем администраторам
    success_count = 0
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, answer, parse_mode='Markdown')
            success_count += 1
            logger.info(f"✅ Заявка отправлена администратору {admin_id}")
        except Exception as e:
            logger.error(f"❌ Не удалось отправить сообщение администратору {admin_id}: {e}")
    
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
        "✅ *Спасибо!* Ваши данные переданы нашему специалисту.\n"
        "Ожидайте звонка или сообщения в ближайшее время.",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
    )
    
    user_data.pop(user_id, None)

# --- ОБРАБОТЧИК ВСЕХ ОСТАЛЬНЫХ СООБЩЕНИЙ ---

@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    user_id = message.chat.id
    
    if user_id in user_data:
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
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
