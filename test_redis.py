import redis
import sys

def test_redis():
    try:
        r = redis.from_url('redis://localhost:6379/0')
        r.ping()
        print("Redis is RUNNING.")
    except Exception as e:
        print(f"Redis is NOT running: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_redis()
