import ast
import inspect
from pathlib import Path
from typing import Any, Optional, get_type_hints
from loguru import logger as log

class TooManyStubs:
    verbose = True
    verbosest = True

    @staticmethod
    def _get_stub_path(cls: type[Any]) -> Path:
        """Return the .pyi path sitting next to cls’s .py file."""
        src = Path(inspect.getfile(cls))
        return src.with_suffix(".pyi")

    @staticmethod
    def _find_bounds(content: str, class_name: str) -> Optional[tuple[int,int]]:
        """
        Return (start, end) 0-based line indices for that class in content,
        or None if it isn’t there.
        """
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                # ast.lineno/end_lineno are 1-based
                start = node.lineno - 1
                end   = (node.end_lineno - 1) if hasattr(node, "end_lineno") \
                        else max(n.lineno for n in ast.walk(node)) - 1
                return start, end
        return None

    @staticmethod
    def update_class_stub(cls: type[Any], new_stub: str) -> None:
        """
        Replace or append the stub for `cls` in its .pyi file.
        """
        stub_file = TooManyStubs._get_stub_path(cls)

        header = "from typing import Any\n\n"
        if not stub_file.exists():
            log.warning(f"[Stubgen]: {stub_file} not found—writing fresh stub")
            stub_file.write_text(header + new_stub + "\n")
            return

        lines   = stub_file.read_text().splitlines()
        bounds  = TooManyStubs._find_bounds("\n".join(lines), cls.__name__)

        if bounds:
            start, end = bounds
            log.debug(f"[Stubgen]: Replacing {cls.__name__} lines {start}-{end}")
            new_lines = lines[:start] + new_stub.splitlines() + lines[end+1:]
        else:
            log.debug(f"[Stubgen]: Appending new stub for {cls.__name__}")
            new_lines = lines + [""] + new_stub.splitlines()

        stub_file.write_text("\n".join(new_lines) + "\n")

    import inspect
    from typing import Any, get_type_hints
    @staticmethod
    def generate_class_stub(cls: type) -> str:
        """
        Produce a PEP-compliant stub block for exactly the attributes
        declared on `cls`, with real signatures/annotations where possible,
        and fall back to the attribute’s runtime type for un-annotated data.
        """
        lines: list[str] = [f"class {cls.__name__}:"]
        members: list[str] = []
        hints = get_type_hints(cls, include_extras=False)
        log.warning(f"[AutoStub]: Generating stubs for {cls}")

        for name, attr in cls.__dict__.items():
            # ----- instance method -----
            if inspect.isfunction(attr):
                sig = inspect.signature(attr)
                try: fn_hints = get_type_hints(attr, include_extras=False)
                except: continue
                params = []
                for p in sig.parameters.values():
                    ann = fn_hints.get(p.name, Any)
                    ann_name = getattr(ann, "__name__", repr(ann))
                    if p.kind is p.VAR_POSITIONAL:
                        params.append(f"*{p.name}: {ann_name}")
                    elif p.kind is p.VAR_KEYWORD:
                        params.append(f"**{p.name}: {ann_name}")
                    else:
                        default = f" = {p.default!r}" if p.default is not p.empty else ""
                        params.append(f"{p.name}: {ann_name}{default}")
                ret = fn_hints.get("return", Any)
                ret_name = getattr(ret, "__name__", repr(ret))
                members.append(f"    def {name}({', '.join(params)}) -> {ret_name}: ...")

            # ----- staticmethod -----
            elif isinstance(attr, staticmethod):
                fn = attr.__func__
                sig = inspect.signature(fn)
                fn_hints = get_type_hints(fn, include_extras=False)
                params = []
                for p in sig.parameters.values():
                    ann = fn_hints.get(p.name, Any)
                    ann_name = getattr(ann, "__name__", repr(ann))
                    if p.kind is p.VAR_POSITIONAL:
                        params.append(f"*{p.name}: {ann_name}")
                    elif p.kind is p.VAR_KEYWORD:
                        params.append(f"**{p.name}: {ann_name}")
                    else:
                        default = f" = {p.default!r}" if p.default is not p.empty else ""
                        params.append(f"{p.name}: {ann_name}{default}")
                ret = fn_hints.get("return", Any)
                ret_name = getattr(ret, "__name__", repr(ret))
                members.append("    @staticmethod")
                members.append(f"    def {name}({', '.join(params)}) -> {ret_name}: ...")

            # ----- classmethod -----
            elif isinstance(attr, classmethod):
                fn = attr.__func__
                sig = inspect.signature(fn)
                fn_hints = get_type_hints(fn, include_extras=False)
                params = []
                for i, p in enumerate(sig.parameters.values()):
                    ann = fn_hints.get(p.name, Any)
                    ann_name = getattr(ann, "__name__", repr(ann))
                    # first param is 'cls'
                    if i == 0:
                        params.append(f"{p.name}: type[{cls.__name__}]")
                    else:
                        default = f" = {p.default!r}" if p.default is not p.empty else ""
                        params.append(f"{p.name}: {ann_name}{default}")
                ret = fn_hints.get("return", Any)
                ret_name = getattr(ret, "__name__", repr(ret))
                members.append("    @classmethod")
                members.append(f"    def {name}({', '.join(params)}) -> {ret_name}: ...")

            # ----- property -----
            elif isinstance(attr, property):
                fget = attr.fget
                fn_hints = get_type_hints(fget, include_extras=False) if fget else {}
                ret = fn_hints.get("return", Any)
                ret_name = getattr(ret, "__name__", repr(ret))
                members.append("    @property")
                members.append(f"    def {name}(self) -> {ret_name}: ...")

            # ----- everything else as data attribute -----
            else:
                # if there’s a type hint on the class, use it; otherwise fall back to runtime type
                ann = hints.get(name)
                if ann is not None:
                    ann_name = getattr(ann, "__name__", repr(ann))
                else:
                    ann_name = type(attr).__name__
                members.append(f"    {name}: {ann_name}")

        annotations = inspect.get_annotations(cls)
        for name in annotations:
            anno = annotations[str(name)]
            anno = anno.__name__
            members.append(f"    {name}: {anno}")

        # if cls.__dict__ was truly empty, still emit a pass
        if not members:
            lines.append("    pass")
        else:
            lines.extend(members)

        return "\n".join(lines)


    def auto_stub(cls: type) -> type:
        """
        Class decorator that (re)generates the .pyi stub for `cls`
        immediately after the class is defined.

        Usage:
            @auto_stub
            class Foo:
                ...
        """
        # 1. Build the stub text for this class
        stub_text = TooManyStubs.generate_class_stub(cls)

        # 2. Locate the stub-file next to cls’s .py source
        src = Path(inspect.getfile(cls))
        stub_file = src.with_suffix(".pyi")

        # 3. Write or update it
        TooManyStubs.update_class_stub(cls, stub_text)

        log.debug(f"[AutoStub]: Wrote stub for {cls.__name__} → {stub_file}")
        return cls

auto_stub = TooManyStubs.auto_stub

@auto_stub
class Foo:
    verbose=True
    foo: str
    bar: str
