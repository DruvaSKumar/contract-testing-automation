# ============================================================
# spec_reader.py — OpenAPI Specification Reader
# ============================================================
# PURPOSE:
#   Fetches the OpenAPI 3.0 spec from a running Provider API
#   and parses it into a structured format that the contract
#   generator can use.
#
# HOW IT WORKS:
#   1. Sends HTTP GET to the Provider's /v3/api-docs endpoint
#   2. Parses the JSON response into a Python dictionary
#   3. Resolves all $ref references (e.g., "#/components/schemas/User")
#   4. Extracts a clean list of endpoints with their details:
#      - HTTP method (GET, POST, PUT, DELETE)
#      - URL path (/api/users, /api/users/{id})
#      - Path parameters (id)
#      - Request body schema (for POST/PUT)
#      - Response status codes and body schemas
#
# WHY IS THIS NEEDED?
#   The OpenAPI spec is the machine-readable source of truth for
#   the Provider's API. By reading it, the AI agent can automatically
#   generate contract files without manual effort — any time the
#   API changes, we just re-read the spec and regenerate.
# ============================================================

import json
import requests


class OpenApiSpecReader:
    """
    Reads and parses an OpenAPI 3.0 specification from a running
    Spring Boot application's /v3/api-docs endpoint.
    """

    def __init__(self, provider_url="http://localhost:8080"):
        """
        Args:
            provider_url: Base URL of the running Provider API.
                          Default is http://localhost:8080 (our User Service).
        """
        self.provider_url = provider_url.rstrip("/")
        self.spec = None  # Will hold the raw parsed spec

    def fetch_spec(self):
        """
        Fetches the OpenAPI spec from the Provider's /v3/api-docs endpoint.

        Returns:
            dict: The parsed OpenAPI specification.

        Raises:
            ConnectionError: If the Provider is not running.
            ValueError: If the response is not valid JSON.
        """
        url = f"{self.provider_url}/v3/api-docs"
        print(f"[SPEC READER] Fetching OpenAPI spec from: {url}")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"\n[ERROR] Cannot connect to Provider at {url}\n"
                f"  Make sure the Provider API is running:\n"
                f"    cd provider-api\n"
                f"    mvn spring-boot:run\n"
                f"  Then try again.\n"
            )
        except requests.exceptions.HTTPError as e:
            raise ValueError(
                f"\n[ERROR] Provider returned HTTP {e.response.status_code}\n"
                f"  URL: {url}\n"
                f"  Make sure springdoc-openapi is configured.\n"
            )

        try:
            self.spec = response.json()
        except json.JSONDecodeError:
            raise ValueError(
                f"\n[ERROR] Response from {url} is not valid JSON.\n"
                f"  Received: {response.text[:200]}\n"
            )

        version = self.spec.get("openapi", "unknown")
        title = self.spec.get("info", {}).get("title", "Unknown API")
        print(f"[SPEC READER] Successfully loaded: {title} (OpenAPI {version})")
        return self.spec

    def load_spec_from_file(self, filepath):
        """
        Loads an OpenAPI spec from a local JSON file (useful for offline/testing).

        Args:
            filepath: Path to the OpenAPI JSON file.

        Returns:
            dict: The parsed OpenAPI specification.
        """
        print(f"[SPEC READER] Loading OpenAPI spec from file: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            self.spec = json.load(f)

        title = self.spec.get("info", {}).get("title", "Unknown API")
        print(f"[SPEC READER] Successfully loaded: {title}")
        return self.spec

    def resolve_ref(self, ref_string):
        """
        Resolves a JSON $ref pointer like "#/components/schemas/User"
        to the actual schema object in the spec.

        How $ref works in OpenAPI:
          - "#/components/schemas/User" means:
            Go to the root → components → schemas → User
          - The parts after # are separated by / and form a path

        Args:
            ref_string: A $ref string like "#/components/schemas/User"

        Returns:
            dict: The resolved schema object.
        """
        if not ref_string.startswith("#/"):
            return {}

        # Split "#/components/schemas/User" → ["components", "schemas", "User"]
        parts = ref_string[2:].split("/")

        # Walk down the spec dictionary following the path
        current = self.spec
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                print(f"[SPEC READER] WARNING: Could not resolve $ref: {ref_string}")
                return {}

        return current

    def resolve_schema(self, schema):
        """
        Recursively resolves a schema, handling $ref, allOf, oneOf, anyOf.

        This is needed because OpenAPI specs often use references instead
        of inline schemas. For example:
            "schema": { "$ref": "#/components/schemas/User" }
        needs to be resolved to the actual User schema with properties.

        Args:
            schema: A schema dict that may contain $ref or composition keywords.

        Returns:
            dict: The fully resolved schema with all properties inlined.
        """
        if schema is None:
            return {}

        # If it's a $ref, resolve it first
        if "$ref" in schema:
            resolved = self.resolve_ref(schema["$ref"])
            return self.resolve_schema(resolved)

        # Handle allOf (merge all sub-schemas into one)
        if "allOf" in schema:
            merged = {}
            merged_props = {}
            merged_required = []
            for sub_schema in schema["allOf"]:
                resolved_sub = self.resolve_schema(sub_schema)
                merged_props.update(resolved_sub.get("properties", {}))
                merged_required.extend(resolved_sub.get("required", []))
                merged.update(resolved_sub)
            merged["properties"] = merged_props
            if merged_required:
                merged["required"] = merged_required
            return merged

        # Handle oneOf / anyOf — just use the first option for simplicity
        for keyword in ("oneOf", "anyOf"):
            if keyword in schema and schema[keyword]:
                return self.resolve_schema(schema[keyword][0])

        # Handle array items
        if schema.get("type") == "array" and "items" in schema:
            resolved_items = self.resolve_schema(schema["items"])
            return {**schema, "items": resolved_items}

        # Handle nested object properties
        if "properties" in schema:
            resolved_props = {}
            for prop_name, prop_schema in schema["properties"].items():
                resolved_props[prop_name] = self.resolve_schema(prop_schema)
            return {**schema, "properties": resolved_props}

        return schema

    def extract_endpoints(self):
        """
        Extracts all API endpoints from the parsed OpenAPI spec into a
        structured list that the contract generator can use.

        Returns:
            list[dict]: A list of endpoint dictionaries, each containing:
                - method: HTTP method (get, post, put, delete)
                - path: URL path (/api/users, /api/users/{id})
                - summary: Human-readable description
                - operation_id: Unique operation identifier
                - path_parameters: List of path param dicts
                - request_body_schema: Resolved schema for request body (or None)
                - responses: Dict of status_code → {description, schema}
                - tags: List of tags (e.g., ["user-controller"])
        """
        if self.spec is None:
            raise RuntimeError(
                "No spec loaded. Call fetch_spec() or load_spec_from_file() first."
            )

        endpoints = []
        paths = self.spec.get("paths", {})

        for path, path_item in paths.items():
            for method in ("get", "post", "put", "delete", "patch"):
                if method not in path_item:
                    continue

                operation = path_item[method]

                # --- Extract path parameters ---
                # These come from both the path-level and operation-level
                path_params = []
                for param in path_item.get("parameters", []) + operation.get("parameters", []):
                    if param.get("in") == "path":
                        param_schema = self.resolve_schema(param.get("schema", {}))
                        path_params.append({
                            "name": param["name"],
                            "type": param_schema.get("type", "string"),
                            "format": param_schema.get("format"),
                            "required": param.get("required", True),
                        })

                # --- Extract request body schema ---
                request_body_schema = None
                request_body = operation.get("requestBody", {})
                if request_body:
                    content = request_body.get("content", {})
                    json_content = content.get("application/json", {})
                    if "schema" in json_content:
                        request_body_schema = self.resolve_schema(json_content["schema"])

                # --- Extract response schemas ---
                responses = {}
                for status_code, response_obj in operation.get("responses", {}).items():
                    resp_schema = None
                    content = response_obj.get("content", {})
                    json_content = content.get("application/json", {})
                    if "schema" in json_content:
                        resp_schema = self.resolve_schema(json_content["schema"])

                    # Also check for */* content type (some APIs use this)
                    if resp_schema is None:
                        wildcard_content = content.get("*/*", {})
                        if "schema" in wildcard_content:
                            resp_schema = self.resolve_schema(wildcard_content["schema"])

                    responses[status_code] = {
                        "description": response_obj.get("description", ""),
                        "schema": resp_schema,
                    }

                endpoint = {
                    "method": method,
                    "path": path,
                    "summary": operation.get("summary", ""),
                    "description": operation.get("description", ""),
                    "operation_id": operation.get("operationId", ""),
                    "path_parameters": path_params,
                    "request_body_schema": request_body_schema,
                    "responses": responses,
                    "tags": operation.get("tags", []),
                }

                endpoints.append(endpoint)

        print(f"[SPEC READER] Extracted {len(endpoints)} endpoints from spec")
        for ep in endpoints:
            print(f"  {ep['method'].upper():6s} {ep['path']}")

        return endpoints
