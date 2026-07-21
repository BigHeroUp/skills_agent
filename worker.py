"""RQ worker entrypoint for durable Skills Agent analysis jobs."""

import os

from redis import Redis
from rq import Worker


if __name__ == "__main__":
    redis_connection = Redis.from_url(os.environ["REDIS_URL"])
    Worker(["analyses"], connection=redis_connection).work(with_scheduler=True)
