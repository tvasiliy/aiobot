import re
import datetime
import gettext
import os
import core.utils.timezone as utils_timezone
from aiogram.types import Message, ContentType, KeyboardButton, ReplyKeyboardMarkup, CallbackQuery,\
    ReplyKeyboardRemove, InlineKeyboardMarkup, ParseMode
from aiogram.dispatcher import Dispatcher, ctx
from aiogram.dispatcher.webhook import SendMessage, EditMessageReplyMarkup, EditMessageText, AnswerCallbackQuery, DeleteMessage
from .utils.utils import *
from core.middleware import PrepareMiddleware
from core.telegram.keyboard import Calendar, Watch
from core.telegram.user import create_user_voice_note, get_list_notification_dates, get_list_notification_times, \
    get_list_notes_by_date
from .models import update_timezone, get_last_note, create_notification, get_notification_by_note, \
    update_notification, get_list_active_notifications, find_user_by_id
from .sender import set_notification_job, cancel_jobs, count_jobs


STATE_LOCATION = 'location'
STATE_LOCATION_FROM_VOICE = 'location_voice'


_ = gettext.gettext
context_data = PrepareMiddleware()

help_text = _('⏰ <b>Бот</b> может напомнить о важном событии, прислав голосовую заметку, которую ему '
              'отправили.\n\n/settimezone — Позволяет установить часовой пояс по геолокации\n\n/mycalendar — Показывает '
              'календарь ваших заметок. С его помощью можно прослушать все голосовые заметки на выбранную дату и время'
              '\n\nЧтобы создать новую голосовую заметку, просто нажмите на микрофон в правом углу 👇'
              'и удерживайте его. Бот попросит выбрать дату и время, когда отправить эту заметку и '
              'отправит напоминание 🔔 именно в это время\n\nНравится бот? Оставьте отзыв по ссылке: ')


async def show_jobs(message: Message):
    cancel_jobs()
    count = count_jobs()
    list = await get_list_active_notifications()
    if count < 3:
        for row in list:
            user = await find_user_by_id(row.user_note_user_id)
            set_notification_job(user.telegram_id, row.user_notification_id, row.user_notification_notify_date, user.timezone)
    return SendMessage(chat_id=message.chat.id, text='Count:{0}/{1}'.format(count, count_jobs()))


async def callback_ignore(query: CallbackQuery):
    return AnswerCallbackQuery(callback_query_id=query.id, text=_('Нажмите другую кнопку:)'), show_alert=True)


