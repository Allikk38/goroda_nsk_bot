import telebot
import logging
import os
from dotenv import load_dotenv
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID'))

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

def get_contact_keyboard():
    """Клавиатура с кнопкой для отправки контакта"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    # Кнопка с запросом контакта
    contact_button = KeyboardButton("📱 Поделиться номером", request_contact=True)
    keyboard.add(contact_button)
    # Кнопка для ручного ввода
    keyboard.add(KeyboardButton("✏️ Ввести номер вручную"))
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
    
    msg = bot.send_message(user_id, "Выше какой стоимости объекты не предлагать?")
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
    
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(KeyboardButton("Да"), KeyboardButton("Нет"))
    
    msg = bot.send_message(user_id, "Нужна ли вам ипотека?", reply_markup=keyboard)
    bot.register_next_step_handler(msg, handle_mortgage)

def handle_mortgage(message):
    user_id = message.chat.id
    user_data[user_id]['mortgage'] = message.text
    
    msg = bot.send_message(user_id, "Как Вас зовут?")
    bot.register_next_step_handler(msg, handle_name)

def handle_name(message):
    user_id = message.chat.id
    user_data[user_id]['name'] = message.text
    
    # Показываем клавиатуру с кнопкой для отправки контакта
    msg = bot.send_message(
        user_id, 
        "Поделитесь своим номером телефона, и мы сразу включимся в работу!\n"
        "Нажмите кнопку ниже или введите номер вручную:",
        reply_markup=get_contact_keyboard()
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
    
    bot.send_message(ADMIN_CHAT_ID, answer, parse_mode='Markdown')
    
    bot.send_message(
        user_id,
        "✅ *Спасибо!* Ваши данные переданы нашему специалисту.\n"
        "Ожидайте звонка или сообщения в ближайшее время.",
        parse_mode='Markdown'
    )
    
    user_data.pop(user_id, None)

# --- ЗАПУСК БОТА (LONG POLLING) ---
if __name__ == '__main__':
    print("🚀 Бот запущен и работает через Long Polling...")
    bot.infinity_polling()
