import mysql.connector
from mysql.connector import errorcode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
import datetime

# Підключення до БД MySQL
try:
    cnx = mysql.connector.connect(
        host='localhost',
        user='root',
        password='...',
        database='bot',
        auth_plugin='mysql_native_password')
    cursor = cnx.cursor()
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Неправильне ім'я користувача або пароль")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("База даних не існує")
    else:
        print("Помилка підключення до БД MySQL:", err)
    exit()


def validate_date(date_str):
    try:
        datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validate_time(time_str):
    try:
        datetime.datetime.strptime(time_str, '%H:%M')
        return True
    except ValueError:
        return False


# Функція додавання розкладу
def add_schedule(update, context):
    user_id = update.message.from_user.id
    context.user_data['user_id'] = user_id

    # Створюємо клавіатуру з кнопками "Продовжити" та "Скасування"
    reply_keyboard = [['Продовжити', 'Скасування']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

    update.message.reply_text("Ви хочете створити новий розклад?", reply_markup=markup)

    return 'add_confirm_creation'


def add_confirm_creation(update, context):
    user_choice = update.message.text.lower()

    if user_choice == 'продовжити':
        update.message.reply_text("Введіть назву розкладу:", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop('keyboard', None)  # Видаляємо клавіатуру з контексту
        return 'title'
    elif user_choice == 'скасування':
        update.message.reply_text("Дія скасована. Ви повернулися в головне меню.")
        context.user_data.pop('keyboard', None)  # Видаляємо клавіатуру з контексту
        reply_keyboard = [['Додати розклад', 'Видалити розклад'], ['Відредагувати розклад', 'Переглянути розклад']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update.message.reply_text("Ось доступні команди:", reply_markup=markup)
        return 'select_option'
    else:
        update.message.reply_text("Не впізнано вибір користувача.")
        return 'add_confirm_creation'


def get_title(update, context):
    title = update.message.text.strip()
    context.user_data['title'] = title

    update.message.reply_text("Введіть дату розкладу (у форматі РРРР-ММ-ДД):")
    return 'date'


def get_date(update, context):
    date = update.message.text.strip()

    if not validate_date(date):
        update.message.reply_text("Неправильний формат дати. Введіть дату в форматі "
                                  "РРРР-ММ-ДД (наприклад, 2023-05-30).")
        return 'date'

    context.user_data['date'] = date

    update.message.reply_text("Введіть час розкладу (у форматі ЧЧ:ММ):")
    return 'time'


def get_time(update, context):
    time = update.message.text.strip()

    if not validate_time(time):
        update.message.reply_text("Неправильней формат часу. Введіть час в форматі ЧЧ:ММ (наприклад, 09:30).")
        return 'time'

    context.user_data['time'] = time

    update.message.reply_text("Введіть опис розкладу:")
    return 'description'


def get_description(update, context):
    description = update.message.text.strip()
    context.user_data['description'] = description

    # Запис розкладу в БД
    try:
        add_schedule_query = "INSERT INTO schedules (user_id, title, date, time, description) " \
                             "VALUES (%s, %s, %s, %s, %s)"
        schedule_data = (context.user_data['user_id'], context.user_data['title'], context.user_data['date'],
                         context.user_data['time'], context.user_data['description'])
        cursor.execute(add_schedule_query, schedule_data)
        cnx.commit()
        update.message.reply_text("Розклад успішно додано!", reply_markup=ReplyKeyboardRemove())
    except mysql.connector.Error as err:
        update.message.reply_text("Помилка при додаванні розкладу до БД:", err)

    # Повернення до вибору опцій
    reply_keyboard = [['Додати розклад', 'Видалити розклад'], ['Відредагувати розклад', 'Переглянути розклад']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text("Ось доступні команди:", reply_markup=markup)
    return 'select_option'


# Функція для редагування розкладу
def edit_schedule(update, context):
    user_id = update.message.from_user.id
    context.user_data['user_id'] = user_id

    # Перевірка наявності розкладу користувача в БД
    check_schedule_query = "SELECT * FROM schedules WHERE user_id = %s"
    check_schedule_data = (user_id,)
    cursor.execute(check_schedule_query, check_schedule_data)
    result = cursor.fetchall()

    if not result:
        update.message.reply_text("У вас немає жодного розкладу.")
        reply_keyboard = [['Додати розклад', 'Видалити розклад'], ['Відредагувати розклад', 'Переглянути розклад']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update.message.reply_text("Ось доступні команди:", reply_markup=markup)
        return 'select_option'

    # Створюємо клавіатуру з кнопками "Продовжити" та "Скасування"
    reply_keyboard = [['Продовжити', 'Скасування']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

    update.message.reply_text("Ви хочете відредагувати розклад?", reply_markup=markup)

    return 'edit_confirm_creation'


def edit_confirm_creation(update, context):
    user_choice = update.message.text.lower()

    if user_choice == 'продовжити':
        update.message.reply_text("Введіть назву розкладу, який потрібно відредагувати:",
                                  reply_markup=ReplyKeyboardRemove())
        context.user_data.pop('keyboard', None)  # Видаляємо клавіатуру з контексту
        return 'edit_title'
    elif user_choice == 'скасування':
        update.message.reply_text("Дія скасована. Ви повернулися в головне меню.")
        context.user_data.pop('keyboard', None)  # Видаляємо клавіатуру з контексту
        reply_keyboard = [['Додати розклад', 'Видалити розклад'], ['Відредагувати розклад', 'Переглянути розклад']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update.message.reply_text("Ось доступні команди:", reply_markup=markup)
        return 'select_option'
    else:
        update.message.reply_text("Не впізнано вибір користувача.")
        return 'edit_confirm_creation'


def get_edit_title(update, context):
    title = update.message.text.strip()
    context.user_data['title'] = title

    # Проверка наличия расписания пользователя в БД
    check_schedule_query = "SELECT COUNT(*) FROM schedules WHERE user_id = %s AND title = %s"
    check_schedule_data = (context.user_data['user_id'], context.user_data['title'])
    cursor.execute(check_schedule_query, check_schedule_data)
    result = cursor.fetchone()

    if result[0] == 0:
        update.message.reply_text("У вас немає розкладу з такою назвою. Будь ласка, введіть існуючу назву розкладу.")
        return 'edit_title'

    keyboard = [['Назва', 'Дата'], ['Час', 'Опис']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text("Що ви хочете редагувати у розкладі?", reply_markup=reply_markup)
    return 'edit_options'


def get_edit_options(update, context):
    options = update.message.text.strip()
    context.user_data['options'] = options

    update.message.reply_text("Введіть нове значення:")
    return 'new_value'


def get_new_value(update, context):
    new_value = update.message.text.strip()
    context.user_data['new_value'] = new_value

    if context.user_data['options'] == 'Час':
        if not validate_time(new_value):
            update.message.reply_text("Неправильний формат часу. Введіть час у форматі CH:MM (наприклад, 09:30).")
            return 'new_value'

    if context.user_data['options'] == 'Дата':
        if not validate_date(new_value):
            update.message.reply_text("Неправильний формат дати. Введіть дату у форматі "
                                      "РРРР-ММ-ДД (наприклад, 2023-05-30).")
            return 'new_value'

    # Редактирование расписания в БД
    try:
        if context.user_data['options'] == 'Назва':
            edit_schedule_query = "UPDATE schedules SET title = %s WHERE user_id = %s AND title = %s"
        elif context.user_data['options'] == 'Дата':
            edit_schedule_query = "UPDATE schedules SET date = %s WHERE user_id = %s AND title = %s"
        elif context.user_data['options'] == 'Час':
            edit_schedule_query = "UPDATE schedules SET time = %s WHERE user_id = %s AND title = %s"
        elif context.user_data['options'] == 'Опис':
            edit_schedule_query = "UPDATE schedules SET description = %s WHERE user_id = %s AND title = %s"
        else:
            update.message.reply_text("Виберіть один із варіантів: Назва, Дата, Час, Опис.",
                                      reply_markup=ReplyKeyboardRemove())
            return 'edit_options'

        edit_schedule_data = (context.user_data['new_value'], context.user_data['user_id'], context.user_data['title'])
        cursor.execute(edit_schedule_query, edit_schedule_data)
        cnx.commit()
        update.message.reply_text("Розклад успішно відредаговано!", reply_markup=ReplyKeyboardRemove())
    except mysql.connector.Error as err:
        update.message.reply_text("Помилка під час редагування розкладу у БД:", err)

    # Повернення до вибору опцій
    reply_keyboard = [['Додати розклад', 'Видалити розклад'], ['Відредагувати розклад', 'Переглянути розклад']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text("Ось доступні команди:", reply_markup=markup)
    return 'select_option'


# Функція видалення розкладу
def delete_schedule(update, context):
    user_id = update.message.from_user.id
    context.user_data['user_id'] = user_id

    # Перевірка наявності розкладу користувача в БД
    check_schedule_query = "SELECT * FROM schedules WHERE user_id = %s"
    check_schedule_data = (user_id,)
    cursor.execute(check_schedule_query, check_schedule_data)
    result = cursor.fetchall()

    if not result:
        update.message.reply_text("У вас немає жодного розкладу.")
        reply_keyboard = [['Додати розклад', 'Видалити розклад'], ['Відредагувати розклад', 'Переглянути розклад']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update.message.reply_text("Ось доступні команди:", reply_markup=markup)
        return 'select_option'

    # Створюємо клавіатуру з кнопками "Продовжити" та "Скасування"
    reply_keyboard = [['Продовжити', 'Скасування']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

    update.message.reply_text("Ви хочете видалити розклад?", reply_markup=markup)

    return 'delete_confirm_creation'


def delete_confirm_creation(update, context):
    user_choice = update.message.text.lower()

    if user_choice == 'продовжити':
        update.message.reply_text("Введіть назву розкладу, який потрібно видалити:",
                                  reply_markup=ReplyKeyboardRemove())
        context.user_data.pop('keyboard', None)  # Видаляємо клавіатуру з контексту
        return 'delete_title'
    elif user_choice == 'скасування':
        update.message.reply_text("Дія скасована. Ви повернулися в головне меню.")
        context.user_data.pop('keyboard', None)  # Видаляємо клавіатуру з контексту
        reply_keyboard = [['Додати розклад', 'Видалити розклад'], ['Відредагувати розклад', 'Переглянути розклад']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update.message.reply_text("Ось доступні команди:", reply_markup=markup)
        return 'select_option'
    else:
        update.message.reply_text("Не впізнано вибір користувача.")
        return 'delete_confirm_creation'


def get_delete_title(update, context):
    title = update.message.text.strip()
    context.user_data['title'] = title

    # Перевірка наявності розкладу користувача
    check_schedule_query = "SELECT * FROM schedules WHERE user_id = %s AND title = %s"
    check_schedule_data = (context.user_data['user_id'], context.user_data['title'])
    cursor.execute(check_schedule_query, check_schedule_data)
    result = cursor.fetchall()

    if not result:
        update.message.reply_text("Розклад з такою назвою не знайдено. Будь ласка, введіть існуючу назву розкладу.")
        return 'delete_title'

    # Удаление расписания из БД
    try:
        delete_schedule_query = "DELETE FROM schedules WHERE user_id = %s AND title = %s"
        delete_schedule_data = (context.user_data['user_id'], context.user_data['title'])
        cursor.execute(delete_schedule_query, delete_schedule_data)
        cnx.commit()
        update.message.reply_text("Розклад успішно видалено!")
    except mysql.connector.Error as err:
        update.message.reply_text(f"Помилка при видаленні розкладу з БД: {err}")

    # Повернення до вибору опцій
    reply_keyboard = [['Додати розклад', 'Видалити розклад'], ['Відредагувати розклад', 'Переглянути розклад']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text("Ось доступні команди:", reply_markup=markup)
    return 'select_option'


# Функция для просмотра расписания
def view_schedule(update, context):
    user_id = update.message.from_user.id
    context.user_data['user_id'] = user_id

    # Получение расписания пользователя из БД
    try:
        view_schedule_query = "SELECT * FROM schedules WHERE user_id = %s"
        view_schedule_data = (context.user_data['user_id'],)
        cursor.execute(view_schedule_query, view_schedule_data)
        result = cursor.fetchall()

        if len(result) == 0:
            update.message.reply_text("У вас немає розкладу.")
            # Повернення до вибору опцій
            reply_keyboard = [['Додати розклад', 'Видалити розклад'], ['Відредагувати розклад', 'Переглянути розклад']]
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            update.message.reply_text("Ось доступні команди:", reply_markup=markup)
            return 'select_option'
        else:
            schedule_text = "📅 Розклад: \n\n"
            schedule_text += "Назва \t\t Дата \t\t Час \t\t Опис\n"
            schedule_text += "-----------------------------------------\n"

            for schedule in result:
                hours = schedule[4].seconds // 3600
                minutes = (schedule[4].seconds % 3600) // 60
                schedule_time = f"{hours:02d}:{minutes:02d}"
                schedule_text += f"{schedule[2]} \t {schedule[3].strftime('%d.%m.%Y')} \t {schedule_time} \t {schedule[5]}\n"
            update.message.reply_text(schedule_text)
            # Повернення до вибору опцій
            reply_keyboard = [['Додати розклад', 'Видалити розклад'], ['Відредагувати розклад', 'Переглянути розклад']]
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            update.message.reply_text("Ось доступні команди:", reply_markup=markup)
            return 'select_option'

    except mysql.connector.Error as err:
        update.message.reply_text("Помилка при видаленні розкладу з БД:", err)
        # Повернення до вибору опцій
        reply_keyboard = [['Додати розклад', 'Видалити розклад'], ['Відредагувати розклад', 'Переглянути розклад']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update.message.reply_text("Ось доступні команди:", reply_markup=markup)
        return 'select_option'


# Обробник команд
def start(update, context):
    reply_keyboard = [['Додати розклад', 'Видалити розклад'], ['Відредагувати розклад', 'Переглянути розклад']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

    update.message.reply_text("Привіт! Я бот для управління розкладом Calendarium. Ось доступні команди:", reply_markup=markup)

    return 'select_option'


def select_option(update, context):
    option = update.message.text.strip().lower()

    if option == 'додати розклад':
        update.message.reply_text("Ви обрали опцію 'Додати розклад'.", reply_markup=ReplyKeyboardRemove())
        return add_schedule(update, context)

    elif option == 'видалити розклад':
        update.message.reply_text("Ви обрали опцію 'Видалити розклад'.", reply_markup=ReplyKeyboardRemove())
        return delete_schedule(update, context)

    elif option == 'відредагувати розклад':
        update.message.reply_text("Ви обрали опцію 'Відредагувати розклад'.", reply_markup=ReplyKeyboardRemove())
        return edit_schedule(update, context)

    elif option == 'переглянути розклад':
        update.message.reply_text("Ви обрали опцію 'Переглянути розклад'.", reply_markup=ReplyKeyboardRemove())
        return view_schedule(update, context)

    else:
        update.message.reply_text("Невірна опція. Будь ласка, оберіть опцію з клавіатури.",
                                  reply_markup=ReplyKeyboardRemove())
        update.message.reply_text("/start")

    return 'select_option'


# Инициализация бота и добавление обработчиков
updater = Updater('...', use_context=True)
dp = updater.dispatcher

# Создание conv_handler для команды /add
add_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('add', add_schedule)],
    states={
        'title': [MessageHandler(Filters.text, get_title)],
        'date': [MessageHandler(Filters.text, get_date)],
        'time': [MessageHandler(Filters.text, get_time)],
        'description': [MessageHandler(Filters.text, get_description)],
    },
    fallbacks=[],
)

# Добавление add_conv_handler в обработчики
dp.add_handler(add_conv_handler)


# Создание conv_handler для команды /edit
edit_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('edit', edit_schedule)],
    states={
        'edit_title': [MessageHandler(Filters.text, get_edit_title)],
        'edit_options': [MessageHandler(Filters.text, get_edit_options)],
        'new_value': [MessageHandler(Filters.text, get_new_value)],
    },
    fallbacks=[],
)

# Добавление edit_conv_handler в обработчики
dp.add_handler(edit_conv_handler)


# Создание conv_handler для команды /delete
delete_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('delete', delete_schedule)],
    states={
        'delete_title': [MessageHandler(Filters.text, get_delete_title)],
    },
    fallbacks=[],
)

# Добавление delete_conv_handler в обработчики
dp.add_handler(delete_conv_handler)


# Создание conv_handler для команды /view
view_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('view', view_schedule)],
    states={
        'select_option': [MessageHandler(Filters.text, view_schedule)],
    },
    fallbacks=[],
)


# Добавление обработчика команды /view
dp.add_handler(view_conv_handler)


# Создание conv_handler для команды /start
start_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        'select_option': [MessageHandler(Filters.text, select_option)],
        'delete_title': [MessageHandler(Filters.text, get_delete_title)],
        'edit_title': [MessageHandler(Filters.text, get_edit_title)],
        'edit_options': [MessageHandler(Filters.text, get_edit_options)],
        'new_value': [MessageHandler(Filters.text, get_new_value)],
        'add_confirm_creation': [MessageHandler(Filters.text, add_confirm_creation)],
        'edit_confirm_creation': [MessageHandler(Filters.text, edit_confirm_creation)],
        'delete_confirm_creation': [MessageHandler(Filters.text, delete_confirm_creation)],
        'title': [MessageHandler(Filters.text, get_title)],
        'date': [MessageHandler(Filters.text, get_date)],
        'time': [MessageHandler(Filters.text, get_time)],
        'description': [MessageHandler(Filters.text, get_description)],
    },
    fallbacks=[],
)

# Добавление start_conv_handler в обработчики
dp.add_handler(start_conv_handler)

# Запуск бота
updater.start_polling()
updater.idle()
