import asyncio
import sqlalchemy as sa
from aiopg.sa import create_engine
from sqlalchemy.sql import func
import logging
import enum
import os

dsn = os.environ.get('DATABASE_URL')


class NoteType(enum.Enum):
    voice = 1
    video = 2
    message = 3


class NotifyStatus(enum.Enum):
    created = 1
    processing = 2
    sent = 3
    cancelled = 4
    error = 5


metadata = sa.MetaData()

user = sa.Table('user', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('telegram_id', sa.Integer, unique=True),
    sa.Column('username', sa.String(255), index=True),
    sa.Column('first_name', sa.String(255)),
    sa.Column('is_bot', sa.Boolean, default=False),
    sa.Column('language_code', sa.String(20), index=True),
    sa.Column('timezone', sa.String(255), index=True),
    sa.Column('created_date', sa.DateTime, default=func.now()),
    sa.Column('login_date', sa.DateTime, default=func.now())
)

user_note = sa.Table('user_note', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('user_id', None, sa.ForeignKey('users.id')),
    sa.Column('note_type', sa.Enum(NoteType), index=True),
    sa.Column('note_data', sa.JSON),
    sa.Column('created_date', sa.DateTime, default=func.now()),
)

user_notify = sa.Table('user_notification', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('note_id', None, sa.ForeignKey('user_note.id')),
    sa.Column('notify_status', sa.Enum(NotifyStatus), default=NotifyStatus.created),
    sa.Column('notify_date', sa.DateTime),
)


async def get_user(from_user):
    if not hasattr(from_user, 'id'):
        return None

    telegram_id = from_user.id
    try:
        async with create_engine(dsn) as engine:

            async with engine.acquire() as conn:
                t_user = await find_user_by_telegram_id(telegram_id, conn)

                if t_user is None:
                    insert = user.insert().values(
                        telegram_id=telegram_id,
                        username=from_user.username,
                        first_name=from_user.first_name,
                        language_code=from_user.language_code,
                        is_bot=from_user.is_bot,
                    )
                    await conn.scalar(insert)
                    t_user = await find_user_by_telegram_id(telegram_id, conn)
                else:
                    await conn.execute(user.update().where(user.c.id == t_user.id).values(login_date=func.now()))

                return t_user
    except Exception as message:
        logging.warning(message)


async def get_list_notifications(user_id, notify_date=None):
    try:
        async with create_engine(dsn) as engine:

            async with engine.acquire() as conn:
                join = sa.join(user_notify, user_note, user_notify.c.note_id == user_note.c.id)
                select = sa.select([user_notify, user_note], use_labels=True).select_from(join).\
                    where(user_notify.c.notify_status == NotifyStatus.processing).\
                    where(user_note.c.user_id == user_id)
                if notify_date is not None:
                    select = select.where(user_notify.c.notify_date == notify_date)

                notify_list = []
                async for row in conn.execute(select):
                    notify_list.append(row)

                return notify_list
    except Exception as message:
        logging.warning(message)


async def get_list_active_notifications():
    try:
        async with create_engine(dsn) as engine:

            async with engine.acquire() as conn:
                join = sa.join(user_notify, user_note, user_notify.c.note_id == user_note.c.id)
                select = sa.select([user_notify, user_note], use_labels=True).select_from(join).\
                    where(user_notify.c.notify_status == NotifyStatus.processing)

                notify_list = []
                async for row in conn.execute(select):
                    notify_list.append(row)

                return notify_list
    except Exception as message:
        logging.warning(message)


async def find_user_by_telegram_id(telegram_id, conn):
    t_user = None
    async for row in conn.execute(user.select().where(user.c.telegram_id == telegram_id)):
        t_user = row
    return t_user


async def find_user_by_id(user_id):
    try:
        async with create_engine(dsn) as engine:

            async with engine.acquire() as conn:
                t_user = None
                async for row in conn.execute(user.select().where(user.c.id == user_id)):
                    t_user = row
                return t_user
    except Exception as message:
        logging.warning(message)


