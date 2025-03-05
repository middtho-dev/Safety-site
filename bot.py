import logging
import sqlite3
import os
import uuid
import tempfile

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    FSInputFile
)
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

# Папка для изображений
os.makedirs("data/image", exist_ok=True)

# Токен бота и ID администратора
BOT_TOKEN = '6602514727:AAF7d2iEQmH5YbynKSZH-lPA9-BDUNmjphY'
ADMIN_CHAT_ID = 382094545

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

def init_db():
    conn = sqlite3.connect('settings.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            phone TEXT
        )
    ''')
    conn.commit()
    conn.close()

def init_answers_db():
    conn = sqlite3.connect('answers.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            description TEXT,
            action TEXT,
            participant TEXT,
            area TEXT,
            category TEXT,
            state TEXT,
            shift TEXT,
            image TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def is_user_registered(user_id: int) -> bool:
    conn = sqlite3.connect('settings.db')
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    conn.close()
    return bool(result)

class CreatePost(StatesGroup):
    title = State()
    description = State()
    action = State()
    participant = State()
    area = State()
    category = State()
    sostoyanie = State()   # Выполнено/Не выполнено
    shift = State()
    image = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if not is_user_registered(user_id):
        contact_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(
            "Привет! 👋 Вы ещё не зарегистрированы. Пожалуйста, поделитесь вашим контактом для регистрации.",
            reply_markup=contact_keyboard
        )
    else:
        main_menu = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📝 Создать пост", callback_data="create_post")],
                [InlineKeyboardButton(text="📊 Выгрузка базы в XLSX", callback_data="export_db")]
            ]
        )
        await message.answer("Главное меню", reply_markup=main_menu)

@dp.message(F.contact)
async def contact_handler(message: types.Message):
    contact = message.contact
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name or ""
    username = message.from_user.username or ""
    phone = contact.phone_number

    conn = sqlite3.connect('settings.db')
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO users (user_id, first_name, last_name, username, phone) VALUES (?, ?, ?, ?, ?)",
        (user_id, first_name, last_name, username, phone)
    )
    conn.commit()
    conn.close()

    remove_keyboard = ReplyKeyboardRemove()
    await message.answer("Регистрация успешно пройдена! 🎉", reply_markup=remove_keyboard)
    main_menu = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Создать пост", callback_data="create_post")],
            [InlineKeyboardButton(text="📊 Выгрузка базы в XLSX", callback_data="export_db")]
        ]
    )
    await message.answer("Главное меню", reply_markup=main_menu)

@dp.message(Command("cancel"))
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        main_menu = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📝 Создать пост", callback_data="create_post")],
                [InlineKeyboardButton(text="📊 Выгрузка базы в XLSX", callback_data="export_db")]
            ]
        )
        await message.answer("Создание поста отменено. Возвращаем в Главное меню.", reply_markup=main_menu)
    else:
        await message.answer("Нет активного процесса создания поста.")

@dp.message(lambda message: message.text is not None and message.text.lower() == "отмена")
async def cancel_by_text(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        main_menu = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📝 Создать пост", callback_data="create_post")],
                [InlineKeyboardButton(text="📊 Выгрузка базы в XLSX", callback_data="export_db")]
            ]
        )
        await message.answer("Создание поста отменено. Возвращаем в Главное меню.", reply_markup=main_menu)

@dp.callback_query(lambda c: c.data == "create_post")
async def process_create_post(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CreatePost.title)
    await callback.message.answer("✏️ Введите заголовок:")

@dp.message(CreatePost.title)
async def process_title(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        return
    await state.update_data(title=message.text)
    await state.set_state(CreatePost.description)
    await message.answer("📝 Введите подробное описание проблемы или происшествия:")

@dp.message(CreatePost.description)
async def process_description(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        return
    await state.update_data(description=message.text)
    await state.set_state(CreatePost.action)
    await message.answer("✅ Введите действие для устранения:")

@dp.message(CreatePost.action)
async def process_action(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        return
    await state.update_data(action=message.text)
    await state.set_state(CreatePost.participant)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👷 Сотрудник", callback_data="participant:sotrudnik")],
            [InlineKeyboardButton(text="🏗 Подрядчик", callback_data="participant:podryadchik")],
            [InlineKeyboardButton(text="🚚 Водитель", callback_data="participant:voditel")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_post")]
        ]
    )
    await message.answer("👥 Выберите участника происшествия:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "cancel_post")
async def cancel_post_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    main_menu = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Создать пост", callback_data="create_post")],
            [InlineKeyboardButton(text="📊 Выгрузка базы в XLSX", callback_data="export_db")]
        ]
    )
    await callback.message.answer("Создание поста отменено. Возвращаем в Главное меню.", reply_markup=main_menu)
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("participant:"))
async def process_participant(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split(":", 1)[1]
    mapping = {"sotrudnik": "Сотрудник", "podryadchik": "Подрядчик", "voditel": "Водитель"}
    participant = mapping.get(data, data)
    await state.update_data(participant=participant)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await state.set_state(CreatePost.area)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Hot End", callback_data="area:hot_end")],
            [InlineKeyboardButton(text="❄️ Cold End", callback_data="area:cold_end")],
            [InlineKeyboardButton(text="🎨 Coater", callback_data="area:coater")],
            [InlineKeyboardButton(text="📦 Warehouse", callback_data="area:warehouse")],
            [InlineKeyboardButton(text="🔧 Maintenance", callback_data="area:maintenance")],
            [InlineKeyboardButton(text="🏢 Office", callback_data="area:office")],
            [InlineKeyboardButton(text="🌳 Территория", callback_data="area:territory")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_post")]
        ]
    )
    await callback.message.answer("📍 Выберите участок:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data and c.data.startswith("area:"))
async def process_area(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split(":", 1)[1]
    mapping = {"hot_end": "Hot End", "cold_end": "Cold End", "coater": "Coater", "warehouse": "Warehouse", "maintenance": "Maintenance", "office": "Office", "territory": "Территория"}
    area = mapping.get(data, data)
    await state.update_data(area=area)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await state.set_state(CreatePost.category)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌿 Экологический инцидент", callback_data="category:eco_incident")],
            [InlineKeyboardButton(text="⚠️ Несоответствие по экологии", callback_data="category:eco_noncompliance")],
            [InlineKeyboardButton(text="❌ Небезопасное действие", callback_data="category:unsafe_action")],
            [InlineKeyboardButton(text="⚡ Небезопасное условие", callback_data="category:unsafe_condition")],
            [InlineKeyboardButton(text="💥 Порча имущества", callback_data="category:property_damage")],
            [InlineKeyboardButton(text="🚑 Первая помощь", callback_data="category:first_aid")],
            [InlineKeyboardButton(text="🔧 HPE", callback_data="category:hpe")],
            [InlineKeyboardButton(text="📉 LTI", callback_data="category:lti")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_post")]
        ]
    )
    await callback.message.answer("🏷 Выберите категорию:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data and c.data.startswith("category:"))
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split(":", 1)[1]
    mapping = {"eco_incident": "Экологический инцидент", "eco_noncompliance": "Несоответствие по экологии", "unsafe_action": "Небезопасное действие", "unsafe_condition": "Небезопасное условие", "property_damage": "Порча имущества", "first_aid": "Первая помощь", "hpe": "HPE", "lti": "LTI"}
    category = mapping.get(data, data)
    await state.update_data(category=category)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await state.set_state(CreatePost.sostoyanie)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнено", callback_data="state:done")],
            [InlineKeyboardButton(text="❌ Не выполнено", callback_data="state:not_done")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_post")]
        ]
    )
    await callback.message.answer("🔄 Выберите состояние:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data and c.data.startswith("state:"))
async def process_state(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split(":", 1)[1]
    mapping = {"done": "Выполнено", "not_done": "Не выполнено"}
    sostoyanie = mapping.get(data, data)
    await state.update_data(sostoyanie=sostoyanie)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await state.set_state(CreatePost.shift)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='🅰️ Shift "A"', callback_data="shift:A")],
            [InlineKeyboardButton(text='🅱️ Shift "B"', callback_data="shift:B")],
            [InlineKeyboardButton(text='🇨 Shift "C"', callback_data="shift:C")],
            [InlineKeyboardButton(text='🇩 Shift "D"', callback_data="shift:D")],
            [InlineKeyboardButton(text='🌞 Shift "Day"', callback_data="shift:day")],
            [InlineKeyboardButton(text='🔧 Maintenance', callback_data="shift:maintenance")],
            [InlineKeyboardButton(text='🏢 Office', callback_data="shift:office")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_post")]
        ]
    )
    await callback.message.answer("⏰ Выберите смену:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data and c.data.startswith("shift:"))
async def process_shift(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split(":", 1)[1]
    mapping = {"A": 'Shift "A"', "B": 'Shift "B"', "C": 'Shift "C"', "D": 'Shift "D"', "day": 'Shift "Day"', "maintenance": "Maintenance", "office": "Office"}
    shift = mapping.get(data, data)
    await state.update_data(shift=shift)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await state.set_state(CreatePost.image)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_image")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_post")]
        ]
    )
    await callback.message.answer("📷 Прикрепите изображение или нажмите «Пропустить»:", reply_markup=keyboard)

@dp.message(CreatePost.image, F.photo)
async def process_image(message: types.Message, state: FSMContext):
    photo = message.photo[-1].file_id
    file = await bot.get_file(photo)
    file_bytes = await bot.download_file(file.file_path)
    filename = f"{uuid.uuid4()}.jpg"
    file_path = os.path.join("data", "image", filename)
    with open(file_path, "wb") as f:
        f.write(file_bytes.getvalue())
    await state.update_data(image=file_path)
    await finalize_post(message, state)

@dp.callback_query(lambda c: c.data == "skip_image")
async def skip_image(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(image=None)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await finalize_post(callback.message, state)

async def finalize_post(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    title = data.get("title")
    description = data.get("description")
    action = data.get("action")
    participant = data.get("participant")
    area = data.get("area")
    category = data.get("category")
    sostoyanie = data.get("sostoyanie")
    shift = data.get("shift")
    image = data.get("image")
    conn = sqlite3.connect('answers.db')
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO posts 
        (user_id, title, description, action, participant, area, category, state, shift, image) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, title, description, action, participant, area, category, sostoyanie, shift, image)
    )
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("Спасибо за ваш пост! 🙏")
    main_menu = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Создать пост", callback_data="create_post")],
            [InlineKeyboardButton(text="📊 Выгрузка базы в XLSX", callback_data="export_db")]
        ]
    )
    await message.answer("Главное меню", reply_markup=main_menu)

@dp.callback_query(lambda c: c.data == "export_db")
async def export_db(callback: types.CallbackQuery):
    await callback.answer()
    conn = sqlite3.connect('answers.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT id, user_id, title, description, action, participant, area, category, state, shift, image, timestamp 
        FROM posts
    """)
    rows = cur.fetchall()
    conn.close()
    wb = Workbook()
    ws = wb.active
    ws.title = "Posts"
    headers = ["ID", "User ID", "Title", "Description", "Action", "Participant", "Area", "Category", "State", "Shift", "Image", "Timestamp"]
    ws.append(headers)
    ws.column_dimensions["K"].width = 25
    current_row = 2
    for r in rows:
        post_id, user_id, title, description, action, participant, area, category, state_text, shift, image_path, timestamp = r
        ws.cell(row=current_row, column=1, value=post_id)
        ws.cell(row=current_row, column=2, value=user_id)
        ws.cell(row=current_row, column=3, value=title)
        ws.cell(row=current_row, column=4, value=description)
        ws.cell(row=current_row, column=5, value=action)
        ws.cell(row=current_row, column=6, value=participant)
        ws.cell(row=current_row, column=7, value=area)
        ws.cell(row=current_row, column=8, value=category)
        ws.cell(row=current_row, column=9, value=state_text)
        ws.cell(row=current_row, column=10, value=shift)
        ws.cell(row=current_row, column=12, value=timestamp)
        if image_path and os.path.exists(image_path):
            try:
                img = OpenpyxlImage(image_path)
                img.width = 150
                img.height = 150
                cell_location = f"K{current_row}"
                ws.cell(row=current_row, column=11, value="") 
                ws.row_dimensions[current_row].height = 110
                ws.add_image(img, cell_location)
            except Exception as e:
                ws.cell(row=current_row, column=11, value=image_path)
        else:
            ws.cell(row=current_row, column=11, value="")
        current_row += 1
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_xlsx:
        wb.save(tmp_xlsx.name)
        export_file_path = tmp_xlsx.name
    await bot.send_document(callback.message.chat.id, FSInputFile(export_file_path, filename="export.xlsx"))
    os.remove(export_file_path)
    main_menu = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Создать пост", callback_data="create_post")],
            [InlineKeyboardButton(text="📊 Выгрузка базы в XLSX", callback_data="export_db")]
        ]
    )
    await bot.send_message(callback.message.chat.id, "Главное меню", reply_markup=main_menu)

if __name__ == "__main__":
    init_db()
    init_answers_db()
    dp.run_polling(bot)
