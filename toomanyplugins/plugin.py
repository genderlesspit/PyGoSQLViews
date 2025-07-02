import inspect
import re
from pathlib import Path
from tkinter.font import names
from typing import Callable, List, cast


from loguru import logger as log
from functools import cached_property

def plugin(target_class, decorators=None, override: bool = False, verbose: bool = True):
    name = "[TooManyPlugins]"
    if verbose: log.debug(f"{name}: Attempting to add plugin...\n - target_class={target_class}\n - decorators={decorators}\n - override={override}")

    def decorator(func):
        # Apply decorators to the function
        enhanced_func = func
        if decorators:
            if callable(decorators):  # Single decorator
                enhanced_func = decorators(func)
            else:  # List of decorators
                for dec in decorators:
                    enhanced_func = dec(enhanced_func)

        # Check if function already exists
        if hasattr(target_class, func.__name__) and not override:
            log.warning(f"[{name}] {func.__name__} already exists, skipping")
            return getattr(target_class, func.__name__)

        # Add to class
        setattr(target_class, func.__name__, enhanced_func)

        # IMPORTANT: Call __set_name__ for descriptors that need it
        if hasattr(enhanced_func, '__set_name__'):
            enhanced_func.__set_name__(target_class, func.__name__)

        if verbose: log.debug(f"[{name}] Successfully added {func.__name__} to {target_class}!")
        return enhanced_func

    return decorator