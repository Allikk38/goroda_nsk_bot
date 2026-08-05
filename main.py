import telebot
import logging
import os
from dotenv import load_dotenv
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

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

# --- INLINE КНОПКИ (под сообщениями) ---

def get_main_inline_keyboard():
    """Inline-кнопки для главного меню"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🏠 Квартира для себя", callback_data="interest_self"),
        InlineKeyboardButton("💰 Инвестиционная квартира", callback_data="interest_invest"),
        InlineKeyboardButton("📢 Хочу разместить свой объект", callback_data="interest_place"),
        InlineKeyboardButton("👀 Просто смотрю", callback_data="interest_watch")
    )
    return keyboard

def get_rooms_inline_keyboard():
    """Inline-кнопки для выбора комнат"""
    keyboard = InlineKeyboardMarkup(row_width=3)
    buttons = []
    for i in range(1, 6):
        buttons.append(InlineKeyboardButton(str(i), callback_data=f"rooms_{i}"))
    buttons.append(InlineKeyboardButton("6+", callback_data="rooms_6"))
    keyboard.add(*buttons)
    return keyboard

def get_yes_no_inline_keyboard():
    """Inline-кнопки Да/Нет"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Да", callback_data="yes"),
        InlineKeyboardButton("❌ Нет", callback_data="no")
    )
    return keyboard