async def cmd_start(message: Message):
    return SendMessage(chat_id=message.chat.id, text=help_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


async def received_voice(message: Message):
    now = context_data['user_time']
    ctx.get_dispatcher()['user_calendar_selected'] = (now.year, now.month)
    calendar = Calendar(now)
    markup = calendar.create_selected(now.year, now.month)

    if message.voice:
        voice_id = await create_user_voice_note(context_data['user_id'], message.voice)

        if context_data['request_timezone']:
            return await send_location(message, STATE_LOCATION_FROM_VOICE)

        return SendMessage(chat_id=message.chat.id, text=_('Выберите дату заметки:'), reply_markup=markup)


async def send_location(message: Message, state_loc=STATE_LOCATION):
    keyboard_button = KeyboardButton(_('Отправить местоположение'), request_location=True)
    markup = ReplyKeyboardMarkup([[keyboard_button]], one_time_keyboard=True)

    state = ctx.get_dispatcher().current_state(chat=message.chat.id, user=message.from_user.id)
    await state.reset_state()
    await state.set_state(state_loc)

    text = _('Задайте свой часовой пояс с помощью отправки вашего местоположения.\n'
             'Данный функционал доступен только для мобильных устройств')
    return SendMessage(chat_id=message.chat.id, text=text, reply_markup=markup)


async def set_timezone_by_location(message: Message):
    if hasattr(message.location, 'longitude') & hasattr(message.location, 'latitude'):
        timezone = utils_timezone.get_by_location(message.location.longitude, message.location.latitude)
        text = 'Установлен часовой пояс: {0}'.format(timezone)
    else:
        timezone = utils_timezone.get_default()
        text = 'Нам не удалось определить часовой пояс по геолокации, по-умолчанию установлен {0}'.format(timezone)

    await update_timezone(context_data['user_id'], timezone)

    state = ctx.get_dispatcher().current_state(chat=message.chat.id, user=message.from_user.id)
    await state.reset_state()

    return SendMessage(chat_id=message.chat.id, text=_(text), reply_markup=ReplyKeyboardRemove())


async def set_timezone_by_location_from_voice(message: Message):
    if hasattr(message.location, 'longitude') & hasattr(message.location, 'latitude'):
        timezone = utils_timezone.get_by_location(message.location.longitude, message.location.latitude)
        text = 'Ваш часовой пояс {0}'.format(timezone)
    else:
        timezone = utils_timezone.get_default()
        text = 'Часовой пояс установлен по-умолчанию {0}'.format(timezone)

    await update_timezone(context_data['user_id'], timezone)

    now = context_data['user_time']
    ctx.get_dispatcher()['user_calendar_selected'] = (now.year, now.month)
    calendar = Calendar(now)
    markup = calendar.create_selected(now.year, now.month)

    state = ctx.get_dispatcher().current_state(chat=message.chat.id, user=message.from_user.id)
    await state.reset_state()

    return SendMessage(chat_id=message.chat.id, text=_(text + '\nВыберите дату заметки:'), reply_markup=markup)


async def my_calendar(message: Message):
    markup = await get_my_calendar_markup()
    return SendMessage(chat_id=message.chat.id, text=_('Ваш календарь голосовых напоминаний. С его помощью можно '
                                                       'просмотреть все напоминания, которые будут отправлены в '
                                                       'будущем'), reply_markup=markup)


async def get_my_calendar_markup():
    now = context_data['user_time']
    ctx.get_dispatcher()['user_calendar_selected_history'] = (now.year, now.month)
    calendar = Calendar(now)
    list_notifications = await get_list_notification_dates(context_data['user_id'])
    markup = calendar.create_history(now.year, now.month, list_notifications)
    return markup


async def callback_calendar_previous_month(query: CallbackQuery):
    return await callback_calendar_selector(query, 'user', 'prev')


async def callback_calendar_next_month(query: CallbackQuery):
    return await callback_calendar_selector(query, 'user', 'next')


async def callback_calendar_previous_month_history(query: CallbackQuery):
    list_notifications = await get_list_notification_dates(context_data['user_id'])
    return await callback_calendar_selector(query, 'history', 'prev', list_notifications)


async def callback_calendar_next_month_history(query: CallbackQuery):
    list_notifications = await get_list_notification_dates(context_data['user_id'])
    return await callback_calendar_selector(query, 'history', 'next', list_notifications)


async def callback_calendar_select_day(query: CallbackQuery):
    search = re.search('^calendar-day-([0-9]{1,2})$', query.data)
    day = search.group(1)
    selected_date = ctx.get_dispatcher().get('user_calendar_selected')

    if selected_date is not None:
        t_selected = datetime.datetime(int(selected_date[0]), int(selected_date[1]), int(day))
        note = await get_last_note(context_data['user_id'])
        if note is not None:
            notify_id = await create_notification(note.id, t_selected)
            if notify_id > 0:
                watch = Watch()
                markup = watch.create_note_watch()
                text = '{0}\nВыберите время напоминания:'.format(t_selected.strftime("%Y-%m-%d"))
                return EditMessageText(chat_id=query.message.chat.id, message_id=query.message.message_id,
                                       text=_(text), reply_markup=markup)
        else:
            return SendMessage(chat_id=query.message.chat.id, text=_('Ошибка запроса, попробуйте позже'))


async def callback_watch_select_time(query: CallbackQuery):
    search = re.search('^calendar-time-([0-9]{1,2})$', query.data)
    time = search.group(1)
    if time is not None:
        note = await get_last_note(context_data['user_id'])
        if note is not None:
            notify = await get_notification_by_note(note.id)

            if notify is not None:
                notify_date = notify.notify_date.replace(hour=int(time))
                await update_notification(notify.id, notify_date)

                set_notification_job(query.message.chat.id, notify.id, notify_date, context_data['user_timezone'])

                bot = ctx.get_bot()
                await bot.answer_callback_query(callback_query_id=query.id,
                                          text=_('Заметка будет отправлена {0}\nВы можете создать новую заметку, '
                                                 'отправив голосовое сообщение'.format(notify_date)),
                                          show_alert=True
                                          )

                return EditMessageText(chat_id=query.message.chat.id, message_id=query.message.message_id,
                               text=help_text,
                               reply_markup=InlineKeyboardMarkup(),
                               parse_mode=ParseMode.HTML,
                               disable_web_page_preview=True)

    return SendMessage(chat_id=query.message.chat.id, text=_('Ошибка запроса, попробуйте позже'))


async def callback_calendar_select_day_history(query: CallbackQuery):
    search = re.search('^calendar-day-history-([0-9]{1,2})$', query.data)
    day = search.group(1)
    selected_date = ctx.get_dispatcher().get('user_calendar_selected_history')

    if selected_date is not None:
        t_selected = datetime.datetime(int(selected_date[0]), int(selected_date[1]), int(day))
        ctx.get_dispatcher()['user_calendar_history_date'] = t_selected

        watch = Watch()
        notification_list = await get_list_notification_times(context_data['user_id'])
        markup = watch.create_history_watch(t_selected, notification_list)
        text = 'Все голосовые заметки на {0}\nВыберите время напоминания:'.format(t_selected.strftime("%Y-%m-%d"))
        return EditMessageText(chat_id=query.message.chat.id, message_id=query.message.message_id,
                               text=_(text), reply_markup=markup)


async def callback_watch_history_select_time(query: CallbackQuery):
    search = re.search('^calendar-time-history-([0-9]{1,2})$', query.data)
    hour = search.group(1)
    selected_date = ctx.get_dispatcher().get('user_calendar_history_date')
    if selected_date is not None:
        notify_date = selected_date.replace(hour=int(hour))

        files = await get_list_notes_by_date(context_data['user_id'], notify_date)

        for file_id in files:
            bot = ctx.get_bot()
            await bot.send_voice(chat_id=query.message.chat.id, caption=str(notify_date), voice=file_id)

        return EditMessageText(chat_id=query.message.chat.id, message_id=query.message.message_id,
                               text=help_text,
                               reply_markup=InlineKeyboardMarkup(),
                               parse_mode=ParseMode.HTML,
                               disable_web_page_preview=True)


async def callback_calendar_selector(query, calendar_type='user', move='next', notify_list=None):
    chat_id = query.message.chat.id

    if calendar_type == 'user':
        key = 'user_calendar_selected'
    elif calendar_type == 'history':
        key = 'user_calendar_selected_history'

    selected_date = ctx.get_dispatcher().get(key)

    if selected_date is not None:
        if move == 'next':
            date = next_month(selected_date)
        elif move == 'prev':
            date = previous_month(selected_date)
        year, month = date

        ctx.get_dispatcher()[key] = date
        calendar = Calendar(context_data['user_time'])

        if calendar_type == 'user':
            markup = calendar.create_selected(year, month)
        elif calendar_type == 'history':
            markup = calendar.create_history(year, month, notify_list)
        return EditMessageReplyMarkup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=markup)
    else:
        # Do something to inform of the error
        pass


