from aiogram import Bot
from core.utils.settings import settings
from core.models import NotifyStatus, NoteType, get_notification, get_note, update_notification_status
import logging
import os
import asyncio
import aiohttp


async def send_note(chat_id, notify_id):
    notify = get_notification(notify_id)
    if notify.user_notification_notify_status != NotifyStatus.processing:
        logging.warning('Notify %s status != %s', notify_id, NotifyStatus.processing)

    if notify.user_note_note_type == NoteType.voice:
        if notify.user_note_note_data is not None:
            note_data = notify.user_note_note_data
            logging.info('Sent note id %s', notify_id)
            bot = Bot(token=os.environ.get('TELEGRAM_TOKEN'))
            result = await bot.send_voice(chat_id, note_data['file_id'])
            if result is not None:
                await update_notification_status(notify_id, NotifyStatus.sent)


def main(chat_id, notify_id):
    event_loop = asyncio.get_event_loop()
    try:
        event_loop.run_until_complete(send_note(chat_id, notify_id))
    finally:
        session = aiohttp.ClientSession()
        session.close()
        event_loop.close()

