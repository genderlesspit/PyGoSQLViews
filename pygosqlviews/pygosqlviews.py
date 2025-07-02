"""
PyGoSQLViews - HTML admin interface for PyGoSQL APIs
Simple card/detail navigation: database → table → row
"""
import json
import asyncio
import shutil
import sqlite3
import time
from functools import cached_property
from json import JSONDecodeError
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

import async_property
import jinja2
from async_property import AwaitLoader, async_cached_property
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Template
from pygosql import PyGoSQL
from loguru import logger as log
from toomanyplugins import plugin

from pygosql import PyGoSQL

@plugin(PyGoSQL, cached_property)
def views(self):
    """Add views property to PyGoSQL instances"""
    self: PyGoSQL
    return PyGoSQLViews(self, cwd=self._sql_root, verbose=self._verbose)

class PyGoSQLViews(AwaitLoader):
    def __init__(self, pygosql: PyGoSQL, cwd: Path, verbose:bool = True):
        self.pygosql = pygosql
        self.cwd = cwd
        self.verbose = verbose
        _ = self.dir
        _ = self.tables
        if self.verbose: log.success(f"[{self}]: Successfully initialized!")

    def __repr__(self):
        return "PyGoSQL.Views"

    @cached_property
    def dir(self):
        return Directories(self)

    @cached_property
    def template_manager(self):
        return TemplateManager(self)

    @cached_property
    def tables(self) -> SimpleNamespace:
        tables = {}
        if self.verbose: log.debug(f"{self}: Attempting to construct table classes...")
        for table in self.pygosql.table_dirs:
            table = Path(table)
            tables[table.name] = Table(self, table)
        ns = SimpleNamespace(
            list=self.pygosql.table_dirs,
            **tables
        )
        if self.verbose: log.success(f"{self}: Constructed namespace!\n{ns}")
        return ns

    @async_cached_property
    async def database(self):
        return await self.pygosql.database

class Directories:
    """Manages directory structure and file creation for PyGoSQLViews"""

    def __init__(self, pygosqlviews: PyGoSQLViews):
        self.pygosqlviews = pygosqlviews
        self.pygosql = pygosqlviews.pygosql
        self.dir = self.pygosqlviews.cwd
        self.verbose = self.pygosqlviews.verbose
        self.src = Path(__file__).parent / "default"
        _ = self.paths
        if self.verbose: log.success(f"{self}: Successfully Initialized!")

    def __repr__(self):
        return "PyGoSQL.Views.Directories"

    @cached_property
    def paths(self):
        if self.verbose: log.debug(f"{self}: generating paths namespace")

        css_dir = self.dir / "css"
        css_dir.mkdir(exist_ok=True)
        if self.verbose: log.debug(f"{self}: created css_dir at {css_dir}")

        css_src = self.src / 'default.css'
        css_dest = css_dir / 'default.css'
        if not css_dest.exists():
            shutil.copy(css_src, css_dir)
            if self.verbose: log.debug(f"{self}: copied {css_src.name} to {css_dest}")

        templates_dir = self.dir / "templates"
        templates_dir.mkdir(exist_ok=True)
        if self.verbose: log.debug(f"{self}: created templates_dir at {templates_dir}")

        for src in ('card.j2', 'detail.j2'):
            src_path = self.src / src
            dest = templates_dir / src
            if not dest.exists():
                shutil.copy(src_path, templates_dir)
                if self.verbose: log.debug(f"{self}: copied {src} to {dest}")

        tables = []
        for tbl in self.pygosql.tables:
            p = self.dir / tbl
            p.mkdir(parents=True, exist_ok=True)
            tables.append(p)
            if self.verbose: log.debug(f"{self}: initialized table dir {p}")

        ns = SimpleNamespace(
            css=css_dest,
            card=templates_dir / 'card.j2',
            detail=templates_dir / 'detail.j2',
            tables=tables
        )
        if self.verbose: log.debug(f"{self}: paths namespace ready {ns}")
        return ns

