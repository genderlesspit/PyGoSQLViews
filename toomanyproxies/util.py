import ast
import inspect
import sys
from pathlib import Path
from types import FrameType, SimpleNamespace
from typing import Any, Dict, Optional
from loguru import logger as log

def find_origin(item: str, frame: FrameType) -> SimpleNamespace | None:
    meta = {}
    try:
        val = get_runtime_value(item, frame)
        meta["val"] = val
        tp = type(val)
        meta["type"] = tp
        meta["type_module"] = tp.__module__
        meta["type_name"] = tp.__name__
        log.info(f"[TooManyProxies.Util]: {item!r} resolved → {val!r} (type={tp.__module__}.{tp.__name__})")
        return SimpleNamespace(
            dict=meta,
            **meta
        )
    except Exception as e:
        raise RuntimeWarning(e)
    finally:
        del frame

def get_runtime_value(name: str, frame: FrameType) -> Any:
    if name in frame.f_locals:
        return frame.f_locals[name]
    mod = sys.modules.get(frame.f_globals.get("__name__", ""))
    if mod and hasattr(mod, name):
        return getattr(mod, name)
    raise NameError(f"{name!r} not found")

def find_decl_locations(frame):
    module = inspect.getmodule(frame)
    src = inspect.getsource(module)
    tree = ast.parse(src)
    decls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    decls.append((target.id, node.lineno))
    return decls

def find_caller(frame: FrameType) -> Dict[str, Any] | None:
    """
    Given the current __getattr__ frame, return call‐site metadata.
    """
    meta: Dict[str, Any] = {}
    if frame is not None:
        try:
            caller = frame.f_back
            if caller is not None:
                #meta["name"] = item
                meta["file"] = caller.f_code.co_filename
                meta["line"] = caller.f_lineno
                meta["module"] = caller.f_globals.get("__name__", "<unknown>")
                log.debug(f"Call site → {meta}")
        finally:
            # avoid reference cycles
            del frame

    return meta

def get_runtime_value(name: str, frame: FrameType) -> Any:
    """
    Return the object bound to `name` in the closest namespace of `frame`:
    1) locals of the caller
    2) globals of the caller’s module
    Raises NameError if not found.
    """
    # 1) Check caller’s locals
    if name in frame.f_locals:
        return frame.f_locals[name]

    # 2) Fall back to caller’s module globals
    mod_name = frame.f_globals.get("__name__")
    if mod_name:
        module = sys.modules.get(mod_name)
        if module and hasattr(module, name):
            return getattr(module, name)

    raise NameError(f"Name {name!r} is not defined in locals or globals")

def get_last_assign_node(
    name: str,
    file: str,
    line: int
) -> Optional[ast.Assign]:
    """
    Parse the file at `filename`, and return the ast.Assign node
    for `name = ...` whose lineno is the largest one < before_line.
    """
    src = open(file, encoding="utf-8").read()
    tree = ast.parse(src, filename=file)
    best: Optional[ast.Assign] = None
    best_ln = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            # check all simple-name targets
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == name:
                    ln = node.lineno
                    if ln < line and ln > best_ln:
                        best_ln = ln
                        best = node

    return best

def assign_node_to_literal(node: ast.Assign, filename: str) -> Any:
    """
    Given an ast.Assign node and its source file, return:
     - the Python literal value of node.value (via ast.literal_eval), or
     - the exact source text for node.value (via ast.get_source_segment)
    """
    try:
        # literal_eval handles numbers, strings, tuples, lists, dicts, booleans, None
        return ast.literal_eval(node.value)
    except Exception:
        # fallback: grab the raw source for the RHS expression
        source = Path(filename).read_text(encoding="utf-8")
        return ast.get_source_segment(source, node.value)