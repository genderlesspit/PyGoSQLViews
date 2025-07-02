import asyncio
from typing import Type, Any
from loguru import logger as log

from toomanyplugins.excruciating_logger import annoying_class
from toomanyplugins.toomanystubs import auto_stub

@auto_stub
class TypeConverter:
    """
    Utility for converting between objects and their types,
    and for absorbing one type’s members into another.
    """
    verbose = True

    @staticmethod
    async def object_to_type(obj: Any) -> Type[Any]:
        """
        Convert an object to its class (type).

        Args:
            obj: any Python object

        Returns:
            The class of the given object.
        """
        typ = obj.__class__
        if obj.verbose or TypeConverter.verbose:
            log.debug(f"[{TypeConverter}]: Object {obj!r} is of type {typ!r}")
        return typ

    @staticmethod
    async def type_to_object(typ: Type[Any],
                             *args: Any,
                             **kwargs: Any
                             ) -> Any:
        """
        Instantiate a new object from a type, passing through any constructor arguments.

        Args:
            typ: the class to instantiate
            *args: positional args for the constructor
            **kwargs: keyword args for the constructor

        Returns:
            A new instance of `typ`.

        Raises:
            Exception: any exception raised by the constructor is propagated.
        """
        try:
            instance = typ(*args, **kwargs)
            if typ.verbose or TypeConverter.verbose:
                log.debug(f"[{TypeConverter}]: Created instance {instance!r} of type {typ!r}")
            return instance
        except Exception as e:
            if typ.verbose or TypeConverter.verbose:
                log.error(f"[{TypeConverter}]: Failed to instantiate {typ!r} with args={args}, kwargs={kwargs}: {e}")
            raise

    @staticmethod
    async def absorb_attr(
        to_target: Type[Any] | object,
        from_source: Type[Any] | object,
        *,
        override: bool = False
    ) -> Type[Any] | object:
        """
        Inject all non-special attributes and annotations from `from_source` into `to_target`,
        and return `to_target` in its original form (class or instance).

        Args:
            to_target: class or instance to be modified
            from_source: class or instance whose members will be copied
            override: if True, replace existing attrs on target; else skip them

        Returns:
            The original `to_target` value (so you keep its original type).
        """
        # Normalize to classes:
        if isinstance(to_target, object):
            tgt_cls = to_target
        else:
            tgt_cls = await TypeConverter.object_to_type(to_target)

        if isinstance(from_source, object):
            src_cls = from_source
        else:
            src_cls = await TypeConverter.object_to_type(from_source)

        if TypeConverter.verbose:
            log.debug(f"[{TypeConverter}]: Absorbing from {src_cls.__name__} into {tgt_cls.__name__}")

        # 1. Copy attributes
        for name, value in src_cls.__dict__.items():
            if name.startswith("__") and name not in ("__annotations__", "__doc__"):
                continue
            if not override and hasattr(tgt_cls, name):
                if TypeConverter.verbose:
                    log.debug(f"[{TypeConverter}]: Skipping existing '{name}' on {tgt_cls.__name__}")
                continue
            setattr(tgt_cls, name, value)
            if TypeConverter.verbose:
                log.debug(f"[{TypeConverter}]: Injected '{name}' from {src_cls.__name__}")

        # 2. Merge annotations
        src_ann = getattr(src_cls, "__annotations__", {})
        if src_ann:
            tgt_ann = getattr(tgt_cls, "__annotations__", {}) or {}
            merged = {**tgt_ann, **src_ann}
            setattr(tgt_cls, "__annotations__", merged)
            if TypeConverter.verbose:
                log.debug(f"[{TypeConverter}]: Merged annotations into {tgt_cls.__name__}")

        if TypeConverter.verbose:
            log.debug(f"[{TypeConverter}]: Completed absorbing {src_cls.__name__} into {tgt_cls.__name__}")

        # Return the original target (so you get back a class if you passed one,
        # or the same instance if you passed an object)
        return to_target

    async def class_to_dict(
        self: Type[Any],
        target: Type[Any] | object
    ) -> dict[str, Any]:
        """
        Convert a class (or instance) into a dict of its metadata.

        Args:
            target: the class or instance to inspect

        Returns:
            A dict with keys:
              - name: class name
              - module: module path
              - bases: list of base class names
              - mro: list of MRO class names
              - annotations: own __annotations__ dict
              - attributes: mapping of own attrs → repr(value)
        """
        # Normalize to class
        if isinstance(target, type):
            typ = target
        else:
            typ = await self.object_to_type(target)

        result: dict[str, Any] = {
            "name": typ.__name__,
            "module": typ.__module__,
            "bases": [b.__name__ for b in typ.__bases__],
            "mro":   [m.__name__ for m in typ.__mro__],
            "annotations": dict(getattr(typ, "__annotations__", {})),
            "attributes": {
                name: repr(val)
                for name, val in typ.__dict__.items()
                if not name.startswith("__")
            }
        }

        if self.verbose:
            log.debug(f"[{self}]: Converted {typ.__name__} to dict → {result}")

        return result

    async def display_everything(
        self: Type[Any],
        target: Type[Any] | object
    ) -> None:
        """
        Log all metadata for a class or instance:
         - Name, module, bases & MRO
         - __annotations__
         - Every entry in __dict__
        """
        # normalize to a class
        typ = target if isinstance(target, type) else await self.object_to_type(target)

        if self.verbose or TypeConverter.verbose:
            log.info(f"[{self}]: Displaying info for {typ.__name__} (module={typ.__module__})")
            log.debug(f"[{self}]: Bases = {typ.__bases__}")
            log.debug(f"[{self}]: MRO   = {typ.__mro__}")

            anns = getattr(typ, "__annotations__", {})
            log.debug(f"[{self}]: __annotations__ = {anns!r}")

            for name, val in typ.__dict__.items():
                log.debug(f"[{self}]: {name!r} → {val!r}")

class A:
    verbose = True
    def foo(self):
        return "foo from A"

class B:
    bar: int

    def bar(self):
        return "bar from B"

async def main():
    conv = TypeConverter

    # Before absorbing:
    print(hasattr(A, "bar"))  # → False

    # Absorb B into A, without overwriting A.foo
    await conv.absorb_attr(A, B, override=False)

    # Now A has B’s members:
    a = A()
    print(a.foo())            # → "foo from A"
    print(a.bar())            # → "bar from B"
    print(A.__annotations__)  # → {'bar': <class 'int'>}
    await TypeConverter.display_everything(A, A)

if __name__ == "__main__":
    asyncio.run(main())