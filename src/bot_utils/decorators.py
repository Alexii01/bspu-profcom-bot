import logging
import functools


def __debug_wrapper(
    func, logger, begin: str | None = None, end: str | None = None, *args, **kwargs
):
    logger.debug(f"{func.__name__} called" if begin is None else begin)
    result = func(*args, **kwargs)
    logger.debug(f"{func.__name__} finished" if end is None else end)
    return result


def __passthrough_debug_wrapper(
    func, logger, begin: str | None = None, end: str | None = None, *args, **kwargs
):
    logger.debug(f"{func.__name__} called" if begin is None else begin)
    result = func(logger, *args, **kwargs)
    logger.debug(f"{func.__name__} finished" if end is None else end)
    return result


def __conditional_log_wrapper(
    func,
    logger: logging.Logger,
    if_true: str | None,
    if_false: str | None,
    *args,
    **kwargs,
):
    result = func(*args, **kwargs)
    if if_true is not None and result is True:
        logger.debug(if_true)
    if if_false is not None and result is False:
        logger.debug(if_false)
    return result


def define_log(
    logger: logging.Logger | None = None,
    begin: str | None = None,
    end: str | None = None,
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return __debug_wrapper(func, logger, begin, end, *args, **kwargs)

        return wrapper

    return decorator


def delegate_logging(
    func,
):
    @functools.wraps(func)
    def logger_catcher(
        logger, begin: str | None = None, end: str | None = None, *args, **kwargs
    ):
        return __debug_wrapper(func, logger, begin, end, *args, **kwargs)

    return logger_catcher


def passthrough_log(
    logger: logging.Logger | None = None,
    begin: str | None = None,
    end: str | None = None,
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return __passthrough_debug_wrapper(
                func, logger, begin, end, *args, **kwargs
            )

        return wrapper

    return decorator


def conditional_log(if_true: str, if_false: str, logger: logging.Logger | None = None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return __conditional_log_wrapper(
                func, logger, if_true, if_false, *args, **kwargs
            )

        return wrapper

    return decorator