def get_contact_inline_keyboard():
    """Inline-кнопка для отправки контакта"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📱 Поделиться номером", callback_data="share_contact"),
        InlineKeyboardButton("✏️ Ввести номер вручную", callback_data="manual_phone")
    )
    return keyboard

# --- ОБРАБОТЧИК КОМАНД ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    user_data[user_id] = {}
    
    # Отправляем приветственное сообщение
    welcome_msg = bot.send_message(
        user_id,
        f"Здравствуйте, {message.from_user.first_name} | Новостройки.\n"
        "Я помощник канала «Города»\n"
        "- Мой сервис помогает жителям Новосибирска и других регионов РФ "
        "в подборе самых интересных объектов недвижимости\n\n"
        "- Ответьте на мои вопросы о ваших пожеланиях, и мы сможем подобрать лучший вариант"
    )
    
    # Сохраняем ID приветственного сообщения
    user_data[user_id]['welcome_msg_id'] = welcome_msg.message_id
    
    # Отправляем вопрос с кнопками
    question_msg = bot.send_message(
        user_id,
        "Ответьте, пожалуйста, что вас интересует?",
        reply_markup=get_main_inline_keyboard()
    )
    
    # Сохраняем ID сообщения с вопросом
    user_data[user_id]['question_msg_id'] = question_msg.message_id

# --- ОБРАБОТЧИК INLINE КНОПОК ---

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data
    
    # Удаляем сообщение с вопросом и кнопками
    try:
        bot.delete_message(user_id, call.message.message_id)
    except Exception as e:
        logger.error(f"Не удалось удалить сообщение: {e}")
    
    # Удаляем приветственное сообщение (если оно еще есть)
    if user_id in user_data and 'welcome_msg_id' in user_data[user_id]:
        try:
            bot.delete_message(user_id, user_data[user_id]['welcome_msg_id'])
            del user_data[user_id]['welcome_msg_id']
        except:
            pass
    
    # Обрабатываем выбор
    if data == "interest_self":
        user_data[user_id]['interest'] = "Квартира для себя"
        ask_budget(user_id, call.message)
        
    elif data == "interest_invest":
        user_data[user_id]['interest'] = "Инвестиционная квартира"
        ask_budget(user_id, call.message)
        
    elif data == "interest_place":
        user_data[user_id]['interest'] = "Хочу разместить свой объект"
        ask_budget(user_id, call.message)
        
    elif data == "interest_watch":
        user_data[user_id]['interest'] = "Просто смотрю"
        bot.send_message(
            user_id,
            "✅ Отлично! Мы будем держать вас в курсе новых интересных предложений.\n"
            "Подпишитесь на наш канал, чтобы не пропустить обновления!"
        )
        user_data.pop(user_id, None)
        
    elif data.startswith("rooms_"):
        rooms = data.split("_")[1]
        user_data[user_id]['rooms'] = rooms
        ask_district(user_id)
        
    elif data == "yes":
        user_data[user_id]['mortgage'] = "Да"
        ask_name(user_id)
        
    elif data == "no":
        user_data[user_id]['mortgage'] = "Нет"
        ask_name(user_id)
        
    elif data == "share_contact":
        # Показываем кнопку запроса контакта на клавиатуре
        request_contact_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        contact_button = KeyboardButton("📱 Отправить контакт", request_contact=True)
        request_contact_keyboard.add(contact_button)
        
        msg = bot.send_message(
            user_id,
            "Нажмите кнопку ниже, чтобы поделиться номером телефона:",
            reply_markup=request_contact_keyboard
        )
        bot.register_next_step_handler(msg, handle_contact)
        
    elif data == "manual_phone":
        msg = bot.send_message(
            user_id,
            "Введите ваш номер телефона в формате +7XXXXXXXXXX:",
            reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
        )
        bot.register_next_step_handler(msg, handle_manual_phone)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def ask_budget(user_id, message):
    """Запрос бюджета"""
    msg = bot.send_message(user_id, "Выше какой стоимости объекты не предлагать?\n(Введите сумму в рублях)")
    bot.register_next_step_handler(msg, handle_budget_limit)

def handle_budget_limit(message):
    user_id = message.chat.id
    user_data[user_id]['budget_limit'] = message.text
    
    # Отправляем вопрос с кнопками
    msg = bot.send_message(
        user_id,
        "Сколько комнат вы хотите в будущей квартире?",
        reply_markup=get_rooms_inline_keyboard()
    )
    # Сохраняем ID сообщения для возможного удаления
    user_data[user_id]['question_msg_id'] = msg.message_id

def ask_district(user_id):
    """Запрос района"""
    # Удаляем предыдущее сообщение с кнопками (если оно есть)
    if user_id in user_data and 'question_msg_id' in user_data[user_id]:
        try:
            bot.delete_message(user_id, user_data[user_id]['question_msg_id'])
            del user_data[user_id]['question_msg_id']
        except:
            pass
    
    msg = bot.send_message(user_id, "Какой район для вас предпочтителен?")
    bot.register_next_step_handler(msg, handle_district)

def handle_district(message):
    user_id = message.chat.id
    user_data[user_id]['district'] = message.text
    
    # Отправляем вопрос с кнопками
    msg = bot.send_message(
        user_id,
        "Нужна ли вам ипотека?",
        reply_markup=get_yes_no_inline_keyboard()
    )
    # Сохраняем ID сообщения для возможного удаления
    user_data[user_id]['question_msg_id'] = msg.message_id

def ask_name(user_id):
    """Запрос имени"""
    # Удаляем предыдущее сообщение с кнопками (если оно есть)
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
    
    # Отправляем вопрос с кнопками
    msg = bot.send_message(
        user_id,
        "Как вы хотите поделиться номером телефона?",
        reply_markup=get_contact_inline_keyboard()
    )
    # Сохраняем ID сообщения для возможного удаления
    user_data[user_id]['question_msg_id'] = msg.message_id

# --- ОБРАБОТЧИКИ КОНТАКТОВ ---

def handle_contact(message):
    """Обработчик для отправки контакта через клавиатуру"""
    user_id = message.chat.id
    
    if message.contact:
        user_data[user_id]['phone'] = message.contact.phone_number
        send_application(user_id, message)
    else:
        # Если пользователь не отправил контакт, а просто написал текст
        bot.send_message(
            user_id,
            "Пожалуйста, используйте кнопку '📱 Отправить контакт' для отправки номера."
        )

def handle_manual_phone(message):
    """Обработчик для ручного ввода номера"""
    user_id = message.chat.id
    user_data[user_id]['phone'] = message.text
    send_application(user_id, message)

def send_application(user_id, message):
    """Отправляет заявку администратору и завершает диалог"""
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
        logger.error(f"Ошибка отправки администратору: {e}")
        bot.send_message(
            user_id,
            "⚠️ Произошла техническая ошибка. Пожалуйста, попробуйте позже."
        )
        user_data.pop(user_id, None)
        return
    
    # Убираем ReplyKeyboard если она есть
    bot.send_message(
        user_id,
        "✅ *Спасибо!* Ваши данные переданы нашему специалисту.\n"
        "Ожидайте звонка или сообщения в ближайшее время.",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True)
    )
    
    user_data.pop(user_id, None)

# --- ЗАПУСК БОТА ---
if __name__ == '__main__':
    print("🚀 Бот запущен и работает через Long Polling...")
    bot.infinity_polling()
