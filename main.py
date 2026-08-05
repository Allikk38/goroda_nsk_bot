import telebot
import logging
import os
from dotenv import load_dotenv
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

load_dotenv()

# --- ПРОВЕРКА ПЕРЕМЕННЫХ ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в .env файле")
if ':' not in BOT_TOKEN:
    raise ValueError(f"❌ Неверный формат токена: {BOT_TOKEN}")

ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
if not ADMIN_CHAT_ID:
    raise ValueError("❌ ADMIN_CHAT_ID не найден в .env файле")
try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID.strip())
except ValueError:
    raise ValueError(f"❌ ADMIN_CHAT_ID должен быть числом, получено: {ADMIN_CHAT_ID}")

# --- ЛОГИРОВАНИЕ ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- СОЗДАНИЕ БОТА ---
bot = telebot.TeleBot(BOT_TOKEN)

# --- ХРАНИЛИЩЕ ДАННЫХ ПОЛЬЗОВАТЕЛЕЙ ---
user_data = {}

# --- КНОПКИ (все с параметром one_time_keyboard=False для постоянного отображения) ---

def get_main_keyboard():
    """Главное меню выбора интереса"""
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True, 
        one_time_keyboard=False  # Кнопки остаются после нажатия
    )
    keyboard.add(KeyboardButton("Квартира для себя"))
    keyboard.add(KeyboardButton("Инвестиционная квартира"))
    keyboard.add(KeyboardButton("Хочу разместить свой объект"))
    keyboard.add(KeyboardButton("Просто смотрю"))
    return keyboard

def get_rooms_keyboard():
    """Клавиатура для выбора количества комнат"""
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True, 
        one_time_keyboard=False
    )
    # Добавляем кнопки в два ряда
    row1 = [KeyboardButton("1"), KeyboardButton("2"), KeyboardButton("3")]
    row2 = [KeyboardButton("4"), KeyboardButton("5"), KeyboardButton("6+")]
    keyboard.row(*row1)
    keyboard.row(*row2)
    return keyboard

def get_yes_no_keyboard():
    """Клавиатура Да/Нет"""
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True, 
        one_time_keyboard=False
    )
    keyboard.add(KeyboardButton("Да"), KeyboardButton("Нет"))
    return keyboard

def get_contact_keyboard():
    """Клавиатура с кнопкой для отправки контакта"""
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True, 
        one_time_keyboard=True  # Скрываем после использования
    )
    # Создаем кнопку с запросом контакта
    contact_button = KeyboardButton(
        "📱 Поделиться номером", 
        request_contact=True  # Это ключевой параметр для отправки контакта
    )
    keyboard.add(contact_button)
    
    # Добавляем кнопку для ручного ввода (на случай, если пользователь не хочет делиться контактом)
    keyboard.add(KeyboardButton("✏️ Ввести номер вручную"))
    return keyboard

def remove_keyboard():
    """Убирает клавиатуру"""
    return ReplyKeyboardRemove()

# --- ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    user_data[user_id] = {}
    
    bot.send_message(
        user_id,
        f"Здравствуйте, {message.from_user.first_name} | Новостройки.\n"
        "Я помощник канала «Города»\n"
        "- Мой сервис помогает жителям Новосибирска и других регионов РФ "
        "в подборе самых интересных объектов недвижимости\n\n"
        "- Ответьте на мои вопросы о ваших пожеланиях, и мы сможем подобрать лучший вариант",
        reply_markup=remove_keyboard()  # Убираем старую клавиатуру при старте
    )
    
    bot.send_message(
        user_id,
        "Ответьте, пожалуйста, что вас интересует?",
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text in [
    "Квартира для себя", 
    "Инвестиционная квартира", 
    "Хочу разместить свой объект", 
    "Просто смотрю"
])
def handle_interest(message):
    user_id = message.chat.id
    user_data[user_id]['interest'] = message.text
    
    # Если пользователь просто смотрит - пропускаем вопросы
    if message.text == "Просто смотрю":
        bot.send_message(
            user_id,
            "✅ Отлично! Мы будем держать вас в курсе новых интересных предложений.\n"
            "Подпишитесь на наш канал, чтобы не пропустить обновления!",
            reply_markup=remove_keyboard()  # Убираем клавиатуру
        )
        user_data.pop(user_id, None)
        return
    
    msg = bot.send_message(
        user_id, 
        "Выше какой стоимости объекты не предлагать?\n(Введите сумму в рублях)",
        reply_markup=remove_keyboard()  # Убираем клавиатуру перед вводом текста
    )
    bot.register_next_step_handler(msg, handle_budget_limit)

