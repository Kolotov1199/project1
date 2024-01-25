import base64
import math
import re
import traceback
import telegram
import asyncio
from telegram import Update, InlineKeyboardMarkup
from telegram import InlineKeyboardButton as IB
from telegram.constants import ParseMode
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import sqlite3

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.service_account import Credentials

# pip install python-telegram-bot


# =========================================================================================================================================
#                             БАЗА ДАННЫХ
# =========================================================================================================================================


подключение = sqlite3.connect("ANDREY_database.db")
cursor = подключение.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='пользователи'")
if not cursor.fetchone():
    cursor.execute('''
   CREATE TABLE IF NOT EXISTS пользователи (
                  id INTEGER PRIMARY KEY,
                  id_пользователя TEXT,
                  имя_пользователя TEXT,
                  статус_регистрации TEXT DEFAULT '0',
                  имя TEXT,
                  страна TEXT,
                  номер TEXT,
                  элпочта TEXT,

                  имя_заявка TEXT DEFAULT '0',
                  страна_заявка TEXT DEFAULT '0',
                  дата_рождения_заявка TEXT DEFAULT '0',
                  номер_заявка TEXT DEFAULT '0',
                  маил_заявка TEXT DEFAULT '0',
                  предыдущая_страна_заявка TEXT DEFAULT '0',

                  паспорт_заявка TEXT DEFAULT '0',
                  паспорт_на_русском_заявка TEXT DEFAULT '0',
                  фото_студент_заявка TEXT DEFAULT '0',
                  виза_заявка TEXT DEFAULT '0',
                  выписка_заявка TEXT DEFAULT '0'
                  )
   ''')
    print("✅ Добавлена таблица пользователи✅")

cursor.execute('''
   CREATE TABLE IF NOT EXISTS настройки (
               имя_группы_анкет TEXT DEFAULT 'не задано',
               id_группы_анкет TEXT DEFAULT 'не задано')
''')

cursor.execute('''
   CREATE TABLE IF NOT EXISTS вопрос_ответ (
               id INTEGER PRIMARY KEY,
               вопрос TEXT,
               ответ TEXT)
''')

cursor.execute("SELECT * FROM настройки")
результат = cursor.fetchone()
if результат == None:
    cursor.execute("INSERT INTO настройки DEFAULT VALUES")
    print("✅ Значение настроек задано на 'не задано'✅")

cursor.execute("SELECT * FROM вопрос_ответ")
if cursor.fetchone() == None:
    cursor.execute("INSERT INTO вопрос_ответ (вопрос, ответ) VALUES (?, ?)", ("пустой вопрос", "пустой ответ"))
    print("✅ Добавлена заглушка вопрос-ответ✅")

cursor.execute("SELECT id_группы_анкет FROM настройки")
полученные_настройки = cursor.fetchone()

подключение.commit()
подключение.close()

# =========================================================================================================================================
#                             ЗАГРУЗКА ДАННЫХ ИЗ НАСТРОЕК
# =========================================================================================================================================

id_рабочих_групп = []
for элемент in полученные_настройки:
    if элемент != "не задано":
        id_рабочих_групп.append(int(элемент))
    else:
        id_рабочих_групп.append(int(-1002055180978))

id_группы_анкет_база = id_рабочих_групп[0]

id_анкетной_группы = int(id_группы_анкет_база)

with open("Настройки.txt", "r") as настройки:
    строки = настройки.readlines()
    первая_строка = строки[0].strip("\n")
    Токен = первая_строка

# Тут должно быть имя пользователя админа, например kolotof
ссылка_на_админа = ""

путь_токена_googel_api = "resolute-might-412215-907775b32497.json"
имя_гугл_таблицы = "Аккаунты"
имя_листа_регистрация = "Лист1"
имя_листа_заявки = "Лист2"

# =========================================================================================================================================
#                             КЛАВИАТУРЫ
# =========================================================================================================================================


КЛАВАИНЛАНАСТРОЙКИБОТА = InlineKeyboardMarkup([
    [IB("Настройка рабочих чатов \U00002699", callback_data='настройка_рабочих_групп')],
    [IB("Настройка FAQ \U0001F4AC", callback_data='настройка_faq')],
    [IB("Рассылка 💣", callback_data='рассылка_всем')],
    [IB("Закрыть ❌", callback_data='закрыть_настройки_бота')]
])

КЛАВАИНЛАНАСТРОЙКИБОТАРАБГРУППЫ = InlineKeyboardMarkup([
    [IB("Рабочий чат \U0001F4DD", callback_data='установить_группу_анкет')],
    [IB("⬅️ Назад", callback_data='назад_настройки_бота_группы')]
])

КЛАВАИНЛАНАСТРОЙКИБОТАFAQ = InlineKeyboardMarkup([
    [IB("⬅️Назад", callback_data='назад_настройки_бота_группы')]
])

КЛАВАИНЛАМЕНЮ = InlineKeyboardMarkup([
    [IB("FAQ", callback_data='faq')],
    [IB("Send a request", callback_data='заявка')],
    [IB("Help", callback_data='тех_поддержка')],
    [IB("Contact the Administrator", url=f'https://t.me/{ссылка_на_админа}')]
    # [IB("Свзяться с Администратором", url=f'tg://user?id={446246013}')]
])

КЛАВАИНЛАНАСТРОЙКИБОТАРАССЫЛКАОТПРАВИТЬ = InlineKeyboardMarkup([
    [IB("ОТПРАВИТЬ ⤴️", callback_data='отправить_рассылку')]
])

КЛАВАИНЛАFAQАДМИН = InlineKeyboardMarkup([
    [IB("Изменить ✏️", callback_data='изменить_faq')],
    [IB("Удалить ❌", callback_data='удалить_faq')],
    [IB("⬅️Назад", callback_data='назад_faq')]
])

КЛАВАИНЛАFAQПОЛЬЗОВАТЕЛЬ = InlineKeyboardMarkup([
    [IB("⬅️Back", callback_data='назад_faq')]
])

КЛАВАИНЛАНАСТРОЙКИБОТАFAQСОХРАНИТЬВОПРОС = InlineKeyboardMarkup([
    [IB("СОХРАНИТЬ ✅", callback_data='сохранить_вопрос')]
])

КЛАВАИНЛАНАСТРОЙКИБОТАFAQСОХРАНИТЬОТВЕТ = InlineKeyboardMarkup([
    [IB("СОХРАНИТЬ ✅", callback_data='сохранить_ответ')]
])

КЛАВАИНЛАНАСТРОЙКИБОТАFAQДОБАВИТЬВОПРОС = InlineKeyboardMarkup([
    [IB("СОХРАНИТЬ ✅", callback_data='сохранить_вопрос_добавление')]
])

КЛАВАИНЛАНАСТРОЙКИБОТАFAQДОБАВИТЬОТВЕТ = InlineKeyboardMarkup([
    [IB("СОХРАНИТЬ ✅", callback_data='сохранить_ответ_добавление')]
])

КЛАВАИНЛАFAQОТМЕНА = InlineKeyboardMarkup([
    [IB("ОТМЕНА 🚫", callback_data='faq_отмена')]
])

КЛАВАИНЛАFAQДОБАВИТЬОТМЕНА = InlineKeyboardMarkup([
    [IB("ОТМЕНА 🚫", callback_data='faq_добавить_отмена')]
])

КЛАВАИНЛАПОМОЩЬОТПРАВИТЬ = InlineKeyboardMarkup([
    [IB("SEND⤴️", callback_data='помощь_отправить')]
])

# ОБНОВИЛ
КЛАВАИНЛАПЕРВОЕПОДТВЕРЖДЕНИЕРЕГИСТРАЦИИ = InlineKeyboardMarkup([
    [IB("Agree", callback_data='подтвердить_намерение_регистрации')]
])

КЛАВАИНЛАПОДТВЕРДИТЬЗАЯВКУ = InlineKeyboardMarkup([
    [IB("Подтвердить ✅", callback_data='подтвердить_заявку')],
    [IB("Отклонить ❌", callback_data='отклонить_заявку')]
])

КЛАВАИНЛАПОДТВЕРДИТЬЗАЯВКУОТМЕНАОТВЕТПРИЧИНА = InlineKeyboardMarkup([
    [IB("Отправить ответ ✅", callback_data='ответ_причина_отмена_заявка')]
])


# ОБНОВИЛ


# =========================================================================================================================================
#                             ОБРАБОТЧИКИ ИНЛАЙН СОБЫТИЙ
# =========================================================================================================================================


