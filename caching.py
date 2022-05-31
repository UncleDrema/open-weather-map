from functools import cache
import time
from typing import Callable, Optional


# Собственный декоратор кеширования, использующий готовый декоратор
# Из модуля functools, но с функционалом времени жизни
def ttl_cache(ttl: Optional[int] = None):
    # Если время жизни не задано, используем стандартный декоратор @cache
    if ttl is None:
        def decorator(f: Callable):

            @cache
            def wrapper(*args, **kwargs):
                return f(*args, **kwargs)

            return wrapper
    else:
        # Иначе обманываем декоратор @cache
        # Передавая фиктивный параметр ttl_hash
        # Который отличается для интервалов в ttl секунд
        init_time = time.time()

        def decorator(f: Callable):
            @cache
            def real_call(ttl_hash, *args, **kwargs):
                return f(*args, **kwargs)

            def wrapper(*args, **kwargs):
                ttl_hash = round((init_time - time.time()) / ttl)
                return real_call(ttl_hash, *args, **kwargs)

            return wrapper

    return decorator
