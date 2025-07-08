import asyncio
import inspect
from pathlib import Path
from tabnanny import verbose
from types import FrameType, SimpleNamespace
from typing import Any, Type, Callable, List

from async_property import AwaitLoader
from loguru import logger as log
from propcache import cached_property

from toomanyplugins import TypeConverter, auto_stub, plugin, excruciating_logger
from toomanyplugins import combine
from toomanyproxies.factory import Factory, Default
from toomanyproxies.util import get_runtime_value, find_origin

@auto_stub
class Proxies:
    pass

class Proxying:
    verbose: bool = False
    _proxied_class: Type
    _cached_proxies: dict[str, Callable]
    _factory: Factory = None
    _whitelist: List[str] = ["verbose", "log"]
    _whitelisted_prefixes: tuple[str | str] = ["_", "__"]

@combine(Proxying)
class Proxy:
    verbose: bool = True
    _factory: Factory | Any
    _proxyer: Type
    _proxied: Type

    def __name__(self):
        return "Proxy"

    def __init__(self, proxyer, proxied, verbose: bool = True):
        if proxyer.__name__ not in Proxies.__dict__:
            log.warning(f"Attempted to call {proxyer.__name__} from {Proxies}, but it doesn't exist yet!")
            setattr(Proxies, proxyer.__name__, self)
            log.success(f"Successfully enabled proxying for {proxyer}")

        self._proxyer = proxyer
        self._proxied = proxied
        self.verbose = verbose

        self._whitelist_container(self.__dict__, self._proxyer.__dict__, self._proxied.__dict__)
        if self.verbose: log.debug(f"{self}: Currently operating with whitelisted settings:\n - prefixes={self._whitelisted_prefixes}\n - fullstrs={self._whitelist}")

        class DefaultFactory(Factory):
            verbose = True
            target_cls = self._proxied

        self._factory = DefaultFactory

        #time to infect the host...
        asyncio.run(TypeConverter.absorb_attr(Proxy, Proxies))
        asyncio.run(TypeConverter.absorb_attr(self._proxyer, self))
        combine(self._proxyer, self)
        self._proxyer.__getattribute__ = self.__proxied_getattr__
        log.success(f"{self}: {proxyer} now has the ability to proxy {proxied} based on {proxyer._factory}!")

    def __proxied_getattr__(self, item: Any):
        if self.verbose: log.debug(f"{self}: Attempting to retrieve {item}")

        # if item == self._proxyer.__name__:
        #     setattr(Proxy, self._proxyer.__name__, self._proxyer)
        #     return self._proxyer

        if not isinstance(item, str):
            log.warning(f"{self}: Attempting to get an attr... that's not a str?")
            try: return getattr(self._proxyer, item)
            except Exception as e:
                RuntimeWarning(f"{self}: {e}")
                try:
                    return getattr(self._proxied, item)
                except Exception as e:
                    RuntimeWarning(f"{self}: {e}")
                    return ""

        else:
            item: str
            if item not in self._whitelist and not item.startswith("_"):
                if self.verbose:
                    log.warning(f"{self}: {item} is not in the whitelist... Attempting to initialize as {self._proxied}\ncurrent_whitelist: {self._whitelist}")
                frame = inspect.currentframe().f_back
                meta = find_origin(item, frame)
                log.debug(meta.val)
                meta.val = {}
                obj = self._factory.process(self._factory, meta.val)
                if item is not None:
                    setattr(self, item, obj)
                    if self.verbose: log.success(f"Successfully generated missing item, {item} as {obj}")
                return item

    def _whitelist_container(self, *objects):
        """Add all dict/list attribute names from objects."""
        if self.verbose: log.debug(f"{self}: Attempting to whitelist {objects}")
        visited = set()

        def scan(obj):
            if id(obj) in visited: return
            visited.add(id(obj))

            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, (dict, list)): self._whitelist.append(k)
                    scan(v)
            elif isinstance(obj, list):
                for item in obj: scan(item)
            elif hasattr(obj, '__dict__'):
                for k, v in obj.__dict__.items():
                    if isinstance(v, (dict, list)): self._whitelist.append(k)
                    scan(v)

        for obj in objects: scan(obj)

        if self.verbose: log.success(f"{self}: Successfully updated whitelist: {self._whitelist}!")

class Dummy:
    foo = "bar"
    pass

class Dummy2:
    def __init__(self, item):
        self.item = item

Proxy(Dummy, Dummy2)
bar = "foo"
Dummy.bar
# log.debug(Dummy.bar)

#ten = ["ten"]
#log.debug(ProxyManager.ten)

#log.debug(Proxy.__dict__)

# class ProxyingClass(ProxyParent):
#     def __init_subclass__(cls, **kwargs):
#         for attr in ProxyingClass.__dict__:
#             try: setattr(cls, attr, getattr(ProxyingClass, attr))
#             except Exception: continue

#         for k in kwargs:
#             setattr(cls, k, kwargs.get(k))

# log.debug(f"dummy={DummyClass.__dict__}")
# log.debug(f"proxying={ProxyingClass.__dict__}")
# #log.debug(ProxyingClass().__dict__)
# path = Path.cwd()

# class SmartProxy(type):
#     _target_class: Type          # What class are we hijacking?
#     _smart_proxy_dunders: List[Callable]
#     _target_dunders: List[Callable]
#     _class_objects: List[object] # Track created objects
#     _whitelist: List[str]        # Allowed attribute names
#     _whitelist_prefixes: List[str] # Allowed prefixes (_private, etc)
#     _factories: List[Callable]
#     _is_async: bool