def handle_budget_limit(message):
    user_id = message.chat.id
    user_data[user_id]['budget_limit'] = message.text
    
    msg = bot.send_message(
        user_id,
        "Сколько комнат вы хотите в будущей квартире?",
        reply_markup=get_rooms_keyboard()  # Показываем кнопки с комнатами
    )
    bot.register_next_step_handler(msg, handle_rooms)

def handle_rooms(message):
    user_id = message.chat.id
    user_data[user_id]['rooms'] = message.text
    
    msg = bot.send_message(
        user_id, 
        "Какой район для вас предпочтителен?",
        reply_markup=remove_keyboard()  # Убираем клавиатуру перед вводом текста
    )
    bot.register_next_step_handler(msg, handle_district)

def handle_district(message):
    user_id = message.chat.id
    user_data[user_id]['district'] = message.text
    
    msg = bot.send_message(
        user_id, 
        "Нужна ли вам ипотека?", 
        reply_markup=get_yes_no_keyboard()  # Показываем кнопки Да/Нет
    )
    bot.register_next_step_handler(msg, handle_mortgage)

def handle_mortgage(message):
    user_id = message.chat.id
    user_data[user_id]['mortgage'] = message.text
    
    msg = bot.send_message(
        user_id, 
        "Как Вас зовут?",
        reply_markup=remove_keyboard()  # Убираем клавиатуру перед вводом текста
    )
    bot.register_next_step_handler(msg, handle_name)

def handle_name(message):
    user_id = message.chat.id
    user_data[user_id]['name'] = message.text
    
    msg = bot.send_message(
        user_id, 
        "Поделитесь своим номером телефона, и мы сразу включимся в работу!\n"
        "Нажмите кнопку ниже или введите номер вручную:",
        reply_markup=get_contact_keyboard()  # Показываем кнопку с контактом
    )
    bot.register_next_step_handler(msg, handle_phone_or_contact)

def handle_phone_or_contact(message):
    """Обработчик для номера телефона (кнопка контакта или ручной ввод)"""
    user_id = message.chat.id
    
    # Проверяем, пришел ли контакт
    if message.contact:
        # Если пользователь поделился контактом через кнопку
        phone = message.contact.phone_number
        user_data[user_id]['phone'] = phone
        logger.info(f"Получен контакт от {user_id}: {phone}")
    else:
        # Если пользователь ввел номер вручную
        user_data[user_id]['phone'] = message.text
    
    # Отправка администратору
    answer = (
        "📝 *Новая заявка с канала «Города»*\n\n"
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
    
    try:
        bot.send_message(ADMIN_CHAT_ID, answer, parse_mode='Markdown')
        logger.info(f"Заявка отправлена администратору {ADMIN_CHAT_ID}")
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение администратору: {e}")
        bot.send_message(
            user_id,
            "⚠️ Произошла техническая ошибка. Пожалуйста, попробуйте позже.",
            reply_markup=remove_keyboard()
        )
        user_data.pop(user_id, None)
        return
    
    bot.send_message(
        user_id,
        "✅ *Спасибо!* Ваши данные переданы нашему специалисту.\n"
        "Ожидайте звонка или сообщения в ближайшее время.",
        parse_mode='Markdown',
        reply_markup=remove_keyboard()  # Убираем клавиатуру после завершения
    )
    
    user_data.pop(user_id, None)

# --- ОБРАБОТКА ОШИБОК ---

@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    bot.send_message(
        message.chat.id,
        "⚠️ Пожалуйста, используйте кнопки для ответа или напишите /start чтобы начать заново.",
        reply_markup=get_main_keyboard()  # Показываем главное меню
    )

# --- ЗАПУСК БОТА ---

if __name__ == '__main__':
    print("🚀 Бот запущен и работает через Long Polling...")
    print(f"📋 Токен: {BOT_TOKEN[:10]}...")
    print(f"👤 Администратор: {ADMIN_CHAT_ID}")
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
