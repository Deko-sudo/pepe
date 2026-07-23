import os
import sys

import redis


def check_worker_health() -> bool:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        r = redis.from_url(redis_url, socket_connect_timeout=2)
        r.ping()
        r.close()
    except Exception:
        return False

    return os.path.exists("/proc/1/status")


if __name__ == "__main__":
    sys.exit(0 if check_worker_health() else 1)
