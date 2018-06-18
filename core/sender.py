from rq_scheduler import Scheduler
from rq_worker import conn
import logging
import pytz
from .utils.timezone import get_default
from .telegram.from_bot import main

scheduler = Scheduler(connection=conn)


def set_notification_job(chat_id, notify_id, notify_datetime, user_timezone):
    # Add job to queue
    logging.info('New sending task by notify = %s and date = %s', notify_id, notify_datetime)

    if user_timezone is None or user_timezone is '':
        user_timezone = get_default()

    try:
        timezone = pytz.timezone(user_timezone)
    except pytz.UnknownTimeZoneError:
        timezone = pytz.timezone(get_default())
        pass

    run_date = timezone.localize(notify_datetime)
    run_date = run_date.astimezone(tz=pytz.utc)
    run_date = run_date.replace(tzinfo=None)

    logging.info('Run enqueue_in by date %s', run_date)
    result = scheduler.enqueue_at(run_date, main, notify_id=notify_id, chat_id=chat_id)
    logging.info('Set enqueue_at result= %s', result)
    return True


def count_jobs():
    return scheduler.count()


def cancel_jobs():
    list_of_job_instances = scheduler.get_jobs()
    if len(list_of_job_instances) > 0:
        for job in list_of_job_instances:
            scheduler.cancel(job)
