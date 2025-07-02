from pathlib import Path

import jinja2
from loguru import logger as log
from toomanyproxies.proxy import Proxy

class TemplateManager:
    pass
    # """
    # Standalone Jinja2 template manager utility.
    #
    # Supports multiple named meta environments and a cache of environments per directory.
    # """
    # _instance: 'TemplateManager' = None
    # _whitelisted_attr: []
    #
    # def __new__(cls):
    #     if cls._instance is None:
    #         cls._instance = super().__new__(cls)
    #     return cls._instance
    #
    # def __init__(self, verbose: bool = False) -> None:
    #     """
    #     Initialize TemplateManager singleton.
    #
    #     Args:
    #         verbose: Enable info logging when True.
    #     """
    #     self.verbose = verbose
    #
    # def __getattr__(self, item: str):
    #     """
    #     Auto-create Jinja2 Environment for filesystem paths.
    #     Only called when normal attribute access fails.
    #     """
    #     # Handle whitelisted_attr safely
    #     whitelisted = getattr(self, 'whitelisted_attr', set())
    #
    #     if item.startswith("_") or item in whitelisted:
    #         raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")
    #
    #     try:
    #         path = Path(item)
    #     except Exception:
    #         raise AttributeError(f"'{item}' is not a valid path")
    #
    #     if not path.exists():
    #         raise AttributeError(f"Path '{path}' does not exist")
    #
    #     obj = Env(path)
    #
    #     # Fix: Cache using the requested name, not obj.name
    #     setattr(self, item, obj)
    #
    #     # Fix: Actually return the object
    #     return obj

class Env:
    def __init__(self, path: Path):
        self.path = path
        self.name = path.name


Proxy(TemplateManager, Env)

log.debug(TemplateManager.__dict__)
