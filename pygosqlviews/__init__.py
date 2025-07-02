from toomanyplugins import plugin

@plugin(PyGoSQL, cached_property)
def views(self):
    self: PyGoSQL
    return PyGoSQLViews(
        self,
        pygosql_dir= self._sql_root
    )