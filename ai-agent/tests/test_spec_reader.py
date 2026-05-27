# ============================================================
# test_spec_reader.py — Unit Tests for OpenAPI Spec Reader
# ============================================================

import json
import pytest
from unittest.mock import patch, MagicMock

from agent.spec_reader import OpenApiSpecReader


class TestOpenApiSpecReader:
    """Tests for the OpenApiSpecReader module."""

    # ---- Initialization Tests ----

    def test_init_default_url(self):
        """Should default to localhost:8080."""
        reader = OpenApiSpecReader()
        assert reader.provider_url == "http://localhost:8080"

    def test_init_custom_url(self):
        """Should accept a custom provider URL."""
        reader = OpenApiSpecReader("http://custom-host:9090")
        assert reader.provider_url == "http://custom-host:9090"

    def test_init_strips_trailing_slash(self):
        """Should strip trailing slashes from URL."""
        reader = OpenApiSpecReader("http://localhost:8080/")
        assert reader.provider_url == "http://localhost:8080"

    # ---- load_spec_from_file Tests ----

    def test_load_spec_from_file(self, spec_file, sample_spec):
        """Should load and parse a spec from a JSON file."""
        reader = OpenApiSpecReader()
        result = reader.load_spec_from_file(spec_file)

        assert result is not None
        assert result["openapi"] == "3.0.1"
        assert result["info"]["title"] == "User Service API"

    def test_load_spec_from_file_sets_internal_state(self, spec_file):
        """Should set self.spec after loading."""
        reader = OpenApiSpecReader()
        reader.load_spec_from_file(spec_file)
        assert reader.spec is not None

    # ---- fetch_spec Tests (mocked HTTP) ----

    @patch("agent.spec_reader.requests.get")
    def test_fetch_spec_success(self, mock_get, sample_spec):
        """Should fetch and parse spec from Provider API."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_spec
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = OpenApiSpecReader("http://localhost:8080")
        result = reader.fetch_spec()

        mock_get.assert_called_once_with("http://localhost:8080/v3/api-docs", timeout=10)
        assert result["info"]["title"] == "User Service API"
        assert reader.spec == sample_spec

    @patch("agent.spec_reader.requests.get")
    def test_fetch_spec_connection_error(self, mock_get):
        """Should raise ConnectionError when Provider is not running."""
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError("Connection refused")

        reader = OpenApiSpecReader()
        with pytest.raises(ConnectionError, match="Cannot connect to Provider"):
            reader.fetch_spec()

    @patch("agent.spec_reader.requests.get")
    def test_fetch_spec_invalid_json(self, mock_get):
        """Should raise ValueError when response is not valid JSON."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
        mock_response.text = "<html>Not JSON</html>"
        mock_get.return_value = mock_response

        reader = OpenApiSpecReader()
        with pytest.raises(ValueError, match="not valid JSON"):
            reader.fetch_spec()

    # ---- resolve_ref Tests ----

    def test_resolve_ref_valid(self, spec_file):
        """Should resolve a valid $ref pointer."""
        reader = OpenApiSpecReader()
        reader.load_spec_from_file(spec_file)

        result = reader.resolve_ref("#/components/schemas/User")
        assert result["type"] == "object"
        assert "name" in result["properties"]
        assert "email" in result["properties"]

    def test_resolve_ref_invalid(self, spec_file):
        """Should return empty dict for invalid $ref."""
        reader = OpenApiSpecReader()
        reader.load_spec_from_file(spec_file)

        result = reader.resolve_ref("#/components/schemas/NonExistent")
        assert result == {}

    def test_resolve_ref_non_hash_prefix(self, spec_file):
        """Should return empty dict for non-# refs."""
        reader = OpenApiSpecReader()
        reader.load_spec_from_file(spec_file)

        result = reader.resolve_ref("external.json#/something")
        assert result == {}

    # ---- resolve_schema Tests ----

    def test_resolve_schema_with_ref(self, spec_file):
        """Should resolve schemas with $ref."""
        reader = OpenApiSpecReader()
        reader.load_spec_from_file(spec_file)

        schema = {"$ref": "#/components/schemas/User"}
        result = reader.resolve_schema(schema)
        assert "properties" in result
        assert "name" in result["properties"]

    def test_resolve_schema_array_type(self, spec_file):
        """Should resolve array items schemas."""
        reader = OpenApiSpecReader()
        reader.load_spec_from_file(spec_file)

        schema = {
            "type": "array",
            "items": {"$ref": "#/components/schemas/User"},
        }
        result = reader.resolve_schema(schema)
        assert result["type"] == "array"
        assert "properties" in result["items"]

    def test_resolve_schema_none(self, spec_file):
        """Should return empty dict for None schema."""
        reader = OpenApiSpecReader()
        reader.load_spec_from_file(spec_file)
        assert reader.resolve_schema(None) == {}

    # ---- extract_endpoints Tests ----

    def test_extract_endpoints_count(self, spec_file):
        """Should extract all 5 endpoints from the spec."""
        reader = OpenApiSpecReader()
        reader.load_spec_from_file(spec_file)
        endpoints = reader.extract_endpoints()
        assert len(endpoints) == 5

    def test_extract_endpoints_methods(self, spec_file):
        """Should extract correct HTTP methods."""
        reader = OpenApiSpecReader()
        reader.load_spec_from_file(spec_file)
        endpoints = reader.extract_endpoints()

        methods = [ep["method"] for ep in endpoints]
        assert "get" in methods
        assert "post" in methods
        assert "put" in methods
        assert "delete" in methods

    def test_extract_endpoints_paths(self, spec_file):
        """Should extract correct URL paths."""
        reader = OpenApiSpecReader()
        reader.load_spec_from_file(spec_file)
        endpoints = reader.extract_endpoints()

        paths = [ep["path"] for ep in endpoints]
        assert "/api/users" in paths
        assert "/api/users/{id}" in paths

    def test_extract_endpoints_path_params(self, spec_file):
        """Should extract path parameters correctly."""
        reader = OpenApiSpecReader()
        reader.load_spec_from_file(spec_file)
        endpoints = reader.extract_endpoints()

        get_by_id = next(
            ep for ep in endpoints
            if ep["method"] == "get" and ep["path"] == "/api/users/{id}"
        )
        assert len(get_by_id["path_parameters"]) == 1
        assert get_by_id["path_parameters"][0]["name"] == "id"
        assert get_by_id["path_parameters"][0]["type"] == "integer"

    def test_extract_endpoints_request_body(self, spec_file):
        """Should extract request body schema for POST/PUT."""
        reader = OpenApiSpecReader()
        reader.load_spec_from_file(spec_file)
        endpoints = reader.extract_endpoints()

        post = next(ep for ep in endpoints if ep["method"] == "post")
        assert post["request_body_schema"] is not None
        assert "properties" in post["request_body_schema"]
        assert "name" in post["request_body_schema"]["properties"]

    def test_extract_endpoints_no_spec_loaded(self):
        """Should raise RuntimeError if no spec loaded."""
        reader = OpenApiSpecReader()
        with pytest.raises(RuntimeError, match="No spec loaded"):
            reader.extract_endpoints()

    def test_extract_endpoints_responses(self, spec_file):
        """Should extract response status codes and schemas."""
        reader = OpenApiSpecReader()
        reader.load_spec_from_file(spec_file)
        endpoints = reader.extract_endpoints()

        get_all = next(
            ep for ep in endpoints
            if ep["method"] == "get" and ep["path"] == "/api/users"
        )
        assert "200" in get_all["responses"]
        assert get_all["responses"]["200"]["schema"] is not None
