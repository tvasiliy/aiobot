from aiogram.types import Message, CallbackQuery, Update
from aiogram.contrib.middlewares.context import ContextMiddleware
from aiogram.dispatcher import CancelHandler
from core.models import get_user
import datetime
import core.utils.timezone as utils_timezone
import gettext
_ = gettext.gettext


class PrepareMiddleware(ContextMiddleware):
    def __init__(self):
        super(PrepareMiddleware, self).__init__()

    async def set_user(self, from_user):
        user = await get_user(from_user)

        if user is not None:
            self.__setitem__('user_id', user.id)
            self.__setitem__('user_timezone', user.timezone)
            self.__setitem__('request_timezone', False)
            if self.get('user_timezone') is None or self.get('user_timezone') is '':
                self.__setitem__('request_timezone', True)
                self.__setitem__('user_timezone', utils_timezone.get_default())
            timezone = self.get('user_timezone')
            self.__setitem__('user_time', utils_timezone.convert_from_utc(datetime.datetime.now(),timezone))
        return user

    async def on_process_message(self, message: Message):
        user = await self.set_user(message.from_user)
        if user is None:
            await message.reply(_('Извините, бот временно недоступен'))

            raise CancelHandler()

    async def on_process_callback_query(self, query: CallbackQuery):
        await self.set_user(query.from_user)
