import logging
import functools


def __log_wrapper(
    func,
    logger: logging.Logger,
    level: int,
    begin: str | None = None,
    end: str | None = None,
    *args,
    **kwargs,
):
    logger.log(level=level, msg=f"{func.__name__} called" if begin is None else begin)
    result = func(*args, **kwargs)
    logger.log(level=level, msg=f"{func.__name__} finished" if end is None else end)
    return result


def __one_log(
    func,
    logger: logging.Logger,
    level: int,
    msg: str | None = None,
    *args,
    **kwargs,
):
    logger.log(level=level, msg=f"{func.__name__} called" if msg is None else msg)
    return func(*args, **kwargs)


def __passthrough_log_wrapper(
    func,
    logger: logging.Logger,
    level: int,
    begin: str | None = None,
    end: str | None = None,
    *args,
    **kwargs,
):
    logger.log(level=level, msg=f"{func.__name__} called" if begin is None else begin)
    result = func(logger, *args, **kwargs)
    logger.log(level=level, msg=f"{func.__name__} finished" if end is None else end)
    return result


def __conditional_log_wrapper(
    func,
    logger: logging.Logger,
    level: int,
    if_true: str | None,
    if_false: str | None,
    *args,
    **kwargs,
):
    result = func(*args, **kwargs)
    if if_true is not None and result is True:
        logger.log(level=level, msg=if_true)
    if if_false is not None and result is False:
        logger.log(level=level, msg=if_false)
    return result


def define_log(
    logger: logging.Logger,
    level: int,
    begin: str | None = None,
    end: str | None = None,
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return __log_wrapper(func, logger, level, begin, end, *args, **kwargs)

        return wrapper

    return decorator


def define_one_log(
    logger: logging.Logger,
    level: int,
    msg: str | None = None,
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return __one_log(func, logger, level, msg, *args, **kwargs)

        return wrapper


def delegate_logging(
    func,
):
    @functools.wraps(func)
    def logger_catcher(
        logger: logging.Logger,
        level: int,
        begin: str | None = None,
        end: str | None = None,
        *args,
        **kwargs,
    ):
        return __log_wrapper(func, logger, level, begin, end, *args, **kwargs)

    return logger_catcher


def passthrough_log(
    logger: logging.Logger,
    level: int,
    begin: str | None = None,
    end: str | None = None,
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return __passthrough_log_wrapper(
                func, logger, level, begin, end, *args, **kwargs
            )

        return wrapper

    return decorator


def conditional_log(logger: logging.Logger, level: int, if_true: str, if_false: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return __conditional_log_wrapper(
                func, logger, level, if_true, if_false, *args, **kwargs
            )

        return wrapper

    return decorator


def log_error_and_reraise(logger: logging.Logger):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{type(e).__name__:} {e}")
                raise e

        return wrapper

    return decorator
