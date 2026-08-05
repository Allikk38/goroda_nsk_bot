import telebot
import logging
import os
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# --- ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')  # или os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в переменных окружения")
if ':' not in BOT_TOKEN:
    raise ValueError(f"❌ Неверный формат токена: {BOT_TOKEN}")

ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID')
if not ADMIN_CHAT_ID:
    raise ValueError("❌ ADMIN_CHAT_ID не найден в переменных окружения")
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

# --- КНОПКИ ---
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(KeyboardButton("Квартира для себя"))
    keyboard.add(KeyboardButton("Инвестиционная квартира"))
    keyboard.add(KeyboardButton("Хочу разместить свой объект"))
    keyboard.add(KeyboardButton("Просто смотрю"))
    return keyboard

def get_rooms_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for i in range(1, 6):
        keyboard.add(KeyboardButton(str(i)))
    return keyboard

def get_yes_no_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(KeyboardButton("Да"), KeyboardButton("Нет"))
    return keyboard

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
        "- Ответьте на мои вопросы о ваших пожеланиях, и мы сможем подобрать лучший вариант"
    )
    
    bot.send_message(
        user_id,
        "Ответьте, пожалуйста, что вас интересует?",
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text in ["Квартира для себя", "Инвестиционная квартира", "Хочу разместить свой объект", "Просто смотрю"])
def handle_interest(message):
    user_id = message.chat.id
    user_data[user_id]['interest'] = message.text
    
    # Если пользователь просто смотрит - пропускаем вопросы
    if message.text == "Просто смотрю":
        bot.send_message(
            user_id,
            "✅ Отлично! Мы будем держать вас в курсе новых интересных предложений.\n"
            "Подпишитесь на наш канал, чтобы не пропустить обновления!"
        )
        user_data.pop(user_id, None)
        return
    
    msg = bot.send_message(user_id, "Выше какой стоимости объекты не предлагать?\n(Введите сумму в рублях)")
    bot.register_next_step_handler(msg, handle_budget_limit)

def handle_budget_limit(message):
    user_id = message.chat.id
    user_data[user_id]['budget_limit'] = message.text
    
    msg = bot.send_message(
        user_id,
        "Сколько комнат вы хотите в будущей квартире?",
        reply_markup=get_rooms_keyboard()
    )
    bot.register_next_step_handler(msg, handle_rooms)

def handle_rooms(message):
    user_id = message.chat.id
    user_data[user_id]['rooms'] = message.text
    
    msg = bot.send_message(user_id, "Какой район для вас предпочтителен?")
    bot.register_next_step_handler(msg, handle_district)

def handle_district(message):
    user_id = message.chat.id
    user_data[user_id]['district'] = message.text
    
    msg = bot.send_message(
        user_id, 
        "Нужна ли вам ипотека?", 
        reply_markup=get_yes_no_keyboard()
    )
    bot.register_next_step_handler(msg, handle_mortgage)

def handle_mortgage(message):
    user_id = message.chat.id
    user_data[user_id]['mortgage'] = message.text
    
    msg = bot.send_message(user_id, "Как Вас зовут?")
    bot.register_next_step_handler(msg, handle_name)

def handle_name(message):
    user_id = message.chat.id
    user_data[user_id]['name'] = message.text
    
    msg = bot.send_message(
        user_id, 
        "Напишите свой номер телефона, и мы сразу включимся в работу!"
    )
    bot.register_next_step_handler(msg, handle_phone)

def handle_phone(message):
    user_id = message.chat.id
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
            "⚠️ Произошла техническая ошибка. Пожалуйста, попробуйте позже."
        )
        user_data.pop(user_id, None)
        return
    
    bot.send_message(
        user_id,
        "✅ *Спасибо!* Ваши данные переданы нашему специалисту.\n"
        "Ожидайте звонка или сообщения в ближайшее время.",
        parse_mode='Markdown'
    )
    
    user_data.pop(user_id, None)

# --- ОБРАБОТКА НЕИЗВЕСТНЫХ СООБЩЕНИЙ ---
@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    bot.send_message(
        message.chat.id,
        "⚠️ Пожалуйста, используйте кнопки для ответа или напишите /start чтобы начать заново."
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
