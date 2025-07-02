import sys
import linecache
import inspect
import functools
from loguru import logger as log

def excruciating_logger(func, toggle=True, force_verbosity=False):
    """
    Decorator that logs every executed line within a method if self.verbose is True.
    Supports both async and sync methods.
    """
    is_coro = inspect.iscoroutinefunction(func)
    if not toggle: return

    @functools.wraps(func)
    async def async_wrapper(self, *args, **kwargs):
        if not force_verbosity:
            if not getattr(self, "verbose", True):
                return await func(self, *args, **kwargs)

        code_obj = func.__code__
        self_ref = self

        def tracer(frame, event, arg):
            if event == "line" and frame.f_code is code_obj:
                lineno = frame.f_lineno
                line = linecache.getline(code_obj.co_filename, lineno).strip()
                log.debug(f"[{self_ref}]: {func.__name__}:{lineno} – {line}")
            return tracer

        sys.settrace(tracer)
        try:
            return await func(self, *args, **kwargs)
        finally:
            sys.settrace(None)

    @functools.wraps(func)
    def sync_wrapper(self, *args, **kwargs):
        if not force_verbosity:
            if not getattr(self, "verbose", True):
                return func(self, *args, **kwargs)

        code_obj = func.__code__
        self_ref = self

        def tracer(frame, event, arg):
            if event == "line" and frame.f_code is code_obj:
                lineno = frame.f_lineno
                line = linecache.getline(code_obj.co_filename, lineno).strip()
                try:
                    log.debug(f"[{self_ref}]: {func.__name__}:{lineno} – {line}")
                except: return
            return tracer

        sys.settrace(tracer)
        try:
            return func(self, *args, **kwargs)
        finally:
            sys.settrace(None)

    return async_wrapper if is_coro else sync_wrapper

def annoying_class(cls):
    """
    Class decorator that applies excruciating_logger to every method in the class.
    """
    for name, attr in vars(cls).items():
        # static methods
        if isinstance(attr, staticmethod):
            fn = attr.__func__
            decorated = staticmethod(excruciating_logger(fn))
            setattr(cls, name, decorated)

        # class methods
        elif isinstance(attr, classmethod):
            fn = attr.__func__
            decorated = classmethod(excruciating_logger(fn))
            setattr(cls, name, decorated)

        # regular functions (sync or async)
        elif inspect.isfunction(attr):
            setattr(cls, name, excruciating_logger(attr))

    return cls