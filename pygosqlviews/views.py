from pathlib import Path
from functools import cached_property

from pygosql import PyGoSQL

from toomanyplugins import plugin

@plugin(PyGoSQL, cached_property)
def views(self: PyGoSQL) -> PyGoSQLViews:
    return PyGoSQLViews(self)
