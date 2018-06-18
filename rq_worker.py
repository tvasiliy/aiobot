import redis
import os
from rq import Queue, Worker, Connection
REDIS_URL = os.environ.get('REDISTOGO_URL')

listen = ['high', 'default', 'low']
conn = redis.from_url(REDIS_URL)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