async def create_user_note(user_id, note_type, note_data):
    try:
        async with create_engine(dsn) as engine:

            async with engine.acquire() as conn:
                insert = user_note.insert().values(
                    note_type=note_type,
                    note_data=note_data,
                    user_id=user_id,
                )
                note_id = await conn.scalar(insert)
                if note_id is None:
                    logging.warning('Result/insert error')
                    return None
                else:
                    return note_id
    except BaseException as e:
        logging.warning('Error:' + e)


async def get_last_note(user_id):
    try:
        async with create_engine(dsn) as engine:

            async with engine.acquire() as conn:
                note = None
                select = user_note.select().where(user_note.c.user_id == user_id).order_by(sa.desc(user_note.c.id)).limit(1)
                async for row in conn.execute(select):
                    note = row
                if note is None:
                    logging.warning('Result/insert error')
                    return None
                else:
                    return note
    except BaseException as e:
        logging.warning('Error:' + e)


async def create_notification(note_id, note_date):
    try:
        async with create_engine(dsn) as engine:

            async with engine.acquire() as conn:
                insert = user_notify.insert().values(
                    note_id=note_id,
                    notify_date=note_date,
                )
                notify_id = await conn.scalar(insert)
                if notify_id is None:
                    logging.warning('Result/insert error')
                    return None
                else:
                    return notify_id
    except BaseException as e:
        logging.warning('Error:' + e)


async def update_notification(notify_id, notify_date, notify_status=NotifyStatus.processing):
    try:
        async with create_engine(dsn) as engine:

            async with engine.acquire() as conn:
                update = user_notify.update().where(user_notify.c.id == notify_id).values(
                    notify_date=notify_date,
                    notify_status=notify_status,
                )
                return await conn.execute(update)
    except BaseException as e:
        logging.warning('Error:' + e)


async def update_notification_status(notify_id, notify_status):
    try:
        async with create_engine(dsn) as engine:

            async with engine.acquire() as conn:
                update = user_notify.update().where(user_notify.c.id == notify_id).values(
                    notify_status=notify_status,
                )
                return await conn.execute(update)
    except BaseException as e:
        logging.warning('Error:' + e)


async def get_notification_by_note(note_id, notify_status=NotifyStatus.created):
    try:
        async with create_engine(dsn) as engine:

            async with engine.acquire() as conn:
                select = user_notify.select().\
                    where(user_notify.c.note_id == note_id).\
                    where(user_notify.c.notify_status == notify_status).\
                    order_by(sa.desc(user_notify.c.id)).limit(1)

                notify = None
                async for row in conn.execute(select):
                    notify = row
                if notify is None:
                    logging.warning('Result/insert error')
                    return None
                else:
                    return notify
    except BaseException as e:
        logging.warning('Error:' + e)


def get_notification(notify_id):
    try:
        engine = sa.create_engine(dsn)
        conn = engine.connect()
        if conn:
            join = sa.join(user_notify, user_note, user_notify.c.note_id == user_note.c.id)
            select = sa.select([user_notify, user_note], use_labels=True).select_from(join).\
                where(user_notify.c.id == notify_id).\
                order_by(sa.desc(user_notify.c.id)).limit(1)

            notify = None
            for row in conn.execute(select):
                notify = row
            if notify is None:
                logging.warning('Result/insert error')
                return None
            else:
                return notify
    except BaseException as e:
        logging.warning('Error:' + e)


async def get_note(note_id):
    try:
        async with create_engine(dsn) as engine:

            async with engine.acquire() as conn:
                select = user_note.select().\
                    where(user_note.c.id == note_id).\
                    order_by(sa.desc(user_note.c.id)).limit(1)

                note = None
                async for row in conn.execute(select):
                    note = row
                if note is None:
                    logging.warning('Result/insert error')
                    return None
                else:
                    return note
    except BaseException as e:
        logging.warning('Error:' + e)


async def update_timezone(user_id, timezone):
    try:
        async with create_engine(dsn) as engine:
            async with engine.acquire() as conn:
                await conn.execute(user.update().where(user.c.id == user_id).values(timezone=timezone))
                return True
    except BaseException as e:
        logging.warning('Error:' + e)



async def create_tables(conn):
    #await conn.execute("")
    return


async def go():
    async with create_engine(dsn) as engine:
        async with engine.acquire() as conn:
            await create_tables(conn)


loop = asyncio.get_event_loop()
loop.run_until_complete(go())