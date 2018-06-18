from core.models import create_user_note, NoteType, get_list_notifications
import logging


async def create_user_voice_note(user_id, voice):
    if not hasattr(voice, 'file_id'):
        return None
    try:
        json_voice = {
            'file_id': voice.file_id,
            'duration': voice.duration,
            'mime_type': voice.mime_type,
            'file_size': voice.file_size
        }
        return await create_user_note(user_id, NoteType.voice, json_voice)
    except BaseException as e:
        logging.warning('Error ' + e)


async def get_list_notification_dates(user_id):
    notifications = await get_list_notifications(user_id)

    user_notifications = {}
    if len(notifications) > 0:
        for row in notifications:
            user_notifications[str(str(row.user_notification_notify_date.date()))] = True

    return user_notifications


async def get_list_notification_times(user_id):
    notifications = await get_list_notifications(user_id)

    user_notifications = {}
    if len(notifications) > 0:
        for row in notifications:
            user_notifications[str(row.user_notification_notify_date)] = True

    return user_notifications


async def get_list_notes_by_date(user_id, notify_date):
    notifications = await get_list_notifications(user_id, notify_date)

    list = []
    for row in notifications:
        list.append(row.user_note_note_data['file_id'])

    return list