async def callback_close_keyboard(query: CallbackQuery):
    return DeleteMessage(chat_id=query.message.chat.id, message_id=query.message.message_id)


def setup_handlers(dispatcher: Dispatcher):
    dispatcher.middleware.setup(context_data)

    # start/welcome commands
    dispatcher.register_message_handler(cmd_start, commands=['start', 'help'])

    # mycalendar
    dispatcher.register_message_handler(my_calendar, commands=['mycalendar'])

    dispatcher.register_message_handler(show_jobs, commands=['show_jobs'])

    # voice handlers
    dispatcher.register_message_handler(received_voice, content_types=ContentType.VOICE)
    # location
    dispatcher.register_message_handler(send_location, commands=['settimezone'])
    dispatcher.register_message_handler(set_timezone_by_location_from_voice, content_types=ContentType.LOCATION,
                                        state=STATE_LOCATION_FROM_VOICE)
    dispatcher.register_message_handler(set_timezone_by_location_from_voice, content_types=ContentType.TEXT,
                                        state=STATE_LOCATION_FROM_VOICE)
    dispatcher.register_message_handler(set_timezone_by_location, content_types=ContentType.LOCATION,
                                        state=STATE_LOCATION)
    dispatcher.register_message_handler(set_timezone_by_location, content_types=ContentType.TEXT, state=STATE_LOCATION)

    # calendar
    dispatcher.register_callback_query_handler(callback_calendar_previous_month,
                                               func=lambda query: query.data == 'callback_previous_month')
    dispatcher.register_callback_query_handler(callback_calendar_next_month,
                                               func=lambda query: query.data == 'callback_next_month')
    dispatcher.register_callback_query_handler(callback_calendar_select_day,
                                               func=lambda query: bool(
                                                   re.search('^calendar-day-[0-9]{1,2}$', query.data,
                                                             flags=re.IGNORECASE | re.MULTILINE)))
    dispatcher.register_callback_query_handler(callback_watch_select_time,
                                               func=lambda query: bool(
                                                   re.search('^calendar-time-[0-9]{1,2}$', query.data,
                                                             flags=re.IGNORECASE | re.MULTILINE)))

    # calendar history
    dispatcher.register_callback_query_handler(callback_calendar_previous_month_history,
                                               func=lambda query: query.data == 'callback_previous_month_history')
    dispatcher.register_callback_query_handler(callback_calendar_next_month_history,
                                               func=lambda query: query.data == 'callback_next_month_history')
    dispatcher.register_callback_query_handler(callback_calendar_select_day_history,
                                               func=lambda query: bool(
                                                   re.search('^calendar-day-history-[0-9]{1,2}$', query.data,
                                                             flags=re.IGNORECASE | re.MULTILINE)))
    dispatcher.register_callback_query_handler(callback_watch_history_select_time,
                                               func=lambda query: bool(
                                                   re.search('^calendar-time-history-[0-9]{1,2}$', query.data,
                                                             flags=re.IGNORECASE | re.MULTILINE)))

    dispatcher.register_callback_query_handler(callback_ignore,
                                               func=lambda query: query.data == 'ignore')

    dispatcher.register_callback_query_handler(callback_close_keyboard,
                                               func=lambda query: query.data == 'close_keyboard')