async def событие_инлайн(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global id_анкетной_группы

    инлайн_запрос = update.callback_query

    if инлайн_запрос.data == 'подтвердить_намерение_регистрации':
        asyncio.create_task(событие_юнити(update, context))

    if инлайн_запрос.data == 'тех_поддержка':
        asyncio.create_task(событие_техподдержка(update, context))

    if инлайн_запрос.data == 'помощь_отправить':
        if "обращение_в_техподдержку" in context.user_data and context.user_data["обращение_в_техподдержку"] == 1:
            context.user_data["обращение_в_техподдержку"] = 0
            # await context.bot.edit_message_reply_markup(update.effective_chat.id, инлайн_запрос.message.id, reply_markup=None)

            id_пользователя = инлайн_запрос.from_user.id
            подключение = sqlite3.connect("ANDREY_database.db")
            cursor = подключение.cursor()
            cursor.execute("SELECT имя FROM пользователи WHERE id_пользователя = ?", (id_пользователя,))
            имя = cursor.fetchall()[0][0]
            подключение.close()

            await context.bot.send_message(id_анкетной_группы, f"Вопрос от {имя}:")
            await context.bot.forward_message(id_анкетной_группы, update.effective_chat.id,
                                              инлайн_запрос.message.id - 1)
            await context.bot.delete_message(update.effective_chat.id, инлайн_запрос.message.id)
            await context.bot.answer_callback_query(инлайн_запрос.id, "✅ Ваш вопрос успешно отправлен ✅")
            asyncio.create_task(событие_меню(update, context, update.callback_query.from_user.language_code))

        elif "обращение_в_техподдержку" not in context.user_data:
            # await context.bot.edit_message_reply_markup(update.effective_chat.id, инлайн_запрос.message.id, reply_markup=None)
            await context.bot.delete_message(update.effective_chat.id, инлайн_запрос.message.id)
            await context.bot.answer_callback_query(инлайн_запрос.id,
                                                    "⚠️ Контекст был неожиданно сброшен, пожалуйста, отправьте вопрос заново через меню.",
                                                    True)
            asyncio.create_task(событие_меню(update, context, update.callback_query.from_user.language_code))

        elif "обращение_в_техподдержку" in context.user_data and context.user_data["обращение_в_техподдержку"] == 0:
            # await context.bot.edit_message_reply_markup(update.effective_chat.id, инлайн_запрос.message.id, reply_markup=None)
            await context.bot.delete_message(update.effective_chat.id, инлайн_запрос.message.id)
            await context.bot.answer_callback_query(инлайн_запрос.id,
                                                    "⚠️ Кнопка не активна, пожалуйста, отправьте вопрос заново через меню.",
                                                    True)
            asyncio.create_task(событие_меню(update, context, update.callback_query.from_user.language_code))

    if инлайн_запрос.data == 'рассылка_всем':
        await context.bot.edit_message_text("🚨 Режим рассылки 🚨", update.effective_chat.id, инлайн_запрос.message.id,
                                            reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТАFAQ)
        await context.bot.answer_callback_query(инлайн_запрос.id,
                                                "🚨 Запущен режим рассылки 🚨\n\nОтправь текст рассылки ниже и подтверди рассылку.",
                                                show_alert=True)
        context.user_data["режим_рассылки"] = 1

    if инлайн_запрос.data == 'отправить_рассылку':
        if "режим_рассылки" in context.user_data and context.user_data["режим_рассылки"] == 1:

            try:
                await context.bot.edit_message_reply_markup(update.effective_chat.id, инлайн_запрос.message.message_id,
                                                            reply_markup=None)

                подключение = sqlite3.connect("ANDREY_database.db")
                cursor = подключение.cursor()
                cursor.execute("SELECT id_пользователя FROM пользователи")
                id_пользователей = cursor.fetchall()
                подключение.close()

                for id_пользователя in id_пользователей:
                    await context.bot.copy_message(id_пользователя[0], update.effective_chat.id,
                                                   инлайн_запрос.message.id, reply_markup=None)
                    print(f"✅ Успешно заспамлен рекрут: {id_пользователя[0]}")
                    await asyncio.sleep(0.1)

                await context.bot.answer_callback_query(инлайн_запрос.id, "✅ Рассылка успешно отправлена ✅")
                context.user_data["режим_рассылки"] = 0
            except Exception as e:
                строка_ошибки = traceback.print_exc(limit=1)
                код_ошибки = f"Код ошибки: {type(e).__name__}"
                содержание_ошибки = f"\nСодержание: {str(e)}"
                await context.bot.answer_callback_query(инлайн_запрос.id,
                                                        строка_ошибки + код_ошибки + содержание_ошибки, True)

        else:
            await context.bot.answer_callback_query(инлайн_запрос.id,
                                                    "⚠️ Не запущена рассылка ⚠️\n\nНеобходимо запустить решим рассылки в панели инструментов.",
                                                    show_alert=True)
            await context.bot.edit_message_reply_markup(update.effective_chat.id, инлайн_запрос.message.message_id,
                                                        reply_markup=None)

    # СТРАНИЦЫ FAQ
    if инлайн_запрос.data == 'настройка_faq' or инлайн_запрос.data == 'faq':
        context.chat_data["изменение_faq"] = 0
        context.chat_data["добавление_faq"] = 0
        await загрузка_списка_вопросов()
        global номер_страницы
        номер_страницы = context.chat_data["номер_страницы"] = 0

        # Первая страница
        if len(список_страниц) > 1:
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            # СОЗДАНИЕ УНИВЕРСАЛЬНОЙ КЛАВЫ ПЕРВАЯ СТРАНИЦА
            текст_страницы = список_страниц[номер_страницы][1].splitlines()
            клавиатура = []
            клавиатура.clear()
            if инлайн_запрос.message.chat.id == id_анкетной_группы:
                клавиатура = [[], [], [], [IB("⬅️", callback_data='назад_админ_панель_2стрзаписи'),
                                           IB("➡️", callback_data='далее_ученики')],
                              [IB("Добавить ➕", callback_data='добавить_faq')]]
            else:
                клавиатура = [[], [], [], [IB("⬅️", callback_data='назад_админ_панель_2стрзаписи'),
                                           IB("➡️", callback_data='далее_ученики')]]
            for i, строка in enumerate(текст_страницы):
                # Получаем номер вопроса и добавляем его в список номеров вопросов страницы
                номер_вопроса = строка[1:строка.index(']')]
                значение_вопроса = номер_вопроса + "!!"
                кнопка = IB(text=номер_вопроса, callback_data=значение_вопроса)
                if -1 < i < 3:
                    клавиатура[0].append(кнопка)
                elif 2 < i < 6:
                    клавиатура[1].append(кнопка)
                elif 5 < i < 10:
                    клавиатура[2].append(кнопка)
            КЛАВАИНЛААДМИНПАНЕЛЬУЧЕНИКИОБРАТНО = InlineKeyboardMarkup(клавиатура)
            # //////////////////////////////////////////////////////////////////////////////////
            клавиатура = КЛАВАИНЛААДМИНПАНЕЛЬУЧЕНИКИОБРАТНО
        # Единственная страница
        elif len(список_страниц) == 1:
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            # СОЗДАНИЕ УНИВЕРСАЛЬНОЙ КЛАВЫ ПЕРВАЯ СТРАНИЦА
            текст_страницы = список_страниц[номер_страницы][1].splitlines()
            клавиатура = []
            клавиатура.clear()
            if инлайн_запрос.message.chat.id == id_анкетной_группы:
                клавиатура = [[], [], [], [IB("⬅️", callback_data='назад_админ_панель_2стрзаписи')],
                              [IB("Добавить ➕", callback_data='добавить_faq')]]
            else:
                клавиатура = [[], [], [], [IB("⬅️", callback_data='назад_админ_панель_2стрзаписи')]]
            for i, строка in enumerate(текст_страницы):
                # Получаем номер вопроса и добавляем его в список номеров вопросов страницы
                номер_вопроса = строка[1:строка.index(']')]
                значение_вопроса = номер_вопроса + "!!"
                кнопка = IB(text=номер_вопроса, callback_data=значение_вопроса)
                if -1 < i < 3:
                    клавиатура[0].append(кнопка)
                elif 2 < i < 6:
                    клавиатура[1].append(кнопка)
                elif 5 < i < 10:
                    клавиатура[2].append(кнопка)
            КЛАВАИНЛААДМИНПАНЕЛЬУЧЕНИКИНАЗАДЗАПИСИ = InlineKeyboardMarkup(клавиатура)
            # //////////////////////////////////////////////////////////////////////////////////
            клавиатура = КЛАВАИНЛААДМИНПАНЕЛЬУЧЕНИКИНАЗАДЗАПИСИ

        await context.bot.edit_message_text("Список FAQ\n\n" + список_страниц[номер_страницы][
            1] + f"\n\nСтраница: {номер_страницы + 1} из {количество_страниц}", update.effective_chat.id,
                                            инлайн_запрос.message.message_id, reply_markup=клавиатура)

    if инлайн_запрос.data == 'далее_ученики':
        if "номер_страницы" not in context.chat_data:
            номер_страницы = context.chat_data["номер_страницы"] = 0
            if инлайн_запрос.message.chat.id == id_анкетной_группы:
                await context.bot.edit_message_text("Что я должен сделать?", update.effective_chat.id,
                                                    инлайн_запрос.message.message_id,
                                                    reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТА)
            else:
                await context.bot.edit_message_text("Меню", update.effective_chat.id, инлайн_запрос.message.message_id,
                                                    reply_markup=КЛАВАИНЛАМЕНЮ)
            return
        else:
            номер_страницы += 1
        # Если страница промежуточная
        if 0 < номер_страницы < количество_страниц - 1:
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            # СОЗДАНИЕ УНИВЕРСАЛЬНОЙ КЛАВЫ ПРОМЕЖУТОЧНАЯ СТРАНИЦА
            текст_страницы = список_страниц[номер_страницы][1].splitlines()
            клавиатура = []
            клавиатура.clear()
            if инлайн_запрос.message.chat.id == id_анкетной_группы:
                клавиатура = [[], [], [],
                              [IB("⬅️", callback_data='назад_ученики'), IB("➡️", callback_data='далее_ученики')],
                              [IB("Добавить ➕", callback_data='добавить_faq')]]
            else:
                клавиатура = [[], [], [],
                              [IB("⬅️", callback_data='назад_ученики'), IB("➡️", callback_data='далее_ученики')]]
            for i, строка in enumerate(текст_страницы):
                # Получаем номер вопроса и добавляем его в список номеров вопросов страницы
                номер_вопроса = строка[1:строка.index(']')]
                значение_вопроса = номер_вопроса + "!!"
                кнопка = IB(text=номер_вопроса, callback_data=значение_вопроса)
                if -1 < i < 3:
                    клавиатура[0].append(кнопка)
                elif 2 < i < 6:
                    клавиатура[1].append(кнопка)
                elif 5 < i < 10:
                    клавиатура[2].append(кнопка)
            КЛАВАИНЛААДМИНПАНЕЛЬУЧЕНИКИТУДАСЮДА = InlineKeyboardMarkup(клавиатура)
            # //////////////////////////////////////////////////////////////////////////////////
            клавиатура = КЛАВАИНЛААДМИНПАНЕЛЬУЧЕНИКИТУДАСЮДА
        # Если страница последняя
        elif номер_страницы == количество_страниц - 1:
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            # СОЗДАНИЕ УНИВЕРСАЛЬНОЙ КЛАВЫ ПРОМЕЖУТОЧНАЯ СТРАНИЦА
            текст_страницы = список_страниц[номер_страницы][1].splitlines()
            клавиатура = []
            клавиатура.clear()
            if инлайн_запрос.message.chat.id == id_анкетной_группы:
                клавиатура = [[], [], [], [IB("⬅️", callback_data='назад_ученики')],
                              [IB("Добавить ➕", callback_data='добавить_faq')]]
            else:
                клавиатура = [[], [], [], [IB("⬅️", callback_data='назад_ученики')]]
            for i, строка in enumerate(текст_страницы):
                # Получаем номер вопроса и добавляем его в список номеров вопросов страницы
                номер_вопроса = строка[1:строка.index(']')]
                значение_вопроса = номер_вопроса + "!!"
                кнопка = IB(text=номер_вопроса, callback_data=значение_вопроса)
                if -1 < i < 3:
                    клавиатура[0].append(кнопка)
                elif 2 < i < 6:
                    клавиатура[1].append(кнопка)
                elif 5 < i < 10:
                    клавиатура[2].append(кнопка)
            КЛАВАИНЛААДМИНПАНЕЛЬУЧЕНИКИНАЗАД = InlineKeyboardMarkup(клавиатура)
            # //////////////////////////////////////////////////////////////////////////////////
            клавиатура = КЛАВАИНЛААДМИНПАНЕЛЬУЧЕНИКИНАЗАД
        await context.bot.edit_message_text("Список FAQ\n\n" + список_страниц[номер_страницы][
            1] + f"\n\nСтраница: {номер_страницы + 1} из {количество_страниц}", update.effective_chat.id,
                                            инлайн_запрос.message.message_id, reply_markup=клавиатура)

    if инлайн_запрос.data == 'назад_ученики':
        # Условие после перезхапуска бота
        if "номер_страницы" not in context.chat_data:
            номер_страницы = context.chat_data["номер_страницы"] = 0
            if инлайн_запрос.message.chat.id == id_анкетной_группы:
                await context.bot.edit_message_text("Что я должен сделать?", update.effective_chat.id,
                                                    инлайн_запрос.message.message_id,
                                                    reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТА)
            else:
                await context.bot.edit_message_text("Меню", update.effective_chat.id, инлайн_запрос.message.message_id,
                                                    reply_markup=КЛАВАИНЛАМЕНЮ)
            return
        else:
            номер_страницы -= 1
        # Если первая страница
        if номер_страницы == 0:
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            # СОЗДАНИЕ УНИВЕРСАЛЬНОЙ КЛАВЫ ПЕРВАЯ СТРАНИЦА
            текст_страницы = список_страниц[номер_страницы][1].splitlines()
            клавиатура = []
            клавиатура.clear()
            if инлайн_запрос.message.chat.id == id_анкетной_группы:
                клавиатура = [[], [], [], [IB("⬅️", callback_data='назад_админ_панель_2стрзаписи'),
                                           IB("➡️", callback_data='далее_ученики')],
                              [IB("Добавить ➕", callback_data='добавить_faq')]]
            else:
                клавиатура = [[], [], [], [IB("⬅️", callback_data='назад_админ_панель_2стрзаписи'),
                                           IB("➡️", callback_data='далее_ученики')]]
            for i, строка in enumerate(текст_страницы):
                # Получаем номер вопроса и добавляем его в список номеров вопросов страницы
                номер_вопроса = строка[1:строка.index(']')]
                значение_вопроса = номер_вопроса + "!!"
                кнопка = IB(text=номер_вопроса, callback_data=значение_вопроса)
                if -1 < i < 3:
                    клавиатура[0].append(кнопка)
                elif 2 < i < 6:
                    клавиатура[1].append(кнопка)
                elif 5 < i < 10:
                    клавиатура[2].append(кнопка)
            КЛАВАИНЛААДМИНПАНЕЛЬУЧЕНИКИОБРАТНО = InlineKeyboardMarkup(клавиатура)
            # //////////////////////////////////////////////////////////////////////////////////
            клавиатура = КЛАВАИНЛААДМИНПАНЕЛЬУЧЕНИКИОБРАТНО
        # Если промежуточная
        elif 0 < номер_страницы < количество_страниц - 1:
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            # СОЗДАНИЕ УНИВЕРСАЛЬНОЙ КЛАВЫ ПРОМЕЖУТОЧНАЯ СТРАНИЦА
            текст_страницы = список_страниц[номер_страницы][1].splitlines()
            клавиатура = []
            клавиатура.clear()
            if инлайн_запрос.message.chat.id == id_анкетной_группы:
                клавиатура = [[], [], [],
                              [IB("⬅️ Назад", callback_data='назад_ученики'), IB("➡️", callback_data='далее_ученики')],
                              [IB("Добавить ➕", callback_data='добавить_faq')]]
            else:
                клавиатура = [[], [], [],
                              [IB("⬅️ Назад", callback_data='назад_ученики'), IB("➡️", callback_data='далее_ученики')]]
            for i, строка in enumerate(текст_страницы):
                # Получаем номер вопроса и добавляем его в список номеров вопросов страницы
                номер_вопроса = строка[1:строка.index(']')]
                значение_вопроса = номер_вопроса + "!!"
                кнопка = IB(text=номер_вопроса, callback_data=значение_вопроса)
                if -1 < i < 3:
                    клавиатура[0].append(кнопка)
                elif 2 < i < 6:
                    клавиатура[1].append(кнопка)
                elif 5 < i < 10:
                    клавиатура[2].append(кнопка)
            КЛАВАИНЛААДМИНПАНЕЛЬУЧЕНИКИТУДАСЮДА = InlineKeyboardMarkup(клавиатура)
            # //////////////////////////////////////////////////////////////////////////////////
            клавиатура = КЛАВАИНЛААДМИНПАНЕЛЬУЧЕНИКИТУДАСЮДА
        elif номер_страницы == количество_страниц - 1:
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            # СОЗДАНИЕ УНИВЕРСАЛЬНОЙ КЛАВЫ ПОСЛЕДНЯЯ СТРАНИЦА
            текст_страницы = список_страниц[номер_страницы][1].splitlines()
            клавиатура = []
            клавиатура.clear()
            if инлайн_запрос.message.chat.id == id_анкетной_группы:
                клавиатура = [[], [], [], [IB("⬅️", callback_data='назад_ученики')],
                              [IB("Добавить ➕", callback_data='добавить_faq')]]
            else:
                клавиатура = [[], [], [], [IB("⬅️", callback_data='назад_ученики')]]
            for i, строка in enumerate(текст_страницы):
                # Получаем номер вопроса и добавляем его в список номеров вопросов страницы
                номер_вопроса = строка[1:строка.index(']')]
                значение_вопроса = номер_вопроса + "!!"
                кнопка = IB(text=номер_вопроса, callback_data=значение_вопроса)
                if -1 < i < 3:
                    клавиатура[0].append(кнопка)
                elif 2 < i < 6:
                    клавиатура[1].append(кнопка)
                elif 5 < i < 10:
                    клавиатура[2].append(кнопка)
            КЛАВАИНЛААДМИНПАНЕЛЬУЧЕНИКИНАЗАД = InlineKeyboardMarkup(клавиатура)
            # //////////////////////////////////////////////////////////////////////////////////
            клавиатура = КЛАВАИНЛААДМИНПАНЕЛЬУЧЕНИКИНАЗАД
        await context.bot.edit_message_text("Список FAQ\n\n" + список_страниц[номер_страницы][
            1] + f"\n\nСтраница: {номер_страницы + 1} из {количество_страниц}", update.effective_chat.id,
                                            инлайн_запрос.message.message_id, reply_markup=клавиатура)
    # Реакция на номера вопросов в группе
    if "!!" in инлайн_запрос.data and инлайн_запрос.message.chat.id == id_анкетной_группы:
        if "номер_страницы" not in context.chat_data:
            номер_страницы = context.chat_data["номер_страницы"] = 0
            await context.bot.edit_message_text("Что я должен сделать?", update.effective_chat.id,
                                                инлайн_запрос.message.message_id, reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТА)
            return

        await asyncio.sleep(1)
        context.user_data["id_страницы"] = инлайн_запрос.message.message_id
        номер_вопроса_в_базе_данных = int(инлайн_запрос.data.replace('!!', ''))
        context.user_data["номер_вопроса_в_базе_данных"] = номер_вопроса_в_базе_данных
        текст_страницы2 = список_страниц[номер_страницы][1].split('\n')
        название_вопроса = None
        for вопрос in текст_страницы2:
            if f"[{номер_вопроса_в_базе_данных}]" in вопрос:
                название_вопроса = вопрос

        подключение = sqlite3.connect("ANDREY_database.db")
        cursor = подключение.cursor()
        # cursor.execute("SELECT ответ FROM вопрос_ответ WHERE id = ?", (номер_вопроса_в_базе_данных,))
        cursor.execute("SELECT ответ FROM вопрос_ответ ORDER BY ROWID LIMIT 1 OFFSET ?",
                       (номер_вопроса_в_базе_данных - 1,))
        ответ = cursor.fetchone()[0]
        подключение.close()

        # await context.bot.edit_message_text(название_вопроса + "\n\nОтвет: " + ответ, update.effective_chat.id, инлайн_запрос.message.id, reply_markup=КЛАВАИНЛАFAQАДМИН)
        await context.bot.send_message(update.effective_chat.id, название_вопроса + "\n\nОтвет: " + ответ,
                                       reply_markup=КЛАВАИНЛАFAQАДМИН)
    # Реакция на номера вопросов вне группы
    if "!!" in инлайн_запрос.data and инлайн_запрос.message.chat.id != id_анкетной_группы:
        if "номер_страницы" not in context.chat_data:
            номер_страницы = context.chat_data["номер_страницы"] = 0
            await context.bot.edit_message_text("Меню", update.effective_chat.id, инлайн_запрос.message.message_id,
                                                reply_markup=КЛАВАИНЛАМЕНЮ)
            return

        await asyncio.sleep(1)
        номер_вопроса_в_базе_данных = int(инлайн_запрос.data.replace('!!', ''))
        текст_страницы2 = список_страниц[номер_страницы][1].split('\n')
        название_вопроса = None
        for вопрос in текст_страницы2:
            if f"[{номер_вопроса_в_базе_данных}]" in вопрос:
                название_вопроса = вопрос

        подключение = sqlite3.connect("ANDREY_database.db")
        cursor = подключение.cursor()
        cursor.execute("SELECT ответ FROM вопрос_ответ ORDER BY ROWID LIMIT 1 OFFSET ?",
                       (номер_вопроса_в_базе_данных - 1,))
        ответ = cursor.fetchone()[0]
        подключение.close()

        # await context.bot.edit_message_text(название_вопроса + "\n\nОтвет: " + ответ, update.effective_chat.id, инлайн_запрос.message.id, reply_markup=КЛАВАИНЛАFAQПОЛЬЗОВАТЕЛЬ)
        await context.bot.send_message(update.effective_chat.id, название_вопроса + "\n\nОтвет: " + ответ,
                                       reply_markup=КЛАВАИНЛАFAQПОЛЬЗОВАТЕЛЬ)

    if инлайн_запрос.data == 'назад_faq':
        await context.bot.delete_message(update.effective_chat.id, инлайн_запрос.message.message_id)

    if инлайн_запрос.data == 'изменить_faq':
        if "изменение_faq" not in context.chat_data:
            await context.bot.edit_message_text("Что я должен сделать?", update.effective_chat.id,
                                                инлайн_запрос.message.message_id, reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТА)
            return
        context.chat_data["изменение_faq"] = 1
        context.user_data["вопрос_ответ"] = []
        await context.bot.answer_callback_query(инлайн_запрос.id, "🚨 Запущен режим редактирования FAQ 🚨",
                                                show_alert=False)
        asyncio.create_task(событие_юнити(update, context))

    if инлайн_запрос.data == 'faq_отмена':
        context.chat_data["изменение_faq"] = 0
        context.chat_data["запись_вопроса"] = 0
        context.chat_data["запись_ответ"] = 0
        await context.bot.delete_message(update.effective_chat.id, инлайн_запрос.message.id)

    if инлайн_запрос.data == 'faq_добавить_отмена':
        context.user_data["добавление_faq"] = 0
        context.chat_data["запись_вопроса_добавление"] = 0
        context.chat_data["запись_ответ_добавление"] = 0
        await context.bot.delete_message(update.effective_chat.id, инлайн_запрос.message.id)

    if инлайн_запрос.data == 'сохранить_вопрос':
        await context.bot.edit_message_reply_markup(update.effective_chat.id, инлайн_запрос.message.id,
                                                    reply_markup=None)
        context.chat_data["запись_вопроса"] = 2
        context.user_data["вопрос_ответ"].append(инлайн_запрос.message.text)
        context.chat_data["запись_ответ"] = 1
        await context.bot.send_message(update.effective_chat.id,
                                       "Отлично! Вопрос сохранён. Теперь напиши ответ на него ниже⤵️")

    if инлайн_запрос.data == 'сохранить_ответ':
        await context.bot.edit_message_reply_markup(update.effective_chat.id, инлайн_запрос.message.id,
                                                    reply_markup=None)
        context.chat_data["запись_ответ"] = 2
        context.chat_data["изменение_faq"] = 2
        context.user_data["вопрос_ответ"].append(инлайн_запрос.message.text)
        вопрос_ответ = context.user_data["вопрос_ответ"]
        номер_вопроса_изменение = context.user_data["номер_вопроса_в_базе_данных"]

        # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        подключение = sqlite3.connect("ANDREY_database.db")
        cursor = подключение.cursor()
        # cursor.execute("UPDATE вопрос_ответ SET вопрос = ?, ответ = ? ORDER BY ROWID LIMIT 1 OFFSET ?", (вопрос_ответ[0], вопрос_ответ[1], номер_вопроса_изменение))
        cursor.execute(
            "UPDATE вопрос_ответ SET вопрос = ?, ответ = ? WHERE ROWID = (SELECT ROWID FROM вопрос_ответ ORDER BY ROWID LIMIT 1 OFFSET ?)",
            (вопрос_ответ[0], вопрос_ответ[1], номер_вопроса_изменение - 1))
        подключение.commit()
        подключение.close()
        # ////////////////////////////////////////////////

        context.user_data["номер_вопроса_в_базе_данных"] = -1
        await context.bot.send_message(update.effective_chat.id, "Связка вопрос-ответ успешно сохранены 🚀")
        await context.bot.send_message(update.effective_chat.id, "Какие будут указания?", disable_notification=True,
                                       reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТА)

    if инлайн_запрос.data == 'удалить_faq':
        номер_вопроса_изменение = context.user_data["номер_вопроса_в_базе_данных"]
        подключение = sqlite3.connect("ANDREY_database.db")
        cursor = подключение.cursor()
        cursor.execute(
            "DELETE FROM вопрос_ответ WHERE ROWID = (SELECT ROWID FROM вопрос_ответ ORDER BY ROWID LIMIT 1 OFFSET ?)",
            (номер_вопроса_изменение - 1,))
        подключение.commit()
        подключение.close()
        id_страницы = context.user_data["id_страницы"]
        await context.bot.edit_message_text("Что я должен сделать?", update.effective_chat.id, id_страницы,
                                            reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТА)
        await context.bot.delete_message(update.effective_chat.id, инлайн_запрос.message.id)
        context.user_data["id_страницы"] = -1

    if инлайн_запрос.data == 'добавить_faq':
        if "добавление_faq" not in context.chat_data:
            await context.bot.edit_message_text("Что я должен сделать?", update.effective_chat.id,
                                                инлайн_запрос.message.message_id, reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТА)
            return
        context.user_data["добавление_faq"] = 1
        context.user_data["вопрос_ответ_добавление"] = []
        await context.bot.answer_callback_query(инлайн_запрос.id, "🚨 Запущен режим добавления FAQ 🚨", show_alert=False)
        asyncio.create_task(событие_юнити(update, context))

    if инлайн_запрос.data == 'сохранить_вопрос_добавление':
        await context.bot.edit_message_reply_markup(update.effective_chat.id, инлайн_запрос.message.id,
                                                    reply_markup=None)
        context.user_data["запись_вопроса_добавление"] = 2
        context.user_data["вопрос_ответ_добавление"].append(инлайн_запрос.message.text)
        context.user_data["запись_ответ_добавление"] = 1
        await context.bot.send_message(update.effective_chat.id,
                                       "Отлично! Вопрос сохранён. Теперь напиши ответ на него ниже⤵️")

    if инлайн_запрос.data == 'сохранить_ответ_добавление':
        await context.bot.edit_message_reply_markup(update.effective_chat.id, инлайн_запрос.message.id,
                                                    reply_markup=None)
        context.user_data["запись_ответ_добавление"] = 2
        context.user_data["добавление_faq"] = 2
        context.user_data["вопрос_ответ_добавление"].append(инлайн_запрос.message.text)
        вопрос_ответ = context.user_data["вопрос_ответ_добавление"]

        # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        подключение = sqlite3.connect("ANDREY_database.db")
        cursor = подключение.cursor()
        cursor.execute("INSERT INTO вопрос_ответ (вопрос, ответ) VALUES (?, ?)", (вопрос_ответ[0], вопрос_ответ[1]))
        подключение.commit()
        подключение.close()
        # ////////////////////////////////////////////////

        await context.bot.send_message(update.effective_chat.id, "Связка вопрос-ответ успешно добавлены ✅")
        await context.bot.send_message(update.effective_chat.id, "Какие будут указания?", disable_notification=True,
                                       reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТА)
    # СТРАНИЦЫ FAQ

    if инлайн_запрос.data == 'назад_админ_панель_2стрзаписи':
        if инлайн_запрос.message.chat.id == id_анкетной_группы:
            await context.bot.edit_message_text("Что я должен сделать?", update.effective_chat.id,
                                                инлайн_запрос.message.message_id, reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТА)
        else:
            await context.bot.edit_message_text("Меню", update.effective_chat.id, инлайн_запрос.message.message_id,
                                                reply_markup=КЛАВАИНЛАМЕНЮ)

    # ОБНОВИЛ
    if инлайн_запрос.data == 'заявка':

        id_пользователя = update.effective_user.id
        подключение = sqlite3.connect("ANDREY_database.db")
        cursor = подключение.cursor()
        cursor.execute("SELECT статус_регистрации FROM пользователи WHERE id_пользователя = ?", (id_пользователя,))
        статус_регистрации = cursor.fetchone()
        подключение.close

        if статус_регистрации[0] != '2':
            asyncio.create_task(событие_заявка(update, context))
        else:
            await context.bot.send_message(update.effective_chat.id, "The application can be sent only once.")
    # ОБНОВИЛ

    # ===============================================================================================================
    # ===============================================================================================================
    if инлайн_запрос.data == 'настройка_рабочих_групп':
        # if update._effective_user.id == 1035268638:
        # if update.message and update.message.chat.type == 'supergroup' or update.message and update.message.chat.type == 'group':
        подключение = sqlite3.connect("ANDREY_database.db")
        cursor = подключение.cursor()
        cursor.execute("SELECT имя_группы_анкет, id_группы_анкет FROM настройки")
        имя_группы_анкет, id_анкетной_группы_база = cursor.fetchone()
        подключение.close()
        await asyncio.sleep(1)

        await context.bot.edit_message_text(
            f"Настройка рабочих чатов \U00002699\n\n"
            f"Рабочий чат: [{имя_группы_анкет}]\n\n"
            f"Для каких целей назначить данный чат?",
            update.effective_chat.id, инлайн_запрос.message.message_id, reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТАРАБГРУППЫ)
    # else:
    #    await context.bot.answer_callback_query(инлайн_запрос.id, "🚫Вам запрещено это действие🚫", show_alert=True)

    if инлайн_запрос.data == 'назад_настройки_бота_группы':
        # if update._effective_user.id == 1035268638:
        # if update.message and update.message.chat.type == 'supergroup' or update.message and update.message.chat.type == 'group':
        await context.bot.edit_message_text("Какие будут указания?", update.effective_chat.id,
                                            инлайн_запрос.message.message_id, reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТА)
        context.user_data["режим_рассылки"] = 0
    # else:
    #    await context.bot.answer_callback_query(инлайн_запрос.id, "🚫Вам запрещено это действие🚫", show_alert=True)

    if инлайн_запрос.data == 'закрыть_настройки_бота':
        # if update._effective_user.id == 1035268638:
        # if update.message and update.message.chat.type == 'supergroup' or update.message and update.message.chat.type == 'group':
        try:
            await context.bot.delete_message(update.effective_chat.id, инлайн_запрос.message.id)
        except telegram.error.ChatMigrated:
            await context.bot.answer_callback_query(инлайн_запрос.id,
                                                    "⚠️ Невозможно закрыть панель, так как группа стала супергруппой ⚠️\n\nПожалуйста, создаёте новую панель и не используйте старую.",
                                                    show_alert=True)
        # else:
        #    await context.bot.answer_callback_query(инлайн_запрос.id, "🚫Вам запрещено это действие🚫", show_alert=True)

    if инлайн_запрос.data == 'установить_группу_анкет':
        # if update._effective_user.id == 1035268638:
        # if update.message and update.message.chat.type == 'supergroup' or update.message and update.message.chat.type == 'group':
        # global id_анкетной_группы

        подключение = sqlite3.connect("ANDREY_database.db")
        cursor = подключение.cursor()
        cursor.execute("UPDATE настройки SET имя_группы_анкет = ?, id_группы_анкет = ?",
                       (update.effective_chat.effective_name, update.effective_chat.id))
        подключение.commit()
        await context.bot.answer_callback_query(инлайн_запрос.id,
                                                f"Чат [{update.effective_chat.effective_name}] назначен как рабочий!",
                                                show_alert=True)

        cursor.execute("SELECT имя_группы_анкет, id_группы_анкет FROM настройки")
        имя_группы_анкет, id_анкетной_группы_база = cursor.fetchone()
        подключение.close()

        id_анкетной_группы = int(id_анкетной_группы_база)
        await context.bot.edit_message_text(
            f"Настройка рабочих чатов \U00002699\n\nРабочий чат: [{имя_группы_анкет}]\n\nДля каких целей назначить данный чат?",
            update.effective_chat.id, инлайн_запрос.message.message_id, reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТАРАБГРУППЫ)
    # else:
    #    await context.bot.answer_callback_query(инлайн_запрос.id, "🚫Вам запрещено это действие🚫", show_alert=True)
    # ===============================================================================================================
    # ===============================================================================================================

    # ОБНОВИЛ
    if инлайн_запрос.data == 'подтвердить_заявку':

        try:
            анкета = инлайн_запрос.message.text
            id_из_анкеты = re.search(r'ID пользователя: (.+)', анкета)
            id_пользователя = id_из_анкеты.group(1)

            подключение = sqlite3.connect("ANDREY_database.db")
            cursor = подключение.cursor()
            cursor.execute("UPDATE пользователи SET статус_регистрации = ? WHERE id_пользователя = ?",
                           ("2", id_пользователя))
            cursor.execute(
                "SELECT имя_заявка, страна_заявка, дата_рождения_заявка, номер_заявка, маил_заявка, предыдущая_страна_заявка, паспорт_заявка, паспорт_на_русском_заявка, фото_студент_заявка, виза_заявка, выписка_заявка FROM пользователи WHERE id_пользователя = ?",
                (id_пользователя,))
            заявка_база = cursor.fetchone()
            подключение.commit()
            подключение.close

            scope = ['https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive"]
            credentials = ServiceAccountCredentials.from_json_keyfile_name(путь_токена_googel_api, scope)
            client = gspread.authorize(credentials)
            лист_заявки = client.open(имя_гугл_таблицы).worksheet(имя_листа_заявки)
            лист_заявки.append_row(
                [заявка_база[0], заявка_база[1], заявка_база[2], заявка_база[3], заявка_база[4], заявка_база[5],
                 заявка_база[6], заявка_база[7], заявка_база[8], заявка_база[9], заявка_база[10], id_пользователя],
                'USER_ENTERED')

            await context.bot.send_message(id_пользователя, "The application has been confirmed!")
            await context.bot.edit_message_reply_markup(update.effective_chat.id, инлайн_запрос.message.id,
                                                        reply_markup=None)

        except Exception as e:
            print("🔴 ОШИБКА")
            traceback.print_exc(limit=1)
            строка_ошибки = f"\n\nСтрока, в которой произошла ошибка: {traceback.format_exc(limit=1)}"
            код_ошибки = f"Код ошибки: {type(e).__name__}"
            содержание_ошибки = f"\nСодержание: {str(e)}"
            await context.bot.send_message(update.effective_chat.id,
                                           "❌ Произошла ошибка при обновлении данных\n\n" + код_ошибки + содержание_ошибки + строка_ошибки + "\n\nПожалуйста, обратитесь в службу технической поддержки.")

    if инлайн_запрос.data == 'отклонить_заявку':
        context.user_data["этап_отмена_заявки"] = 1

        анкета = инлайн_запрос.message.text
        id_из_анкеты = re.search(r'ID пользователя: (.+)', анкета)
        id_пользователя = id_из_анкеты.group(1)

        context.user_data["id_отмена_заявки"] = id_пользователя
        asyncio.create_task(событие_юнити(update, context))
        await context.bot.edit_message_reply_markup(update.effective_chat.id, инлайн_запрос.message.message_id,
                                                    reply_markup=None)

    if инлайн_запрос.data == 'ответ_причина_отмена_заявка':
        context.user_data["этап_отмена_заявки"] = 0
        id_пользователя = context.user_data["id_отмена_заявки"]
        await context.bot.send_message(id_пользователя, "#The_administrator's_response")
        await context.bot.copy_message(id_пользователя, update.effective_chat.id, инлайн_запрос.message.id,
                                       reply_markup=None)
        del context.user_data["id_отмена_заявки"]
        await context.bot.edit_message_reply_markup(update.effective_chat.id, инлайн_запрос.message.message_id,
                                                    reply_markup=None)
        await context.bot.answer_callback_query(инлайн_запрос.id, "Комментарий по заявке успешно отправлен!",
                                                show_alert=True)

    # ОБНОВИЛ

    await инлайн_запрос.answer()


# =========================================================================================================================================
#                             ОБРАБОТЧИКИ СОБЫТИЙ КОМАНДЫ
# =========================================================================================================================================


# Команда start
async def событие_старт(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(update.effective_user.first_name)

    if update.effective_chat.id != id_анкетной_группы:
        # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
        # ДОБАВЛЕНИЕ НОВОГО ПОЛЬЗОВАТЕЛЯ В БАЗУ ДАННЫХ
        id_пользователя = update.effective_user.id
        имя_пользователя = update.effective_user.username
        подключение = sqlite3.connect("ANDREY_database.db")
        cursor = подключение.cursor()
        cursor.execute("SELECT статус_регистрации FROM пользователи WHERE id_пользователя = ?", (id_пользователя,))
        if cursor.fetchone() == None:
            cursor.execute("INSERT INTO пользователи (id_пользователя, имя_пользователя) VALUES (?, ?)",
                           (id_пользователя, имя_пользователя))
            подключение.commit()

        cursor.execute("SELECT статус_регистрации FROM пользователи WHERE id_пользователя = ?", (id_пользователя,))
        статус_регистрации_база = cursor.fetchone()[0]
        подключение.close()
        # ////////////////////////////////////////////////

        context.user_data["обращение_в_техподдержку"] = 0

        # print(update.message.from_user.language_code)

        if статус_регистрации_база == '0':
            # Мультиязычность организовывается при получении кода языка пользователя
            мультиязычнность = {
                'en': "Hi! I don't know you, so let's register)",
                'ru': "Hi! I don't know you, so let's register)"}
            if update.message.from_user.language_code in мультиязычнность:
                await context.bot.send_message(update.effective_chat.id,
                                               мультиязычнность[update.message.from_user.language_code])
            else:
                # await context.bot.send_message(update.effective_chat.id, f"Этот язык: {update.message.from_user.language_code}, мне пока не известен(")
                await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
            await context.bot.send_message(update.effective_chat.id,
                                           "By this confirmation you consent to the processing of your personal data.",
                                           reply_markup=КЛАВАИНЛАПЕРВОЕПОДТВЕРЖДЕНИЕРЕГИСТРАЦИИ)
            context.user_data["этап_анкеты"] = 1
        else:
            asyncio.create_task(событие_меню(update, context, update.message.from_user.language_code))


# Команда get_id
async def событие_получить_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(update.effective_chat.id, f"\ *User ID:* `{context._user_id}`",
                                   parse_mode=ParseMode.MARKDOWN_V2)
    await context.bot.send_message(update.effective_chat.id, f"\ *Chat ID:* \ `\{context._chat_id}`",
                                   parse_mode=ParseMode.MARKDOWN_V2)


# Команда настройки бота
async def событие_настройки_бота(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # if update.effective_user.id == 1035268638:
    if update.message and update.message.chat.type == 'supergroup' or update.message and update.message.chat.type == 'group':
        context.user_data["ввод_пароля"] = 1
        await context.bot.send_message(update.effective_chat.id, "Какой пароль?", disable_notification=True)
        await context.bot.delete_message(update.effective_chat.id, update.message.id)


async def событие_настройки_бота_запуск(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.chat.type == 'supergroup' or update.message and update.message.chat.type == 'group':
        await context.bot.send_message(update.effective_chat.id, "Какие будут указания?", disable_notification=True,
                                       reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТА)
        await context.bot.delete_message(update.effective_chat.id, update.message.id)


# =========================================================================================================================================
#                             ОБРАБОТЧИКИ СОБЫТИЙ СООБЩЕНИЯ
# =========================================================================================================================================


async def событие_меню(update: Update, context: ContextTypes.DEFAULT_TYPE, language_code: None):
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    мультиязычнность = {
        'en': "Main menu",
        'ru': "Main menu"}
    if update.message and update.message.from_user.language_code in мультиязычнность or update.callback_query and update.callback_query.from_user.language_code in мультиязычнность or language_code in мультиязычнность:
        await context.bot.send_message(update.effective_chat.id, мультиязычнность[
            update.message and update.message.from_user.language_code or update.callback_query and update.callback_query.from_user.language_code or language_code],
                                       reply_markup=КЛАВАИНЛАМЕНЮ)
    else:
        await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"], reply_markup=КЛАВАИНЛАМЕНЮ)
    # /////////////////////////////
    context.user_data["этап_анкеты"] = 0
    context.user_data["обращение_в_техподдержку"] = 0
    context.user_data["заполнение_заявки"] = 0


async def событие_техподдержка(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["обращение_в_техподдержку"] = 1
    context.user_data["заполнение_заявки"] = 0
    context.user_data["этап_анкеты"] = 0
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    мультиязычнность = {
        'en': "What is your problem? Please write everything in one message.",
        'ru': "What is your problem? Please write everything in one message."}
    if update.callback_query.from_user.language_code in мультиязычнность:
        await context.bot.send_message(update.effective_chat.id,
                                       мультиязычнность[update.callback_query.from_user.language_code])
    else:
        await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
    # /////////////////////////////


async def событие_заявка(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["обращение_в_техподдержку"] = 0
    context.user_data["заполнение_заявки"] = 1
    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
    мультиязычнность = {
        'en': "I am ready to accept your application!\n\nFirst, write your name.",
        'ru': "I am ready to accept your application!\n\nFirst, write your name."}
    if update.callback_query.message.from_user.language_code in мультиязычнность:
        await context.bot.send_message(update.effective_chat.id,
                                       мультиязычнность[update.message.from_user.language_code])
    else:
        await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
    # /////////////////////////////


список_страниц = []
количество_страниц = None
количество_вопросов_на_странице = 9


async def загрузка_списка_вопросов():
    подключение = sqlite3.connect("ANDREY_database.db")
    cursor = подключение.cursor()
    # Получаем номер вопроса по естественному порядку и сам вопрос
    cursor.execute(
        "SELECT ROW_NUMBER() OVER (ORDER BY ROWID) AS порядок, вопрос FROM вопрос_ответ WHERE id IS NOT NULL")
    вопросы = cursor.fetchall()
    # print(вопросы)
    # Получаем общее число записей вопросов
    cursor.execute("SELECT COUNT(*) FROM вопрос_ответ")
    количество_вопросов = cursor.fetchone()[0]
    подключение.close()

    global количество_страниц
    # Находим число страниц деля общее количество вопросов на количество которое должно быть на странице
    количество_страниц = math.ceil(
        количество_вопросов / количество_вопросов_на_странице)  # Получаем наибольшее целое число страниц  WHERE вопрос IS NOT NULL
    # print(количество_страниц)

    # Инициируем список страниц, в котором будут храниться номер страницы и текст страницы
    global список_страниц
    список_страниц.clear()

    # 1. Изначально есть пустой список страниц
    # 2. Пустой списко количества страниц

    # Список страниц надо наполнить страницами
    # Каждую страницу надо наполнить текстом

    # 1. Получаем номер страницы
    # 2. Создаём список который будет хранить текст для страницы
    # 3. Дальше надо добавить текст в этот список
    # 4. По этому создаём цикл который получает вопросы но не больше указанного числа раз
    # 5. И каждый полученный вопрос добавляет в список текста для страницы
    # 6. Дальше итерация заканчивается и мы создаём переменную, которая является строкой с переносом после каждой строки
    # 7. Создаём список который представляет собой страницу, в которой содежится номер страницы и текст страницы, номер не используется
    # 8. В список страниц добавляет готовую страницу с пронумерованным текстом

    # Цикл проходит по каждой странице и создаёт для каждой страницы текст
    for i in range(количество_страниц):
        # Делаем копию всех вопросов вообще
        копия_вопросы = вопросы.copy()
        # Создаём список который будет содержать текст для одной страницы
        список_вопросов_страницы = []
        # Создаём цикл который получает номер вопроса и сам вопрос
        for a, вопрос in enumerate(копия_вопросы):
            # Если номер вопроса меньше либо равен указанному числу, то вопрос добавляется в текст страницы
            if a < количество_вопросов_на_странице:
                список_вопросов_страницы.append(f"[{вопрос[0]}] {вопрос[1]}")
                # А после добавленный вопрос удаляется из списка вопросов
                вопросы.remove(вопрос)

        #
        текст_страницы = "\n".join(список_вопросов_страницы)
        страница = [i + 1, текст_страницы]
        список_страниц.append(страница)


# =========================================================================================================================================
#                             НАЧАЛО СОБЫТИЕ ЮНИТИ
# =========================================================================================================================================


async def событие_юнити(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Пароль админ панели
    if update.message and update.message.chat.type == 'supergroup' or update.message and update.message.chat.type == 'group':
        if "ввод_пароля" in context.user_data and context.user_data["ввод_пароля"] == 1:
            if update.message.text == "TbrdpPsJMnQc6zZsOjO9":
                context.user_data["ввод_пароля"] = 0000
                asyncio.create_task(событие_настройки_бота_запуск(update, context))
                return

    if update.effective_chat.id != id_анкетной_группы:

        if "этап_анкеты" in context.user_data and context.user_data["этап_анкеты"] == 1:
            await context.bot.send_chat_action(update.effective_chat.id, "typing")
            await asyncio.sleep(1.5)
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            мультиязычнность = {
                'en': "Write your name",
                'ru': "Write your name"}
            if update.effective_message.from_user.language_code in мультиязычнность:
                await context.bot.send_message(update.effective_chat.id,
                                               мультиязычнность[update.message.from_user.language_code])
            else:
                await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
            # /////////////////////////////
            context.user_data["этап_анкеты"] = 2
            return

        if "этап_анкеты" in context.user_data and context.user_data["этап_анкеты"] == 2:
            context.user_data["имя"] = update.message.text
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            мультиязычнность = {
                'en': "What country are you from?",
                'ru': "What country are you from?"}
            if update.message.from_user.language_code in мультиязычнность:
                await context.bot.send_message(update.effective_chat.id,
                                               мультиязычнность[update.message.from_user.language_code])
            else:
                await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
            # /////////////////////////////
            context.user_data["этап_анкеты"] = 3
            return

        if "этап_анкеты" in context.user_data and context.user_data["этап_анкеты"] == 3:
            context.user_data["страна"] = update.message.text
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            мультиязычнность = {
                'en': "Write down your contact number",
                'ru': "Write down your contact number"}
            if update.message.from_user.language_code in мультиязычнность:
                await context.bot.send_message(update.effective_chat.id,
                                               мультиязычнность[update.message.from_user.language_code])
            else:
                await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
            # /////////////////////////////
            context.user_data["этап_анкеты"] = 4
            return

        if "этап_анкеты" in context.user_data and context.user_data["этап_анкеты"] == 4:
            context.user_data["номер"] = update.message.text
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            мультиязычнность = {
                'en': "And write your email",
                'ru': "And write your email"}
            if update.message.from_user.language_code in мультиязычнность:
                await context.bot.send_message(update.effective_chat.id,
                                               мультиязычнность[update.message.from_user.language_code])
            else:
                await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
            # /////////////////////////////
            context.user_data["этап_анкеты"] = 5
            return

        if "этап_анкеты" in context.user_data and context.user_data["этап_анкеты"] == 5:
            context.user_data["элпочта"] = update.message.text
            context.user_data["этап_анкеты"] = 6

            имя = context.user_data["имя"]
            страна = context.user_data["страна"]
            номер = context.user_data["номер"]
            элпочта = context.user_data["элпочта"]
            id_пользователя = update.effective_user.id

            подключение = sqlite3.connect("ANDREY_database.db")
            cursor = подключение.cursor()
            cursor.execute(
                "UPDATE пользователи SET статус_регистрации = ?, имя = ?, страна = ?, номер = ?, элпочта = ? WHERE id_пользователя = ?",
                (1, имя, страна, номер, элпочта, id_пользователя))
            подключение.commit()
            подключение.close

            await context.bot.send_message(id_анкетной_группы, f"Анкета\n\n{имя}\n{страна}\n{номер}\n{элпочта}")
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            мультиязычнность = {
                'en': "Great! Registration is completed",
                'ru': "Great! Registration is completed"}
            if update.message.from_user.language_code in мультиязычнность:
                await context.bot.send_message(update.effective_chat.id,
                                               мультиязычнность[update.message.from_user.language_code])
            else:
                await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
            # /////////////////////////////

            # ОБНОВИЛ
            scope = ['https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive"]
            credentials = ServiceAccountCredentials.from_json_keyfile_name(путь_токена_googel_api, scope)
            client = gspread.authorize(credentials)
            лист_регистрация = client.open(имя_гугл_таблицы).worksheet(имя_листа_регистрация)
            лист_регистрация.append_row([имя, страна, номер, элпочта, id_пользователя])
            # лист_заявки = client.open('Таблица_ТЕСТ').worksheet("Заявки")
            # лист_заявки.append_row([имя, страна, номер, элпочта, id_пользователя])
            asyncio.create_task(событие_меню(update, context, update.message.from_user.language_code))
            # ОБНОВИЛ

            return

        if "обращение_в_техподдержку" in context.user_data and context.user_data["обращение_в_техподдержку"] == 1:
            # await context.bot.copy_message(update.effective_chat.id, update.effective_chat.id, update.message.message_id, reply_markup=КЛАВАИНЛАПОМОЩЬОТПРАВИТЬ)
            # await context.bot.delete_message(update.effective_chat.id, update.message.message_id)
            await context.bot.send_message(update.effective_chat.id, "^^^^^^^^^^^^^^",
                                           reply_markup=КЛАВАИНЛАПОМОЩЬОТПРАВИТЬ)
            return

        # ВОПРОС СТРАНА
        if "заполнение_заявки" in context.user_data and context.user_data["заполнение_заявки"] == 1:
            context.user_data["имя_заявка"] = update.message.text
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            мультиязычнность = {
                'en': "Fine. Now write, what country are you from?",
                'ru': "Fine. Now write, what country are you from?"}
            if update.message.from_user.language_code in мультиязычнность:
                await context.bot.send_message(update.effective_chat.id,
                                               мультиязычнность[update.message.from_user.language_code])
            else:
                await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
            # /////////////////////////////
            context.user_data["заполнение_заявки"] = 2
            return

        # ВОПРОС ДАТА
        if "заполнение_заявки" in context.user_data and context.user_data["заполнение_заявки"] == 2:
            context.user_data["страна_заявка"] = update.message.text
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            мультиязычнность = {
                'en': "Now write your date of birth in the format DD.MM.YYYY",
                'ru': "Now write your date of birth in the format DD.MM.YYYY"}
            if update.message.from_user.language_code in мультиязычнность:
                await context.bot.send_message(update.effective_chat.id,
                                               мультиязычнность[update.message.from_user.language_code])
            else:
                await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
            # /////////////////////////////
            context.user_data["заполнение_заявки"] = 3
            return

        # ВОПРОС НОМЕР
        if "заполнение_заявки" in context.user_data and context.user_data["заполнение_заявки"] == 3:
            дата_рождения = update.message.text.replace(".", "")
            if дата_рождения.isdigit() and len(дата_рождения) == 8:
                if 1923 <= int(дата_рождения[4:]) <= 2009:
                    if int(дата_рождения[2:4]) <= 12:
                        if int(дата_рождения[:2]) <= 31:
                            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                            мультиязычнность = {
                                'en': "Now write down your contact number",
                                'ru': "Now write down your contact number"}
                            if update.message.from_user.language_code in мультиязычнность:
                                await context.bot.send_message(update.effective_chat.id,
                                                               мультиязычнность[update.message.from_user.language_code])
                            else:
                                await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
                            # /////////////////////////////
                            правильная_дата_рождения = f"{дата_рождения[:2]}.{дата_рождения[2:4]}.{дата_рождения[4:]}"
                            context.user_data["дата_рождения_заявка"] = правильная_дата_рождения
                            context.user_data["заполнение_заявки"] = 4
                            return
                        else:
                            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                            мультиязычнность1 = {
                                'en': "Hmm, I think you made a mistake. Try again..",
                                'ru': "Hmm, I think you made a mistake. Try again.."}
                            if update.message.from_user.language_code in мультиязычнность1:
                                await context.bot.send_message(update.effective_chat.id, мультиязычнность1[
                                    update.message.from_user.language_code])
                            else:
                                await context.bot.send_message(update.effective_chat.id, мультиязычнность1["en"])
                            # /////////////////////////////
                            return
                    else:
                        # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                        мультиязычнность2 = {
                            'en': "Hmm, I think you made a mistake. Try again..",
                            'ru': "Hmm, I think you made a mistake. Try again.."}
                        if update.message.from_user.language_code in мультиязычнность2:
                            await context.bot.send_message(update.effective_chat.id,
                                                           мультиязычнность2[update.message.from_user.language_code])
                        else:
                            await context.bot.send_message(update.effective_chat.id, мультиязычнность2["en"])
                        # /////////////////////////////
                    return
                else:
                    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                    мультиязычнность3 = {
                        'en': "Hmm, I think you made a mistake. Try again..",
                        'ru': "Hmm, I think you made a mistake. Try again.."}
                    if update.message.from_user.language_code in мультиязычнность3:
                        await context.bot.send_message(update.effective_chat.id,
                                                       мультиязычнность3[update.message.from_user.language_code])
                    else:
                        await context.bot.send_message(update.effective_chat.id, мультиязычнность3["en"])
                    # /////////////////////////////
                    return
            else:
                # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                мультиязычнность4 = {
                    'en': "Hmm, I think you made a mistake. Try again..",
                    'ru': "Hmm, I think you made a mistake. Try again.."}
                if update.message.from_user.language_code in мультиязычнность4:
                    await context.bot.send_message(update.effective_chat.id,
                                                   мультиязычнность4[update.message.from_user.language_code])
                else:
                    await context.bot.send_message(update.effective_chat.id, мультиязычнность4["en"])
                # /////////////////////////////
                return

        # ВОПРОС E-MAIL
        if "заполнение_заявки" in context.user_data and context.user_data["заполнение_заявки"] == 4:
            context.user_data["номер_заявка"] = update.message.text
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            мультиязычнность = {
                'en': "I also need your e-mail",
                'ru': "I also need your e-mail"}
            if update.message.from_user.language_code in мультиязычнность:
                await context.bot.send_message(update.effective_chat.id,
                                               мультиязычнность[update.message.from_user.language_code])
            else:
                await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
            # /////////////////////////////
            context.user_data["заполнение_заявки"] = 5
            return

        # ВОПРОС ПРЕДЫДУЩАЯ СТРАНА
        if "заполнение_заявки" in context.user_data and context.user_data["заполнение_заявки"] == 5:
            context.user_data["маил_почта_заявка"] = update.message.text
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            мультиязычнность = {
                'en': "In which country did you study before?",
                'ru': "In which country did you study before?"}
            if update.message.from_user.language_code in мультиязычнность:
                await context.bot.send_message(update.effective_chat.id,
                                               мультиязычнность[update.message.from_user.language_code])
            else:
                await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
            # /////////////////////////////
            context.user_data["заполнение_заявки"] = 6
            return

        # 1
        # ВОПРОС ФОТО ПАСПОРТ
        if "заполнение_заявки" in context.user_data and context.user_data["заполнение_заявки"] == 6:
            context.user_data["предыдущая_страна_заявка"] = update.message.text
            # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
            мультиязычнность = {
                'en': "I need a photo of your passport in .pdf or .jpg format.",
                'ru': "I need a photo of your passport in .pdf or .jpg format."}
            if update.message.from_user.language_code in мультиязычнность:
                await context.bot.send_message(update.effective_chat.id,
                                               мультиязычнность[update.message.from_user.language_code])
            else:
                await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
            # /////////////////////////////
            context.user_data["заполнение_заявки"] = 7
            return

        # 2
        # ВОПРОС ФОТО ПАСПОРТ ПЕРЕВОД
        if "заполнение_заявки" in context.user_data and context.user_data["заполнение_заявки"] == 7:
            if update.message.photo or update.message.document:
                context.user_data["паспорт_заявка"] = update.message.id
                context.user_data["паспорт_заявка_файл"] = update.message.photo[-1].file_id
                # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                мультиязычнность = {
                    'en': "I need a photo of your passport with a translation into Russian in .pdf or .jpg.",
                    'ru': "I need a photo of your passport with a translation into Russian in .pdf or .jpg."}
                if update.message.from_user.language_code in мультиязычнность:
                    await context.bot.send_message(update.effective_chat.id,
                                                   мультиязычнность[update.message.from_user.language_code])
                else:
                    await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
                # /////////////////////////////
                context.user_data["заполнение_заявки"] = 8
                return
            else:
                # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                мультиязычнность1 = {
                    'en': "The .pdf or .jpg format is required.",
                    'ru': "The .pdf or .jpg format is required."}
                if update.message.from_user.language_code in мультиязычнность1:
                    await context.bot.send_message(update.effective_chat.id,
                                                   мультиязычнность1[update.message.from_user.language_code])
                else:
                    await context.bot.send_message(update.effective_chat.id, мультиязычнность1["en"])
                # /////////////////////////////
                return

        # 3
        # ВОПРОС ФОТО СТУДЕНТА
        if "заполнение_заявки" in context.user_data and context.user_data["заполнение_заявки"] == 8:
            if update.message.photo or update.message.document:
                context.user_data["паспорт_русский_заявка"] = update.message.id
                context.user_data["паспорт_русский_заявка_файл"] = update.message.photo[-1].file_id
                # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                мультиязычнность = {
                    'en': "Now I need a photo of the student in .jpg for passport, size 4x3, white background, sharp and clear",
                    'ru': "Now I need a photo of the student in .jpg for passport, size 4x3, white background, sharp and clear"}
                if update.message.from_user.language_code in мультиязычнность:
                    await context.bot.send_message(update.effective_chat.id,
                                                   мультиязычнность[update.message.from_user.language_code])
                else:
                    await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
                # /////////////////////////////
                context.user_data["заполнение_заявки"] = 9
                return
            else:
                # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                мультиязычнность1 = {
                    'en': "The .pdf or .jpg format is required.",
                    'ru': "The .pdf or .jpg format is required."}
                if update.message.from_user.language_code in мультиязычнность1:
                    await context.bot.send_message(update.effective_chat.id,
                                                   мультиязычнность1[update.message.from_user.language_code])
                else:
                    await context.bot.send_message(update.effective_chat.id, мультиязычнность1["en"])
                # /////////////////////////////
                return

        # 4
        # ВОПРОС ЗАПОЛНЕННАЯ ФОРМА ДЛЯ ВИЗЫ
        if "заполнение_заявки" in context.user_data and context.user_data["заполнение_заявки"] == 9:
            if update.message.photo:
                context.user_data["фото_студент_заявка"] = update.message.id
                context.user_data["фото_студент_заявка_файл"] = update.message.photo[-1].file_id
                # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                мультиязычнность = {
                    'en': "Completed and signed visa application form in .pdf or .jpg format.",
                    'ru': "Completed and signed visa application form in .pdf or .jpg format."}
                if update.message.from_user.language_code in мультиязычнность:
                    await context.bot.send_message(update.effective_chat.id,
                                                   мультиязычнность[update.message.from_user.language_code])
                else:
                    await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
                # /////////////////////////////
                context.user_data["заполнение_заявки"] = 10
                return
            else:
                # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                мультиязычнность1 = {
                    'en': "The .pdf or .jpg format is required.",
                    'ru': "The .pdf or .jpg format is required."}
                if update.message.from_user.language_code in мультиязычнность1:
                    await context.bot.send_message(update.effective_chat.id,
                                                   мультиязычнность1[update.message.from_user.language_code])
                else:
                    await context.bot.send_message(update.effective_chat.id, мультиязычнность1["en"])
                # /////////////////////////////
                return

        # 5
        # ВОПРОС 4500$
        if "заполнение_заявки" in context.user_data and context.user_data["заполнение_заявки"] == 10:
            if update.message.photo or update.message.document:
                context.user_data["виза_заявка"] = update.message.id
                context.user_data["виза_заявка_файл"] = update.message.photo[-1].file_id
                # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                мультиязычнность = {
                    'en': "I also need a bank statement in your name with an account balance of $ 4,500 or the equivalent in local currency in the format.pdf or .jpg.",
                    'ru': "I also need a bank statement in your name with an account balance of $ 4,500 or the equivalent in local currency in the format.pdf or .jpg."}
                if update.message.from_user.language_code in мультиязычнность:
                    await context.bot.send_message(update.effective_chat.id,
                                                   мультиязычнность[update.message.from_user.language_code])
                else:
                    await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
                # /////////////////////////////
                context.user_data["заполнение_заявки"] = 11
                return
            else:
                # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                мультиязычнность1 = {
                    'en': "The .pdf or .jpg format is required.",
                    'ru': "The .pdf or .jpg format is required."}
                if update.message.from_user.language_code in мультиязычнность1:
                    await context.bot.send_message(update.effective_chat.id,
                                                   мультиязычнность1[update.message.from_user.language_code])
                else:
                    await context.bot.send_message(update.effective_chat.id, мультиязычнность1["en"])
                # /////////////////////////////
                return

        # ЗАВЕРШЕНИЕ И ОТПРАВКА ЗАЯВКИ
        if "заполнение_заявки" in context.user_data and context.user_data["заполнение_заявки"] == 11:
            if update.message.photo or update.message.document:
                context.user_data["выписка_заявка"] = update.message.id
                context.user_data["выписка_заявка_файл"] = update.message.photo[-1].file_id

                context.user_data["заполнение_заявки"] = 12

                имя_заявка = context.user_data["имя_заявка"]
                страна_заявка = context.user_data["страна_заявка"]
                дата_рождения_заявка = context.user_data["дата_рождения_заявка"]
                номер_заявка = context.user_data["номер_заявка"]
                маил_заявка = context.user_data["маил_почта_заявка"]
                предыдущая_страна_обучения_заявка = context.user_data["предыдущая_страна_заявка"]

                паспорт_заявка = context.user_data["паспорт_заявка"]
                паспорт_на_русском_заявка = context.user_data["паспорт_русский_заявка"]
                фото_студент_заявка = context.user_data["фото_студент_заявка"]
                виза_заявка = context.user_data["виза_заявка"]
                выписка_заявка = context.user_data["выписка_заявка"]

                список = [паспорт_заявка, паспорт_на_русском_заявка, фото_студент_заявка, виза_заявка, выписка_заявка]

                for фото in список:
                    await context.bot.forward_message(id_анкетной_группы, update.effective_chat.id, фото)

                # ОБНОВИЛ
                id_пользователя = update.effective_user.id
                await context.bot.send_message(id_анкетной_группы,
                                               f"Внимание! Новая заявка\nID пользователя: {id_пользователя}\nИмя: {имя_заявка}\nСтрана: {страна_заявка}\nДата рождения: {дата_рождения_заявка}\nКонтактный номер: {номер_заявка}\nМаил почта: {маил_заявка}\nПредыдущая страна обучения: {предыдущая_страна_обучения_заявка}",
                                               reply_markup=КЛАВАИНЛАПОДТВЕРДИТЬЗАЯВКУ)

                # Сохраняем завку в базу данных, а потом после подтверждения, получаем её и отправляем в гугл таблицу
                паспорт_заявка_файл = await context.bot.get_file(context.user_data["паспорт_заявка_файл"])
                паспорт_на_русском_заявка_файл = await context.bot.get_file(
                    context.user_data["паспорт_русский_заявка_файл"])
                фото_студент_заявка_файл = await context.bot.get_file(context.user_data["фото_студент_заявка_файл"])
                виза_заявка_файл = await context.bot.get_file(context.user_data["виза_заявка_файл"])
                выписка_заявка_файл = await context.bot.get_file(context.user_data["выписка_заявка_файл"])

                # Получаем ссылки на фото
                изображение1 = f'=image("{паспорт_заявка_файл.file_path}")'
                изображение2 = f'=image("{паспорт_на_русском_заявка_файл.file_path}")'
                изображение3 = f'=image("{фото_студент_заявка_файл.file_path}")'
                изображение4 = f'=image("{виза_заявка_файл.file_path}")'
                изображение5 = f'=image("{выписка_заявка_файл.file_path}")'

                подключение = sqlite3.connect("ANDREY_database.db")
                cursor = подключение.cursor()
                cursor.execute(
                    "UPDATE пользователи SET имя_заявка = ?, страна_заявка = ?, дата_рождения_заявка = ?, номер_заявка = ?, маил_заявка = ?, предыдущая_страна_заявка = ?, паспорт_заявка = ?, паспорт_на_русском_заявка = ?, фото_студент_заявка = ?, виза_заявка = ?, выписка_заявка = ? WHERE id_пользователя = ?",
                    (имя_заявка, страна_заявка, дата_рождения_заявка, номер_заявка, маил_заявка,
                     предыдущая_страна_обучения_заявка, изображение1, изображение2, изображение3, изображение4,
                     изображение5, id_пользователя))
                подключение.commit()
                подключение.close
                # ОБНОВИЛ

                # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                мультиязычнность = {
                    'en': "Great! The application has been submitted for moderation, please wait.",
                    'ru': "Great! The application has been submitted for moderation, please wait."}
                if update.message.from_user.language_code in мультиязычнность:
                    await context.bot.send_message(update.effective_chat.id,
                                                   мультиязычнность[update.message.from_user.language_code])
                else:
                    await context.bot.send_message(update.effective_chat.id, мультиязычнность["en"])
                # /////////////////////////////
                asyncio.create_task(событие_меню(update, context, update.message.from_user.language_code))
                return
            else:
                # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                мультиязычнность1 = {
                    'en': "The .pdf or .jpg format is required.",
                    'ru': "The .pdf or .jpg format is required."}
                if update.message.from_user.language_code in мультиязычнность1:
                    await context.bot.send_message(update.effective_chat.id,
                                                   мультиязычнность1[update.message.from_user.language_code])
                else:
                    await context.bot.send_message(update.effective_chat.id, мультиязычнность1["en"])
                # /////////////////////////////
                return

    if update.effective_chat.id == id_анкетной_группы:

        if update.message and update.message.reply_to_message and update.message.reply_to_message.forward_from:
            await context.bot.send_message(update.message.reply_to_message.forward_from.id, "#Tech_Support's_response")
            await context.bot.forward_message(update.message.reply_to_message.forward_from.id, id_анкетной_группы,
                                              update.message.reply_to_message.id)
            await context.bot.copy_message(update.message.reply_to_message.forward_from.id, id_анкетной_группы,
                                           update.message.message_id)
            await context.bot.send_message(id_анкетной_группы, "✅ Ответ успешно отправлен!")
        elif update.message and update.message.reply_to_message and not update.message.reply_to_message.forward_from:
            await context.bot.send_message(id_анкетной_группы,
                                           "⚠️Это не сообщение с вопросом либо настройки приватности не позволяют отправить ответ⚠️")
            return

        if "режим_рассылки" in context.user_data and context.user_data["режим_рассылки"] == 1:
            await context.bot.copy_message(update.effective_chat.id, update.effective_chat.id,
                                           update.message.message_id,
                                           reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТАРАССЫЛКАОТПРАВИТЬ)
            await context.bot.delete_message(update.effective_chat.id, update.message.message_id)
            return

        if "изменение_faq" in context.chat_data and context.chat_data["изменение_faq"] == 1:
            await context.bot.send_message(update.effective_chat.id, "Напши сообщение с вопросом ниже⤵️",
                                           reply_markup=КЛАВАИНЛАFAQОТМЕНА)
            context.chat_data["изменение_faq"] = 2
            context.chat_data["запись_вопроса"] = 1
            return

        if "изменение_faq" in context.chat_data and context.chat_data[
            "изменение_faq"] == 2 and "запись_вопроса" in context.chat_data and context.chat_data[
            "запись_вопроса"] == 1:
            await context.bot.copy_message(update.effective_chat.id, update.effective_chat.id,
                                           update.message.message_id,
                                           reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТАFAQСОХРАНИТЬВОПРОС)
            await context.bot.delete_message(update.effective_chat.id, update.message.message_id)
            return

        if "изменение_faq" in context.chat_data and context.chat_data[
            "изменение_faq"] == 2 and "запись_ответ" in context.chat_data and context.chat_data["запись_ответ"] == 1:
            await context.bot.copy_message(update.effective_chat.id, update.effective_chat.id,
                                           update.message.message_id,
                                           reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТАFAQСОХРАНИТЬОТВЕТ)
            await context.bot.delete_message(update.effective_chat.id, update.message.message_id)
            return

        if "добавление_faq" in context.user_data and context.user_data["добавление_faq"] == 1:
            await context.bot.send_message(update.effective_chat.id, "Напшии сообщение с вопросом ниже⤵️",
                                           reply_markup=КЛАВАИНЛАFAQДОБАВИТЬОТМЕНА)
            context.user_data["добавление_faq"] = 2
            context.user_data["запись_вопроса_добавление"] = 1
            return

        if "добавление_faq" in context.user_data and context.user_data[
            "добавление_faq"] == 2 and "запись_вопроса_добавление" in context.user_data and context.user_data[
            "запись_вопроса_добавление"] == 1:
            await context.bot.copy_message(update.effective_chat.id, update.effective_chat.id,
                                           update.message.message_id,
                                           reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТАFAQДОБАВИТЬВОПРОС)
            await context.bot.delete_message(update.effective_chat.id, update.message.message_id)
            return

        if "добавление_faq" in context.user_data and context.user_data[
            "добавление_faq"] == 2 and "запись_ответ_добавление" in context.user_data and context.user_data[
            "запись_ответ_добавление"] == 1:
            await context.bot.copy_message(update.effective_chat.id, update.effective_chat.id,
                                           update.message.message_id,
                                           reply_markup=КЛАВАИНЛАНАСТРОЙКИБОТАFAQДОБАВИТЬОТВЕТ)
            await context.bot.delete_message(update.effective_chat.id, update.message.message_id)
            return

        if "этап_отмена_заявки" in context.user_data and context.user_data["этап_отмена_заявки"] == 1:
            await context.bot.send_message(update.effective_chat.id, "Напшите причину отклонения заявк.")
            context.user_data["этап_отмена_заявки"] = 2
            return

        if "этап_отмена_заявки" in context.user_data and context.user_data["этап_отмена_заявки"] == 2:
            await context.bot.copy_message(update.effective_chat.id, update.effective_chat.id,
                                           update.message.message_id,
                                           reply_markup=КЛАВАИНЛАПОДТВЕРДИТЬЗАЯВКУОТМЕНАОТВЕТПРИЧИНА)
            await context.bot.delete_message(update.effective_chat.id, update.message.message_id)
            return


# =========================================================================================================================================
#                             ЗАПУСК И УСТАНОВКА ОБРАБОТЧИКОВ
# =========================================================================================================================================


if __name__ == '__main__':
    application = ApplicationBuilder().token(Токен).build()

    # Команды
    обработчик_старт = CommandHandler('start', событие_старт)
    обработчик_получить_id = CommandHandler('get_id', событие_получить_id)
    обработчик_приказ_императора = CommandHandler('service_i', событие_настройки_бота)

    # Общий обработчик для АНКЕТЫ
    обработка_анкета_юнити = MessageHandler(filters.ALL, событие_юнити)

    # Добавление обработчиков событий. Порядок важен!
    application.add_handler(обработчик_старт)
    application.add_handler(обработчик_получить_id)
    application.add_handler(обработчик_приказ_императора)

    application.add_handler(CallbackQueryHandler(событие_инлайн))
    # Самый последний
    application.add_handler(обработка_анкета_юнити)

    application.run_polling()