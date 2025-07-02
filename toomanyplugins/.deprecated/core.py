import inspect
import re
from pathlib import Path
from tkinter.font import names
from typing import Callable, List, cast

from loguru import logger as log
from functools import cached_property

#from toomanyplugins.plugin import plugin


class Test:
    instance = None
    foo = "bar"

if __name__ == "__main__":
    @plugin(Test, cached_property)
    def new_method(self):
        return "Hello!"

    l = Test().new_method
    log.debug(l)
    log.debug(Test.__dict__)

def parse_existing_stubs(content: str) -> dict:
    """Parse existing stub file to find class boundaries."""
    classes = {}

    # Find all class definitions with their start/end positions
    class_pattern = r'^class\s+(\w+).*?:'

    lines = content.split('\n')
    current_class = None
    current_start = 0

    for i, line in enumerate(lines):
        if re.match(class_pattern, line):
            # End previous class if exists
            if current_class:
                classes[current_class] = (current_start, i - 1)

            # Start new class
            match = re.match(class_pattern, line)
            current_class = match.group(1)
            current_start = i

    # End last class
    if current_class:
        classes[current_class] = (current_start, len(lines) - 1)

    return classes

def update_stub_file(class_name: str, new_stub: str, output_file: Path):
    """Smart stub file updating."""

    if not output_file.exists():
        log.warning(f"[TooManyPlugins]: No file found at {output_file}, attempting to generate...")
        with open(output_file, 'w') as f:
            f.write("from typing import Any, NoneType\n\n" + new_stub + "\n")
        return

    # Read existing content
    with open(output_file, 'r') as f:
        content = f.read()

    lines = content.split('\n')

    # Find existing class locations
    classes = parse_existing_stubs(content)

    if class_name in classes:
        # Replace existing class
        start, end = classes[class_name]
        new_lines = lines[:start] + new_stub.split('\n') + lines[end + 1:]
    else:
        # Add new class at end
        new_lines = lines + [''] + new_stub.split('\n')

    # Write back
    with open(output_file, 'w') as f:
        f.write('\n'.join(new_lines))

def generate_class_stub(cls) -> str:
    """Generate stub content for a class."""
    lines = [f"class {cls.__name__}:"]

    # Collect all attributes
    all_attrs = {}
    for base in cls.__mro__:
        for key, value in base.__dict__.items():
            all_attrs[key] = value

    # Add to stub
    for key, value in all_attrs.items():
        if callable(value):
            lines.append(f"    def {key}(self, *args, **kwargs) -> Any: ...")
        else:
            lines.append(f"    {key}: {type(value).__name__}")

    if len(lines) == 1:
        lines.append("    pass")

    return '\n'.join(lines)

def stubgen(_cls=None, *, path: Path = None):
    from toomanyproxies import find_caller
    caller = find_caller(inspect.currentframe().f_back)
    def decorator(cls):
        # Generate stub
        stub_content = generate_class_stub(cls)
        caller_path = Path(caller["file"])
        root = caller_path.parent
        name = caller_path.stem
        full_path = root / f"{name}.pyi"

        output_file = full_path if path is None else path

        # Update file (replace if exists)
        update_stub_file(cls.__name__, stub_content, output_file)

        log.debug(f"[TooManyPlugins]: Updated stub for {cls.__name__}")
        return cls

    if _cls is not None:
        return decorator(_cls)
    return decorator

def combine(cls2: object, new_type: bool = False):
    """Decorator to add proxy behavior to existing class."""
    def decorator(cls1: object, cls2 = cls2, new_type=new_type):
        return combine_classes(cls1, cls2, new_type)
    return decorator

def combine_classes(cls1: object, cls2: object, new_type = False):
    combined_dict = {}
    for cls in [cls1, cls2]:
        log.debug(f"[TooManyPlugins]: Inspecting {cls}:"
                  f" __dict__={cls.__dict__.items()}")
        for key, value in cls.__dict__.items():
            if not key.startswith('__') or key in ['__annotations__', '__doc__']:
                combined_dict[key] = value

    combined_anno = {}
    for cls in [cls1, cls2]:
        if hasattr(cls, '__annotations__'):
            combined_anno.update(cls.__annotations__)

    if combined_anno: combined_dict['__annotations__'] = combined_anno

    # Create new class with combined behavior
    class_name = cls1.__name__ + cls2.__name__ if new_type else cls1.__name__

    tp = type(
        class_name,
        (cls1, cls2),  # type: ignore
        combined_dict
    )

    # Add module info for better IDE recognition
    tp.__module__ = cls1.__module__
    tp.__qualname__ = class_name

    log.debug(f"[TooManyPlugins]: Reading newtype {tp}: {tp.__dict__}")
    tp = stubgen(tp)

    return tp  # Simple and clear

def combine_into_instance(target_obj, source_obj):
    """Combine attributes into existing instance."""

    # Copy attributes from source object
    for key, value in source_obj.__dict__.items():
        if not key.startswith('_'):
            setattr(target_obj, key, value)

    # Copy class attributes from source class
    source_class = source_obj.__class__
    for key, value in source_class.__dict__.items():
        if not key.startswith('_') and not hasattr(target_obj, key):
            setattr(target_obj, key, value)

    return target_obj

import re
import ast

class Test:
    instance = None
    foo = "bar"

if __name__ == "__main__":
    @combine(Test)
    class Test2:
        foo2 = "bar2"

    @combine(Test)
    class Test3:
        foo2 = "dunder"

    log.debug(f"{Test2}: {Test2}")
    log.debug(f"test2={Test2.__dict__}")
    log.debug(f"test3={Test3.__dict__}")