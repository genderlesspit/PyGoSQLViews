"""
PyGoSQLViews - HTML admin interface for PyGoSQL APIs

This module provides a FastAPI-based web interface for browsing PyGoSQL database APIs.
It offers a card-based navigation system: database → table → row with configurable
display options for each table.

Features:
- Automatic directory and configuration file creation
- Configurable table display settings
- Card and detail view templates
- Foreign key relationship navigation
- Search functionality
- Responsive HTML interface
"""

import json
from functools import cached_property
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Awaitable

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pygosql import PyGoSQL
from async_property import AwaitLoader, async_cached_property
from loguru import Logger

# Plugin registration
from toomanyplugins import plugin

log: Logger

@plugin(PyGoSQL, cached_property)
def views(self: PyGoSQL) -> PyGoSQLViews:
    """
    Add views property to PyGoSQL instances.
    
    This plugin function registers the PyGoSQLViews with PyGoSQL instances,
    allowing access via `pygosql_instance.views`.
    
    Args:
        self: The PyGoSQL instance
        
    Returns:
        PyGoSQLViews instance configured for this PyGoSQL connection
    """
    ...

class Directories(AwaitLoader):
    """
    Manages directory structure and file creation for PyGoSQLViews.
    
    This class handles the automatic creation of required directories
    and configuration files for the web interface.
    """

    DEFAULT_CONFIG: Dict[str, Any]
    """Default configuration template for table display settings"""

    def __init__(self, pygosqlviews: PyGoSQLViews) -> None:
        """
        Initialize directory manager.
        
        Args:
            pygosqlviews: Parent PyGoSQLViews instance
        """
        ...

    @cached_property
    def mkdirs(self) -> Dict[str, Path]:
        """
        Create required directories and return paths.
        
        Creates the following directories if they don't exist:
        - css: Custom CSS files
        - templates: Jinja2 HTML templates
        - static: Static assets (images, JS, etc.)
        - config: Table configuration JSON files
        
        Returns:
            Dictionary mapping directory names to Path objects
        """
        ...

    @async_cached_property
    async def mkconfigs(self) -> Dict[str, Path]:
        """
        Create configuration files for each database table.
        
        Generates JSON configuration files for each table in the database,
        using DEFAULT_CONFIG as the template. Only creates files that don't
        already exist.
        
        Returns:
            Dictionary mapping table names to their config file paths
            
        Raises:
            Exception: If database tables cannot be retrieved
        """
        ...

class CSS:
    """
    Handles CSS generation and management for the web interface.
    
    Provides methods to generate custom CSS for card and detail views,
    with support for theming and responsive design.
    """

    def __init__(self, pygosqlviews: PyGoSQLViews) -> None:
        """
        Initialize CSS manager.
        
        Args:
            pygosqlviews: Parent PyGoSQLViews instance
        """
        ...

    @cached_property
    def detail(self) -> str:
        """
        Generate CSS for detail view pages.
        
        Returns:
            CSS string for styling record detail pages
        """
        ...

    @cached_property
    def card(self) -> str:
        """
        Generate CSS for card view pages.
        
        Returns:
            CSS string for styling record card layouts
        """
        ...

class Templates:
    """
    Manages HTML template generation and rendering.
    
    Handles the creation and rendering of Jinja2 templates for
    database, table, and record views.
    """

    def __init__(self, pygosqlviews: PyGoSQLViews) -> None:
        """
        Initialize template manager.
        
        Args:
            pygosqlviews: Parent PyGoSQLViews instance
        """
        ...

    @cached_property
    def css(self) -> CSS:
        """
        Get CSS manager instance.
        
        Returns:
            CSS manager for generating stylesheets
        """
        ...

    async def detail(self, input_data: Dict[str, Any]) -> str:
        """
        Render a detail view template.
        
        Args:
            input_data: Data context for template rendering
            
        Returns:
            Rendered HTML string for detail view
        """
        ...

    async def card(self, input_data: Dict[str, Any]) -> str:
        """
        Render a card view template.
        
        Args:
            input_data: Data context for template rendering
            
        Returns:
            Rendered HTML string for card view
        """
        ...

    async def package_with_css(self) -> str:
        """
        Package templates with embedded CSS.
        
        Returns:
            Complete HTML package with inline styles
        """
        ...

    async def render(self, input_data: Dict[str, Any]) -> str:
        """
        Main template rendering entry point.
        
        Args:
            input_data: Data context for template rendering
            
        Returns:
            Rendered HTML string with css header
        """
        ...

