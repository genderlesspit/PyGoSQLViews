import ast
import sys
from abc import ABC, abstractmethod, ABCMeta
from functools import singledispatchmethod, singledispatch
from pathlib import Path
from types import FrameType
from typing import List, Callable, Any, Type, Iterator, Tuple, Dict, Optional
from loguru import logger as log
from propcache import cached_property
import inspect

from abc import ABCMeta, ABC, abstractmethod
from typing import Type, Any, List
from loguru import logger as log
import inspect

class SmartProxyTypeFactory(ABCMeta):
    """
    A metaclass that:
     - Passes through normal class creation calls (name, bases, namespace)
     - Intercepts factory instantiation calls of the form Factory(target_cls, ...)
    """

    def __call__(cls, *args, **kwargs):
        # 1) If called with (name:str, bases:tuple, namespace:dict), this is class creation:
        if len(args) == 3 and isinstance(args[0], str):
            return super().__call__(*args, **kwargs)

        # 2) Otherwise it's Factory(target_cls, [custom_factory], **kwargs)
        target_cls = args[0]
        custom_factory = args[1] if len(args) > 1 else None
        instance = super().__call__()
        instance.target_cls = target_cls
        instance.custom_factory = custom_factory or cls
        instance.kwargs = kwargs
        instance.verbose = kwargs.get("verbose", False)

        if instance.verbose:
            log.success(f"[SmartProxyTypeFactory]: Initialized factory for target {target_cls.__name__}!")
        return instance


def _default_dict(self, item: Any) -> Any:
    if self.verbose: log.debug(f"{self}: Injecting dict {item} into {self.target_cls.__name__}")
    return self.target_cls(item)

def _default_path(self, item: Any) -> Any:
    if self.verbose: log.debug(f"{self}: Injecting Path {item} into {self.target_cls.__name__}")
    return self.target_cls(item)

def _default_list(self, item: Any) -> Any:
    if self.verbose: log.debug(f"{self}: Injecting list {item} into {self.target_cls.__name__}")
    return self.target_cls(item)

DEFAULT_CONVERSIONS: dict[str, Callable] = {
    "dict": _default_dict,
    "path": _default_path,
    "list": _default_list,
}

class Factory(ABC, metaclass=SmartProxyTypeFactory):
    """
    Base factory: subclasses *must* implement any of dict/path/list they care about.
    Missing ones get auto-injected from DEFAULT_CONVERSIONS.
    """
    target_cls: Type
    custom_factory: Type
    kwargs: dict
    verbose: bool = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # For each hook, if subclass didn't define it, inject default
        for name, default_fn in DEFAULT_CONVERSIONS.items():
            if name not in cls.__dict__:
                setattr(cls, name, default_fn)
                log.debug(f"[{cls.__name__}]: injected default '{name}'")

    def __repr__(self):
        return self.__class__.__name__

    @property
    def methods(self) -> List[Callable]:
        # … your non-recursive methods implementation from before …
        fns: List[Callable] = []
        for n, member in type(self).__dict__.items():
            if inspect.isfunction(member) and not n.startswith("_"):
                fns.append(member.__get__(self, type(self)))
        if self.verbose:
            log.debug(f"[{self}]: Methods available = {[fn.__name__ for fn in fns]}")
        return fns

    @singledispatchmethod
    def process(self, item: Any) -> Any:
        """
        Generic converter entry point.
        Returns None if no registered converter exists.
        """
        if self.verbose:
            log.warning(f"{self}: no converter registered for type {type(item)}")
        return None

    @process.register
    def _(self, item: dict) -> Any:
        """
        Dispatch dict to .dict()
        """
        if self.verbose:
            log.debug(f"{self}: dispatching dict item: {item!r}")
        return self.dict(item)

    @process.register
    def _(self, item: Path) -> Any:
        """
        Dispatch Path to .path()
        """
        if self.verbose:
            log.debug(f"{self}: dispatching path item: {item!s}")
        return self.path(item)

    @process.register
    def _(self, item: list) -> Any:
        """
        Dispatch list to .list()
        """
        if self.verbose:
            log.debug(f"{self}: dispatching list item of length: {len(item)}")
        return self.list(item)

    @abstractmethod
    def dict(self, item: Any) -> Any:
        """Convert to dict or return None."""
        ...

    @abstractmethod
    def path(self, item: Any) -> Any:
        """Convert to Path or return None."""
        ...

    @abstractmethod
    def list(self, item: Any) -> Any:
        """Convert to list or return None."""
        ...

class Default(Factory):
    verbose=True

class DummyFactory(Factory):
    def dict(self, item):
        log.debug(f"Hit dispatcher!")
        return self.target_cls(item)

class DummyClass:
    def __init__(self, dict):
        self.dict = dict

    def __repr__(self):
        return "DummyClass"

def debug():
    dict = {"foo": "bar"}
    path = Path.cwd()
    test = DummyFactory(DummyClass, verbose=True)
    cls = test.process(dict)
    log.debug(cls.__dict__)
    cls = test.process(path)
    log.debug(cls.__dict__)

if __name__ == "__main__":
    debug()