from typing import Any

class Foo:
    __module__: str
    __firstlineno__: int
    __annotations__: dict
    verbose: bool
    __static_attributes__: tuple
    __dict__: getset_descriptor
    __weakref__: getset_descriptor
    __doc__: NoneType


def auto_stub(cls: type) -> type:
    return None
