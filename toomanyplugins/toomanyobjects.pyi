from typing import Any

class TypeConverter:
    __module__: str
    __firstlineno__: int
    __doc__: str
    verbose: bool
    @staticmethod
    def object_to_type(obj: Any) -> Type: ...
    @staticmethod
    def type_to_object(typ: Type, *args: Any, **kwargs: Any) -> Any: ...
    @staticmethod
    def absorb_attr(to_target: Union, from_source: Union, override: bool = False) -> Union: ...
    def class_to_dict(self: Type, target: Union) -> dict: ...
    def display_everything(self: Type, target: Union) -> NoneType: ...
    __static_attributes__: tuple
    __dict__: getset_descriptor
    __weakref__: getset_descriptor
