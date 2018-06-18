import os
import timezonefinder
import datetime
import pytz


def get_by_location(longitude, latitude):
    tz = timezonefinder.TimezoneFinder()
    return tz.certain_timezone_at(lng=longitude, lat=latitude)


def get_default():
    return os.environ.get('TIMEZONE_DEFAULT', default='Europe/Moscow')


def convert_to_utc(t_date: datetime.datetime, tmz=get_default()):
    timezone = pytz.timezone(tmz)
    result_date = timezone.localize(t_date)
    result_date = result_date.astimezone(tz=pytz.utc)
    result_date = result_date.replace(tzinfo=None)
    return result_date


def convert_from_utc(t_date: datetime.datetime, tmz=get_default()):
    timezone = pytz.timezone('UTC')
    user_tmz = pytz.timezone(tmz)
    result_date = timezone.localize(t_date)
    result_date = result_date.astimezone(tz=user_tmz)
    result_date = result_date.replace(tzinfo=None)
    return result_date