class TemplateManager:
    """
    Manages Jinja2 template rendering for default templates.
    """
    instance=None
    src_env = {
    }
    envs = {
    }
    def __init__(self, pygosqlviews: PyGoSQLViews):
        self.pygosqlviews = pygosqlviews
        self.verbose = pygosqlviews.verbose
        tmpl_dir = self.pygosqlviews.dir.src

    @cached_property
    def src(self):

    def render_meta_template(self, target_dir: Path, **kwargs) -> None:
        """
        Render a Jinja2 template from default_path into target_dir using provided context.

        Args:
            default_path: Path to the source .j2 file.
            target_dir: Directory where rendered file will be written.
            **kwargs: Context parameters for Jinja2 rendering.
        """
        env = self._env_cache.get(tmpl_dir)
        if not env:
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(tmpl_dir)),
                autoescape=False
            )
            self._env_cache[tmpl_dir] = env
        template = env.get_template(default_path.name)
        rendered = template.render(**kwargs)
        out_path = target_dir / default_path.name
        out_path.write_text(rendered, encoding="utf-8")
        if self.verbose:
            log.info(f"[TemplateManager]: Rendered {default_path.name} to {out_path}.")

class Table(AwaitLoader):
    DEFAULT_CONFIG = {
        "id": "", #This is your id column specified from the SQL Table
        "card_title": "", #This is your column specified as the card title
        "card_subtitle": "", #cont.
        "card_image": "", #cont.
    }

    def __init__(self, pygosqlviews: PyGoSQLViews, path: Path):
        self.pygosqlviews: PyGoSQLViews = pygosqlviews
        self.pygosql: PyGoSQL = pygosqlviews.pygosql
        self.verbose = pygosqlviews.verbose
        self.css = self.pygosqlviews.dir.paths.css
        self.dir = Path(self.pygosql._sql_root)
        self.path = path
        self.name = self.path.name
        _ = self.paths
        if self.verbose: log.success(f"{self}: Successfully initialized!")

    def __repr__(self):
        return f"PyGOSQL.{self.name.title()}"

    @cached_property
    def paths(self) -> SimpleNamespace:
        """
        Paths for table templates and config.
        """
        card = self.path / "card.j2"
        detail = self.path / "detail.j2"
        config = self.path / "config.json"
        if not card.exists():
            if self.verbose:
                log.warning(f"[{self}]: Card template not found at {card}.")
            self.render_from_default(self.pygosqlviews.dir.paths.card)
        if not detail.exists():
            if self.verbose:
                log.warning(f"[{self}]: Detail template not found at {detail}.")
            self.render_from_default(self.pygosqlviews.dir.paths.detail)
        if not config.exists():
            if self.verbose:
                log.warning(f"[{self}]: Config file not found at {config}, creating default.")
            config.write_text(json.dumps(self.DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return SimpleNamespace(card=card, detail=detail, config=config)

    @async_cached_property
    async def columns(self) -> list[str]:
        """
        Fetch this table's columns with cache fallback.
        """
        if self.verbose:
            log.info(f"[{self}]: Fetching columns for {self.name}.")
        try:
            schema = await self.pygosql.schema
        except Exception as e:
            if self.verbose:
                log.warning(f"[{self}]: Failed to fetch schema: {e}. Refreshing schema.")
            schema = await self.pygosql.refresh_schema()
        if self.name not in schema:
            if self.verbose:
                log.warning(f"[{self}]: {self.name} not in schema cache. Refreshing schema.")
            schema = await self.pygosql.refresh_schema()
        cols = schema.get(self.name, [])
        if cols:
            if self.verbose:
                log.debug(f"[{self}]: Columns loaded → {cols}.")
                log.info(f"[{self}]: Retrieved {len(cols)} columns for {self.name}.")
        else:
            log.error(f"[{self}]: No columns found for {self.name}.")
        return cols

    async def schema(self) -> list[str]:
        """
        Retrieve this table's schema bypassing cache.
        """
        if self.verbose:
            log.info(f"[{self}]: Retrieving schema for {self.name}.")
        self.__dict__.pop("columns", None)
        if self.verbose:
            log.debug(f"[{self}]: Cleared cached columns.")
        return await self.columns

    @async_cached_property
    async def config(self) -> SimpleNamespace:
        """
        Load or auto-populate table config.
        """
        data = json.loads(self.paths.config.read_text(encoding="utf-8"))
        ns = SimpleNamespace(**data)
        if self.verbose:
            log.debug(f"[{self}]: Loaded config → {ns}.")
        empty = [k for k, v in vars(ns).items() if isinstance(v, str) and not v]
        if empty:
            if self.verbose:
                log.warning(f"[{self}]: Empty config fields {empty}, auto-populating.")
            await self._auto_populate_config()
            self.__dict__.pop("config", None)
            return await self.config
        return ns

    async def _auto_populate_config(self) -> None:
        """
        Auto-populate config file with defaults based on table columns.
        """
        cols = await self.columns
        if not cols:
            if self.verbose:
                log.error(f"[{self}]: No columns available for auto-population.")
            return
        cfg_path = self.paths.config
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg.setdefault("id", cols[0])
        cfg.setdefault("card_title", cols[1] if len(cols) > 1 else cols[0])
        cfg.setdefault("card_subtitle", cols[2] if len(cols) > 2 else "")
        cfg.setdefault("card_image", next((c for c in cols if "img" in c.lower()), ""))
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        if self.verbose:
            log.info(f"[{self}]: Auto-populated config → {cfg}.")


async def debug():
    server = PyGoSQL(sql_root=Path(r"C:\Users\cblac\PycharmProjects\PyGoSQL Views\sql"), verbose=True)
    await server.launch()
    test: PyGoSQLViews = server.views
    await server.users.insert(name="joe", email="unique@example.com")
    log.debug(await server.users.select(name="joe"))
    card = await test.tables.users.render_card("joe")
    log.warning(card)
    time.sleep(10000)

if __name__ == "__main__":
    asyncio.run(debug())

#
#     def render(self, vars):
#         #Render templates in table path
#         #attach css at top
#
#     def render_card(self, row):
#         #attach css at top
#         vars = {}
#         for column in row:
#             insert
#
#     def render_detail(self):
#         card
#
#     def write_route(self, row_id, view_type):
#        return f"/{self.name}/{row_id}/{view_type}"
#
#
# class RecordProcessor:
#     """Processes database records for display"""
#
#     def __init__(self, pygosqlviews: 'PyGoSQLViews'):
#         self.pygosqlviews = pygosqlviews
#
#     async def prepare_card_data(self, table_name: str, records: List[Dict]) -> List[Dict[str, Any]]:
#         """Prepare records for card display"""
#         config = await self._get_table_config(table_name)
#         processed_records = []
#
#         log.debug(f"Processing {len(records)} records for {table_name}")
#
#         for record in records:
#             try:
#                 card_data = {
#                     'id': self.extract_record_id(record),
#                     'title': config.get_display_title(record),
#                     'image_url': config.get_image_url(record),
#                     'fields': {}
#                 }
#
#                 # Add configured card fields
#                 fields_to_show = config.card_fields if config.card_fields else list(record.keys())[:3]
#                 for field in fields_to_show:
#                     if field in record and config.should_show_field(field):
#                         label = config.get_field_label(field)
#                         value = format_field_value(record[field], field)
#                         card_data['fields'][label] = value
#
#                 processed_records.append(card_data)
#
#             except Exception as e:
#                 log.error(f"Error processing record {record}: {e}")
#                 continue
#
#         log.debug(f"Successfully processed {len(processed_records)} records")
#         return processed_records
#
#     async def prepare_detail_data(self, table_name: str, record: Dict) -> Dict[str, Any]:
#         """Prepare record for detail view with relationships"""
#         config = await self._get_table_config(table_name)
#
#         detail_data = {
#             'title': config.get_display_title(record),
#             'image_url': config.get_image_url(record),
#             'fields': {},
#             'relationships': await self.get_foreign_key_links(table_name, record)
#         }
#
#         for field, value in record.items():
#             if config.should_show_field(field):
#                 label = config.get_field_label(field)
#                 formatted_value = format_field_value(value, field)
#                 detail_data['fields'][label] = formatted_value
#
#         log.debug(f"Prepared detail data for {table_name} record: {detail_data['title']}")
#         return detail_data
#
#     def extract_record_id(self, record: Dict) -> str:
#         """Extract primary key from record"""
#         # Try common primary key names
#         for pk_name in ['id', 'uuid', 'pk', '_id']:
#             if pk_name in record:
#                 return str(record[pk_name])
#
#         # Fallback to first field
#         if record:
#             first_key = next(iter(record.keys()))
#             return str(record[first_key])
#         return ""
#
#     async def get_foreign_key_links(self, table_name: str, record: Dict) -> List[Dict[str, str]]:
#         """Get foreign key relationships as clickable links"""
#         config = await self._get_table_config(table_name)
#         links = []
#
#         for field, related_table in config.relationships.items():
#             if field in record and record[field]:
#                 links.append({
#                     'label': config.get_field_label(field),
#                     'table': related_table,
#                     'id': str(record[field]),
#                     'url': f"/table/{related_table}/row/{record[field]}"
#                 })
#
#         return links
#
#     async def _get_table_config(self, table_name: str) -> TableConfig:
#         """Get table configuration"""
#         try:
#             configs = await self.pygosqlviews.directories.mkconfigs
#             config_path = configs.get(table_name)
#             if config_path and config_path.exists():
#                 return TableConfig.load_from_file(config_path)
#         except Exception as e:
#             log.warning(f"Failed to load config for {table_name}: {e}")
#
#         # Return default config
#         return TableConfig(Path(""))
#
#
# class PyGoSQLViews:
#     """Main FastAPI application for database browsing"""
#
#     def __init__(self,
#                  pygosql: PyGoSQL,
#                  pygosql_dir: Path,
#                  template_dir: Optional[Path] = None,
#                  static_dir: Optional[Path] = None,
#                  verbose_logging: bool = False):
#         self.pygosql = pygosql
#         self.pygosql_dir = Path(pygosql_dir)
#
#         # Setup logging
#         global logger
#         logger = setup_logging(verbose_logging)
#
#         log.info(f"Initializing PyGoSQLViews with directory: {self.pygosql_dir}")
#
#         self.directories = Directories(self)
#         self.processor = RecordProcessor(self)
#
#         # Setup directories
#         dirs = self.directories.mkdirs
#         self.template_dir = template_dir or dirs['templates']
#         self.static_dir = static_dir or dirs['static']
#
#         # Initialize FastAPI
#         self.app = FastAPI(
#             title="PyGoSQL Views",
#             version="1.0.0",
#             description="HTML admin interface for PyGoSQL APIs"
#         )
#
#         self.templates = Jinja2Templates(directory=str(self.template_dir))
#
#         self._setup_routes()
#         self._setup_static_files()
#
#         log.info("PyGoSQLViews initialized successfully")
#
#     def _setup_routes(self):
#         """Configure FastAPI routes"""
#         self.app.get("/", response_class=HTMLResponse)(self.database_view)
#         self.app.get("/table/{table_name}", response_class=HTMLResponse)(self.table_view)
#         self.app.get("/table/{table_name}/row/{row_id}", response_class=HTMLResponse)(self.row_view)
#         self.app.get("/table/{table_name}/search", response_class=HTMLResponse)(self.search_table)
#
#         log.debug("Routes configured successfully")
#
#     def _setup_static_files(self):
#         """Mount static file serving"""
#         if self.static_dir.exists():
#             self.app.mount("/static", StaticFiles(directory=str(self.static_dir)), name="static")
#             log.debug(f"Static files mounted from: {self.static_dir}")
#
#     async def database_view(self, request: Request) -> HTMLResponse:
#         """Show all available tables as cards"""
#         try:
#             log.debug("Loading database view")
#             tables = await self.pygosql.get_tables()
#
#             context = {
#                 **get_base_context(),
#                 "tables": sorted(tables),  # Sort for consistent display
#                 "breadcrumbs": get_breadcrumbs()
#             }
#
#             log.debug(f"Found {len(tables)} tables")
#             return self.templates.TemplateResponse("database.html", {"request": request, **context})
#
#         except Exception as e:
#             log.error(f"Database view error: {e}")
#             raise HTTPException(status_code=500, detail="Failed to load database view")
#
#     async def table_view(self, request: Request, table_name: str) -> HTMLResponse:
#         """Show all records in table as cards"""
#         try:
#             log.debug(f"Loading table view for: {table_name}")
#
#             # Get records with optional pagination
#             limit = int(request.query_params.get('limit', 100))
#             offset = int(request.query_params.get('offset', 0))
#
#             records = await self.pygosql.select_all(table_name, limit=limit, offset=offset)
#             card_data = await self.processor.prepare_card_data(table_name, records)
#
#             context = {
#                 **get_base_context(),
#                 "table_name": table_name,
#                 "records": card_data,
#                 "breadcrumbs": get_breadcrumbs(table_name),
#                 "has_more": len(records) == limit,
#                 "next_offset": offset + limit if len(records) == limit else None,
#                 "prev_offset": max(0, offset - limit) if offset > 0 else None
#             }
#
#             log.debug(f"Loaded {len(records)} records from {table_name}")
#             return self.templates.TemplateResponse("table.html", {"request": request, **context})
#
#         except Exception as e:
#             log.error(f"Table view error for {table_name}: {e}")
#             raise HTTPException(status_code=500, detail=f"Failed to load table {table_name}")
#
#     async def row_view(self, request: Request, table_name: str, row_id: str) -> HTMLResponse:
#         """Show detailed view of single record with foreign key links"""
#         try:
#             log.debug(f"Loading row view for: {table_name}/{row_id}")
#
#             record = await self.pygosql.select_by_id(table_name, row_id)
#             if not record:
#                 log.warning(f"Record not found: {table_name}/{row_id}")
#                 raise HTTPException(status_code=404, detail="Record not found")
#
#             detail_data = await self.processor.prepare_detail_data(table_name, record)
#
#             context = {
#                 **get_base_context(),
#                 "table_name": table_name,
#                 "row_id": row_id,
#                 "record": detail_data,
#                 "breadcrumbs": get_breadcrumbs(table_name, row_id)
#             }
#
#             log.debug(f"Loaded detail view for {table_name}/{row_id}")
#             return self.templates.TemplateResponse("row.html", {"request": request, **context})
#
#         except HTTPException:
#             raise
#         except Exception as e:
#             log.error(f"Row view error for {table_name}/{row_id}: {e}")
#             raise HTTPException(status_code=500, detail="Failed to load record")
#
#     async def search_table(self, request: Request, table_name: str, q: str = Query("")) -> HTMLResponse:
#         """Search records in a table"""
#         try:
#             log.debug(f"Searching {table_name} for: '{q}'")
#
#             records = []
#             if q:
#                 # Get search configuration
#                 config = await self.processor._get_table_config(table_name)
#                 search_fields = config.search_fields
#
#                 if not search_fields:
#                     # Fallback: search all string fields
#                     sample_records = await self.pygosql.select_all(table_name, limit=1)
#                     if sample_records:
#                         sample = sample_records[0]
#                         search_fields = [
#                             field for field, value in sample.items()
#                             if isinstance(value, str) and field not in config.hidden_fields
#                         ]
#
#                 # Perform search using PyGoSQL's search capability
#                 if hasattr(self.pygosql, 'search'):
#                     records = await self.pygosql.search(table_name, q, fields=search_fields)
#                 else:
#                     # Fallback: manual search implementation
#                     records = await self._manual_search(table_name, q, search_fields)
#
#             card_data = await self.processor.prepare_card_data(table_name, records)
#
#             context = {
#                 **get_base_context(),
#                 "table_name": table_name,
#                 "query": q,
#                 "records": card_data,
#                 "breadcrumbs": get_breadcrumbs(table_name),
#                 "search_performed": bool(q)
#             }
#
#             log.debug(f"Search for '{q}' in {table_name} returned {len(records)} results")
#             return self.templates.TemplateResponse("search.html", {"request": request, **context})
#
#         except Exception as e:
#             log.error(f"Search error for {table_name} with query '{q}': {e}")
#             raise HTTPException(status_code=500, detail="Search failed")
#
#     async def _manual_search(self, table_name: str, query: str, search_fields: List[str]) -> List[Dict]:
#         """Fallback manual search implementation"""
#         try:
#             all_records = await self.pygosql.select_all(table_name)
#             matching_records = []
#
#             query_lower = query.lower()
#
#             for record in all_records:
#                 match_found = False
#                 for field in search_fields:
#                     if field in record:
#                         field_value = str(record[field]).lower()
#                         if query_lower in field_value:
#                             match_found = True
#                             break
#
#                 if match_found:
#                     matching_records.append(record)
#
#             return matching_records
#
#         except Exception as e:
#             log.error(f"Manual search failed: {e}")
#             return []
#
#     async def health_check(self) -> Dict[str, str]:
#         """Health check endpoint"""
#         try:
#             # Test database connection
#             tables = await self.pygosql.get_tables()
#             return {
#                 "status": "healthy",
#                 "tables_count": str(len(tables)),
#                 "timestamp": datetime.now().isoformat()
#             }
#         except Exception as e:
#             log.error(f"Health check failed: {e}")
#             return {
#                 "status": "unhealthy",
#                 "error": str(e),
#                 "timestamp": datetime.now().isoformat()
#             }
#
#
# def get_base_context() -> Dict[str, Any]:
#     """Base template context"""
#     return {
#         "app_name": "PyGoSQL Views",
#         "version": "1.0.0",
#         "timestamp": datetime.now().isoformat()
#     }
#
#
# def get_breadcrumbs(table_name: str = None, row_id: str = None) -> List[Dict[str, str]]:
#     """Generate breadcrumb navigation"""
#     breadcrumbs = [{"name": "Database", "url": "/"}]
#
#     if table_name:
#         breadcrumbs.append({
#             "name": table_name.replace('_', ' ').title(),
#             "url": f"/table/{table_name}"
#         })
#
#     if row_id:
#         breadcrumbs.append({
#             "name": f"Record {row_id}",
#             "url": f"/table/{table_name}/row/{row_id}"
#         })
#
#     return breadcrumbs
#
#
# def format_field_value(value: Any, field_name: str = "") -> str:
#     """Format field value for display"""
#     if value is None:
#         return ""
#
#     # Handle different data types
#     if isinstance(value, bool):
#         return "✓" if value else "✗"
#     elif isinstance(value, (int, float)):
#         # Format numbers with appropriate precision
#         if isinstance(value, float):
#             return f"{value:.2f}" if value != int(value) else str(int(value))
#         return str(value)
#     elif isinstance(value, str):
#         # Truncate long strings
#         if len(value) > 100:
#             return value[:97] + "..."
#         return value
#     elif isinstance(value, datetime):
#         return value.strftime("%Y-%m-%d %H:%M:%S")
#     elif isinstance(value, (list, dict)):
#         # Handle JSON fields
#         try:
#             json_str = json.dumps(value, indent=2)
#             return json_str[:100] + "..." if len(json_str) > 100 else json_str
#         except:
#             return str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
#     else:
#         str_value = str(value)
#         return str_value[:100] + "..." if len(str_value) > 100 else str_value
#
#
# def create_app(pygosql_client: PyGoSQL,
#                pygosql_dir: Path,
#                verbose_logging: bool = False) -> FastAPI:
#     """Create PyGoSQLViews FastAPI application"""
#     views = PyGoSQLViews(
#         pygosql_client,
#         pygosql_dir,
#         verbose_logging=verbose_logging
#     )
#
#     # Add health check endpoint
#     views.app.get("/health")(views.health_check)
#
#     return views.app
#
#
# # Usage example and CLI support
# async def main():
#     """Example usage and CLI entry point"""
#     import argparse
#
#     parser = argparse.ArgumentParser(description="PyGoSQL Views - Database Admin Interface")
#     parser.add_argument("--sql-dir", required=True, help="Path to SQL directory")
#     parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
#     parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
#     parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
#     parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
#
#     args = parser.parse_args()
#
#     # Setup logging
#     setup_logging(args.verbose)
#
#     try:
#         # Initialize PyGoSQL (you'll need to adapt this to your actual PyGoSQL setup)
#         pygosql_client = PyGoSQL(sql_root=args.sql_dir)
#
#         # Create the FastAPI app
#         app = create_app(
#             pygosql_client,
#             Path(args.sql_dir),
#             verbose_logging=args.verbose
#         )
#
#         # Run with uvicorn
#         import uvicorn
#         uvicorn.run(
#             app,
#             host=args.host,
#             port=args.port,
#             reload=args.reload,
#             log_level="debug" if args.verbose else "info"
#         )
#
#     except Exception as e:
#         log.error(f"Failed to start application: {e}")
#         raise
#
#
# if __name__ == "__main__":
#     asyncio.run(main())