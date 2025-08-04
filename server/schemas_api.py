"""YAML Command Schemas API for N8N MCP Integration.

Professional endpoint to serve command schemas for N8N workflows.
Optimized with caching and proper error handling.

Path: server/schemas_api.py
"""
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from fastapi import HTTPException


class SchemasAPI:
    """Professional YAML schemas API with caching."""

    def __init__(self):
        """Initialize schemas API with project paths."""
        self.project_root = Path(__file__).parent.parent
        self.schemas_dir = self.project_root / "shared" / "command_schemas"
        self._cache_time = {}
        self._cache_ttl = 300  # 5 minutes cache

    def _get_schema_file_path(self, schema_name: str) -> Path:
        """Get schema file path with validation."""
        schema_file = self.schemas_dir / f"{schema_name}.yaml"
        if not schema_file.exists():
            raise HTTPException(status_code=404, detail=f"Schema '{schema_name}' not found")
        return schema_file

    def _is_cache_valid(self, schema_name: str, file_path: Path) -> bool:
        """Check if cached schema is still valid."""
        if schema_name not in self._cache_time:
            return False

        cached_time = self._cache_time[schema_name]
        file_mtime = file_path.stat().st_mtime
        current_time = time.time()

        # Cache invalid if file modified or TTL expired
        return file_mtime <= cached_time and current_time - cached_time < self._cache_ttl

    @lru_cache(maxsize=32)
    def _load_yaml_file(self, file_path: str, mtime: float) -> Dict[str, Any]:
        """Load YAML file with LRU cache (mtime for cache invalidation)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise HTTPException(status_code=500, detail=f"YAML parsing error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"File reading error: {str(e)}")

    def get_schema(self, schema_name: str) -> Dict[str, Any]:
        """Get individual command schema with caching."""
        file_path = self._get_schema_file_path(schema_name)

        # Use file modification time for cache key
        mtime = file_path.stat().st_mtime
        schema_data = self._load_yaml_file(str(file_path), mtime)

        # Update cache time
        self._cache_time[schema_name] = time.time()

        return {
            "schema_name": schema_name,
            "data": schema_data,
            "file_path": str(file_path.relative_to(self.project_root)),
            "last_modified": mtime,
            "cached": True,
        }

    def get_all_schemas(self) -> Dict[str, Any]:
        """Get all command schemas with metadata."""
        if not self.schemas_dir.exists():
            raise HTTPException(status_code=500, detail="Schemas directory not found")

        schemas = {}
        metadata = {
            "total_schemas": 0,
            "schemas_directory": str(self.schemas_dir.relative_to(self.project_root)),
            "cache_ttl_seconds": self._cache_ttl,
        }

        # Load all YAML files
        for yaml_file in self.schemas_dir.glob("*.yaml"):
            schema_name = yaml_file.stem
            try:
                mtime = yaml_file.stat().st_mtime
                schema_data = self._load_yaml_file(str(yaml_file), mtime)

                schemas[schema_name] = {
                    "data": schema_data,
                    "file_name": yaml_file.name,
                    "last_modified": mtime,
                }

                # Update cache time
                self._cache_time[schema_name] = time.time()

            except Exception as e:
                # Continue loading other schemas if one fails
                schemas[schema_name] = {"error": str(e)}

        metadata["total_schemas"] = len(schemas)

        return {"metadata": metadata, "schemas": schemas}

    def get_schemas_for_mcp(self) -> Dict[str, Any]:
        """Get schemas optimized for MCP tool definitions."""
        all_schemas = self.get_all_schemas()

        mcp_tools = {}
        for schema_name, schema_info in all_schemas["schemas"].items():
            if "error" in schema_info:
                continue

            schema_data = schema_info["data"]

            # Extract MCP-relevant information
            mcp_tools[schema_name] = {
                "name": schema_data.get("name", schema_name),
                "description": schema_data.get("description", ""),
                "category": schema_data.get("category", "general"),
                "mcp_tool_schema": schema_data.get("mcp_tool_schema", {}),
                "ai_guidelines": schema_data.get("ai_guidelines", {}),
                "natural_language_patterns": schema_data.get("ai_guidelines", {}).get(
                    "natural_language_patterns", {}
                ),
            }

        return {"mcp_tools": mcp_tools, "metadata": all_schemas["metadata"]}

    def clear_cache(self) -> Dict[str, Any]:
        """Clear schemas cache (useful for development)."""
        self._load_yaml_file.cache_clear()
        self._cache_time.clear()

        return {"status": "success", "message": "Schemas cache cleared", "timestamp": time.time()}


# Global instance for FastAPI endpoints
schemas_api = SchemasAPI()
