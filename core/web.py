import asyncio
import aiopg
import logging
import os
import functools
from logging import config

from aiohttp import web

from core.utils.settings import settings
from aiogram.dispatcher.webhook import get_new_configured_app
from aiogram.utils.executor import start_polling
from core.handlers import setup_handlers
from aiogram import Bot
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import context

loop = asyncio.get_event_loop()
loop.set_task_factory(context.task_factory)
# webhook config
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
WEBHOOK_HOST = os.environ.get('HOST')
WEBHOOK_URL_PATH = '/webhook' + '/' + TELEGRAM_TOKEN
WEBHOOK_URL = f"https://{WEBHOOK_HOST}{WEBHOOK_URL_PATH}"

# set logging settings
log = logging.getLogger(__name__)
logging.config.dictConfig(settings['logging'])

# aio debug
aio_debug = settings.get('asyncio_debug_enabled', False)
if aio_debug is True:
    loop.set_debug(True)

bot = Bot(TELEGRAM_TOKEN, loop=loop)
dispatcher = Dispatcher(bot, storage=MemoryStorage())


async def init_pg(app):
    engine = await aiopg.sa.create_engine(
        dsn=os.environ.get('DATABASE_URL'),
        loop=app.loop)
    app['db'] = engine


async def close_pg(app):
    app['db'].close()
    await app['db'].wait_closed()


async def on_shutdown(app, url=None):
    if url:
        # Remove webhook.
        await dispatcher.bot.delete_webhook()

    # Close Redis connection.
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


async def on_startup(app, url=None):
    setup_handlers(dispatcher)

    # Get current webhook status
    webhook = await bot.get_webhook_info()

    if url:
        # If URL is bad
        if webhook.url != url:
            # If URL doesnt match with by current remove webhook
            if not webhook.url:
                await bot.delete_webhook()

            await bot.set_webhook(url)
    elif webhook.url:
        # Otherwise remove webhook.
        await bot.delete_webhook()


def build_app(dispatcher):
    application = get_new_configured_app(dispatcher=dispatcher, path=WEBHOOK_URL_PATH)
    # set settings
    application.settings = settings

    application.on_startup.append(init_pg)
    application.on_shutdown.append(functools.partial(on_shutdown, url=WEBHOOK_URL))
    application.on_startup.append(functools.partial(on_startup, url=WEBHOOK_URL))
    application.on_cleanup.append(close_pg)

    return application


application = build_app(dispatcher)
web.run_app(application, host='0.0.0.0', port=os.environ['PORT'])
