from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_consent_keyboard():
    """Клавиатура для согласия на обработку данных"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("✅ Даю согласие на обработку данных", callback_data="consent_agree"),
        InlineKeyboardButton("❌ Я не согласен", callback_data="consent_disagree")
    )
    return keyboard

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

def get_revoke_consent_keyboard():
    """Клавиатура для отзыва согласия"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Да, отозвать согласие", callback_data="revoke_confirm"),
        InlineKeyboardButton("❌ Нет, оставить", callback_data="revoke_cancel")
    )
    return keyboard