class Table:
    """
    Configuration manager for individual table UI display settings.
    
    Handles loading and providing access to table-specific configuration
    such as display fields, hidden fields, field labels, and relationships.
    """

    def __init__(self, config_path: Path) -> None:
        """
        Initialize table configuration.
        
        Args:
            config_path: Path to the table's JSON configuration file
        """
        ...

    @cached_property
    def config(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Configuration dictionary, falls back to DEFAULT_CONFIG if file
            cannot be loaded
        """
        ...

    @cached_property
    def display_field(self) -> str:
        """
        Get the primary display field name.
        
        Returns:
            Field name to use as the main title/identifier for records
        """
        ...

    @cached_property
    def image_field(self) -> Optional[str]:
        """
        Get the image field name if configured.
        
        Returns:
            Field name containing image URLs, or None if not configured
        """
        ...

    @cached_property
    def fallback_image(self) -> str:
        """
        Get the fallback image URL.
        
        Returns:
            URL to use when no image is available for a record
        """
        ...

    @cached_property
    def card_fields(self) -> List[str]:
        """
        Get list of fields to display in card view.
        
        Returns:
            List of field names to show in card layout
        """
        ...

    @cached_property
    def hidden_fields(self) -> List[str]:
        """
        Get list of fields to hide from display.
        
        Returns:
            List of field names to never show in the interface
        """
        ...

    @cached_property
    def field_labels(self) -> Dict[str, str]:
        """
        Get custom field labels mapping.
        
        Returns:
            Dictionary mapping field names to human-readable labels
        """
        ...

    @cached_property
    def relationships(self) -> Dict[str, str]:
        """
        Get foreign key relationships mapping.
        
        Returns:
            Dictionary mapping field names to related table names
        """
        ...

    @classmethod
    async def load_from_file(cls, config_path: Path) -> 'Table':
        """
        Load table configuration from JSON file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Table configuration instance
        """
        ...

    def get_display_title(self, record: Dict[str, Any]) -> str:
        """
        Get display title for a record.
        
        Args:
            record: Database record dictionary
            
        Returns:
            Human-readable title for the record
        """
        ...

    def get_image_url(self, record: Dict[str, Any]) -> Optional[str]:
        """
        Get image URL for a record.
        
        Args:
            record: Database record dictionary
            
        Returns:
            Image URL or fallback image if no image field is set
        """
        ...

    def should_show_field(self, field_name: str) -> bool:
        """
        Check if field should be displayed.
        
        Args:
            field_name: Name of the database field
            
        Returns:
            True if field should be shown, False if it's in hidden_fields
        """
        ...

    def get_field_label(self, field_name: str) -> str:
        """
        Get human-readable label for field.
        
        Args:
            field_name: Name of the database field
            
        Returns:
            Human-readable label, either from field_labels mapping or
            auto-generated from field name
        """
        ...

class RecordProcessor:
    """
    Processes database records for display in the web interface.
    
    Handles the transformation of raw database records into structured
    data suitable for template rendering, including relationship resolution
    and field formatting.
    """

    def __init__(self, pygosqlviews: PyGoSQLViews) -> None:
        """
        Initialize record processor.
        
        Args:
            pygosqlviews: Parent PyGoSQLViews instance
        """
        ...

    async def prepare_card_data(self, table_name: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare records for card display.
        
        Transforms raw database records into structured data for card view,
        including image URLs, display titles, and selected fields.
        
        Args:
            table_name: Name of the database table
            records: List of raw database records
            
        Returns:
            List of processed records ready for card template rendering
        """
        ...

    async def prepare_detail_data(self, table_name: str, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare record for detail view with relationships.
        
        Transforms a single database record into structured data for detail view,
        including all visible fields, relationships, and formatted values.
        
        Args:
            table_name: Name of the database table
            record: Raw database record
            
        Returns:
            Processed record data ready for detail template rendering
        """
        ...

    def extract_record_id(self, record: Dict[str, Any]) -> str:
        """
        Extract primary key from record.
        
        Attempts to find the primary key using common field names
        (id, uuid, pk) or falls back to the first field value.
        
        Args:
            record: Database record dictionary
            
        Returns:
            String representation of the record's primary key
        """
        ...

    async def get_foreign_key_links(self, table_name: str, record: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Get foreign key relationships as clickable links.
        
        Identifies foreign key fields based on table configuration and
        generates navigation links to related records.
        
        Args:
            table_name: Name of the database table
            record: Database record with potential foreign keys
            
        Returns:
            List of link dictionaries with label, table, id, and url keys
        """
        ...

    async def _get_table_config(self, table_name: str) -> Table:
        """
        Get table configuration instance.
        
        Args:
            table_name: Name of the database table
            
        Returns:
            Table configuration instance, with default config if not found
        """
        ...

class PyGoSQLViews:
    """
    Main FastAPI application for database browsing.
    
    Provides a complete web interface for browsing PyGoSQL database APIs
    with card-based navigation, configurable display options, and search
    functionality.
    """

    def __init__(self,
                 pygosql: PyGoSQL,
                 pygosql_dir: Path,
                 template_dir: Optional[Path] = None,
                 static_dir: Optional[Path] = None) -> None:
        """
        Initialize PyGoSQLViews application.
        
        Args:
            pygosql: PyGoSQL database client instance
            pygosql_dir: Base directory for PyGoSQL files
            template_dir: Custom template directory (optional)
            static_dir: Custom static files directory (optional)
        """
        ...

    pygosql: PyGoSQL
    """PyGoSQL database client instance"""
    
    pygosql_dir: Path
    """Base directory for PyGoSQL files"""
    
    directories: Directories
    """Directory manager instance"""
    
    processor: RecordProcessor
    """Record processor instance"""
    
    template_dir: Path
    """Directory containing Jinja2 templates"""
    
    static_dir: Path
    """Directory containing static files"""
    
    app: FastAPI
    """FastAPI application instance"""
    
    templates: Jinja2Templates
    """Jinja2 template engine"""

    def _setup_routes(self) -> None:
        """
        Configure FastAPI routes.
        
        Sets up all the web interface routes including database view,
        table view, row view, and search functionality.
        """
        ...

    def _setup_static_files(self) -> None:
        """
        Mount static file serving.
        
        Configures FastAPI to serve static files from the static directory.
        """
        ...

    async def database_view(self, request: Request) -> HTMLResponse:
        """
        Show all available tables as cards.
        
        Main database overview page displaying all tables in a card layout.
        
        Args:
            request: FastAPI request object
            
        Returns:
            HTML response with database overview
            
        Raises:
            HTTPException: If database tables cannot be loaded
        """
        ...

    async def table_view(self, request: Request, table_name: str) -> HTMLResponse:
        """
        Show all records in table as cards.
        
        Table overview page displaying all records in a card layout with
        pagination and search options.
        
        Args:
            request: FastAPI request object
            table_name: Name of the database table
            
        Returns:
            HTML response with table records
            
        Raises:
            HTTPException: If table records cannot be loaded
        """
        ...

    async def row_view(self, request: Request, table_name: str, row_id: str) -> HTMLResponse:
        """
        Show detailed view of single record with foreign key links.
        
        Detailed record view showing all visible fields, formatted values,
        and navigation links to related records.
        
        Args:
            request: FastAPI request object
            table_name: Name of the database table
            row_id: Primary key of the record
            
        Returns:
            HTML response with record details
            
        Raises:
            HTTPException: If record is not found or cannot be loaded
        """
        ...

    async def search_table(self, request: Request, table_name: str, q: str = "") -> HTMLResponse:
        """
        Search records in a table.
        
        Search functionality for finding records within a specific table
        based on query parameters.
        
        Args:
            request: FastAPI request object
            table_name: Name of the database table
            q: Search query string
            
        Returns:
            HTML response with search results
            
        Raises:
            HTTPException: If search operation fails
        """
        ...

def get_base_context() -> Dict[str, Any]:
    """
    Get base template context.
    
    Provides common template variables used across all pages.
    
    Returns:
        Dictionary with base template context variables
    """
    ...

def get_breadcrumbs(table_name: Optional[str] = None, row_id: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Generate breadcrumb navigation.
    
    Creates hierarchical navigation breadcrumbs based on current page context.
    
    Args:
        table_name: Current table name (optional)
        row_id: Current record ID (optional)
        
    Returns:
        List of breadcrumb dictionaries with name and url keys
    """
    ...

def format_field_value(value: Any, field_name: str = "") -> str:
    """
    Format field value for display.
    
    Converts database field values into human-readable strings with
    appropriate formatting for different data types.
    
    Args:
        value: Raw field value from database
        field_name: Name of the field (for context-specific formatting)
        
    Returns:
        Formatted string representation of the value
    """
    ...

def create_app(pygosql_client: PyGoSQL, pygosql_dir: Path) -> FastAPI:
    """
    Create PyGoSQLViews FastAPI application.
    
    Factory function to create and configure a complete FastAPI application
    with PyGoSQLViews integration.
    
    Args:
        pygosql_client: Configured PyGoSQL client instance
        pygosql_dir: Base directory for PyGoSQL files
        
    Returns:
        Configured FastAPI application ready to serve
    """
    ...