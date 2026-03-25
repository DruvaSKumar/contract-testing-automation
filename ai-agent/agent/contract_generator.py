# ============================================================
# contract_generator.py — Spring Cloud Contract YAML Generator
# ============================================================
# PURPOSE:
#   Takes parsed OpenAPI endpoint data (from spec_reader.py) and
#   generates Spring Cloud Contract (SCC) YAML files that can be
#   used for automated consumer-provider verification.
#
# HOW IT WORKS:
#   1. Receives a list of endpoint definitions from the spec reader
#   2. For each endpoint, generates:
#      - A descriptive YAML contract file
#      - Sample request data (URL, headers, body)
#      - Sample response data (status, body)
#      - Regex matchers for flexible validation
#   3. Writes the YAML files to the Provider's contracts directory
#
# WHY IS THIS NEEDED?
#   Manually writing contract files is tedious and error-prone.
#   This generator reads the OpenAPI spec (the machine-readable
#   source of truth) and creates contracts that MATCH the spec.
#   When the API changes, you just re-run the generator.
#
# SCC YAML FORMAT:
#   Spring Cloud Contract expects YAML files with this structure:
#     description: "Human-readable description"
#     name: "contract_name"
#     request:
#       method: GET
#       url: /api/users/1
#     response:
#       status: 200
#       headers:
#         Content-Type: application/json
#       body:
#         id: 1
#         name: "Alice Johnson"
#       matchers:
#         body:
#           - path: $.id
#             type: by_regex
#             value: "[0-9]+"
# ============================================================

import os
import re

import yaml


class ContractGenerator:
    """
    Generates Spring Cloud Contract YAML files from parsed OpenAPI
    endpoint definitions.
    """

    # ---- Sample data used when generating contract bodies ----
    # These are realistic placeholder values for common field types.
    # The SCC framework uses these values in the contract body,
    # and the matchers (regex) validate the STRUCTURE, not exact values.
    SAMPLE_STRINGS = {
        "name": "Sample User",
        "email": "sample@example.com",
        "role": "USER",
        "title": "Sample Title",
        "description": "Sample description",
        "status": "ACTIVE",
        "productName": "Sample Product",
        "username": "sampleuser",
        "firstName": "John",
        "lastName": "Doe",
        "phone": "+1-555-0100",
        "address": "123 Main Street",
    }

    # Maps HTTP method → typical success status code
    METHOD_STATUS_MAP = {
        "get": 200,
        "post": 201,
        "put": 200,
        "delete": 204,
        "patch": 200,
    }

    # Maps HTTP method → verb used in contract names
    METHOD_VERB_MAP = {
        "get": "return",
        "post": "create",
        "put": "update",
        "delete": "delete",
        "patch": "patch",
    }

    def __init__(self, output_dir=None):
        """
        Args:
            output_dir: Directory where generated YAML files will be saved.
                        Defaults to provider-api/src/test/resources/contracts/
        """
        if output_dir is None:
            # Default to the Provider's contracts directory
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(
                base, "..", "provider-api", "src", "test", "resources", "contracts"
            )
        self.output_dir = os.path.normpath(output_dir)

    def generate_all(self, endpoints, overwrite=False):
        """
        Generates SCC YAML contract files for all provided endpoints.

        Args:
            endpoints: List of endpoint dicts from OpenApiSpecReader.extract_endpoints()
            overwrite: If True, overwrite existing contract files.
                       If False (default), skip endpoints that already have contracts.

        Returns:
            dict with keys:
                - generated: list of file paths that were created
                - skipped: list of file paths that already existed (when overwrite=False)
                - errors: list of (endpoint, error_message) tuples
        """
        results = {"generated": [], "skipped": [], "errors": []}

        for endpoint in endpoints:
            try:
                file_path = self._generate_one(endpoint, overwrite)
                if file_path is None:
                    results["skipped"].append(
                        self._build_file_path(endpoint)
                    )
                else:
                    results["generated"].append(file_path)
            except Exception as e:
                results["errors"].append((endpoint, str(e)))

        # Print summary
        print(f"\n[CONTRACT GENERATOR] Generation complete:")
        print(f"  Generated: {len(results['generated'])} contracts")
        print(f"  Skipped:   {len(results['skipped'])} (already exist)")
        print(f"  Errors:    {len(results['errors'])}")

        if results["generated"]:
            print(f"\n  New contract files:")
            for path in results["generated"]:
                print(f"    + {path}")

        if results["skipped"]:
            print(f"\n  Skipped (use --overwrite to regenerate):")
            for path in results["skipped"]:
                print(f"    ~ {path}")

        if results["errors"]:
            print(f"\n  Errors:")
            for ep, err in results["errors"]:
                print(f"    ! {ep['method'].upper()} {ep['path']}: {err}")

        return results

    def _generate_one(self, endpoint, overwrite=False):
        """
        Generates a single contract YAML file for one endpoint.

        Args:
            endpoint: A single endpoint dict from the spec reader.
            overwrite: Whether to overwrite existing files.

        Returns:
            str: The file path of the generated contract, or None if skipped.
        """
        file_path = self._build_file_path(endpoint)

        # Check if file already exists
        if os.path.exists(file_path) and not overwrite:
            return None

        # Build the contract dictionary
        contract = self._build_contract(endpoint)

        # Ensure output directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write YAML with a descriptive header comment
        header = self._build_header_comment(endpoint)
        yaml_content = yaml.dump(contract, default_flow_style=False, sort_keys=False, allow_unicode=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(header)
            f.write(yaml_content)

        return file_path

    def _build_contract(self, endpoint):
        """
        Builds the contract dictionary structure for a single endpoint.

        This is the core logic — it maps OpenAPI endpoint info to the
        SCC YAML format that Spring Cloud Contract understands.
        """
        method = endpoint["method"]
        path = endpoint["path"]
        summary = endpoint.get("summary", "")

        contract_name = self._generate_contract_name(method, path, summary)

        # Build description
        description = summary if summary else f"{method.upper()} {path}"

        # Build request section
        request = self._build_request(endpoint)

        # Determine success status code
        status_code = self._get_success_status(endpoint)

        # Build response section
        response = self._build_response(endpoint, status_code)

        contract = {
            "description": description,
            "name": contract_name,
            "request": request,
            "response": response,
        }

        return contract

    def _build_request(self, endpoint):
        """Builds the 'request' section of the contract."""
        method = endpoint["method"]
        path = endpoint["path"]
        path_params = endpoint.get("path_parameters", [])
        request_body_schema = endpoint.get("request_body_schema")

        # Substitute path parameters with sample values
        # e.g., /api/users/{id} → /api/users/1
        url = self._substitute_path_params(path, path_params)

        request = {
            "method": method.upper(),
            "url": url,
        }

        # Add request body for POST, PUT, PATCH
        if method in ("post", "put", "patch") and request_body_schema:
            request["headers"] = {"Content-Type": "application/json"}
            request["body"] = self._generate_sample_body(
                request_body_schema, exclude_id=True
            )

        return request

    def _build_response(self, endpoint, status_code):
        """Builds the 'response' section of the contract."""
        method = endpoint["method"]
        responses = endpoint.get("responses", {})

        response = {"status": status_code}

        # DELETE with 204 has no body
        if status_code == 204:
            return response

        # Get the response schema for this status code
        resp_info = responses.get(str(status_code), {})
        resp_schema = resp_info.get("schema")

        if resp_schema:
            response["headers"] = {"Content-Type": "application/json"}
            response["body"] = self._generate_sample_body(resp_schema, exclude_id=False)

            # Generate matchers for response body validation
            matchers = self._generate_matchers(resp_schema)
            if matchers:
                response["matchers"] = {"body": matchers}

        return response

    def _generate_sample_body(self, schema, exclude_id=False):
        """
        Generates a sample JSON body from an OpenAPI schema.

        This creates realistic placeholder values that will be used
        in the contract body. The actual validation happens via matchers.

        Args:
            schema: Resolved OpenAPI schema dict.
            exclude_id: If True, skip the 'id' field (for request bodies
                        where ID is auto-generated by the server).

        Returns:
            dict or list: Sample body matching the schema.
        """
        schema_type = schema.get("type", "object")

        # Array → generate a list with one sample item
        if schema_type == "array":
            items_schema = schema.get("items", {})
            sample_item = self._generate_sample_body(items_schema, exclude_id)
            return [sample_item]

        # Object → generate each property
        if schema_type == "object" or "properties" in schema:
            body = {}
            properties = schema.get("properties", {})

            for prop_name, prop_schema in properties.items():
                # Skip 'id' in request bodies (it's auto-generated)
                if exclude_id and prop_name.lower() == "id":
                    continue

                body[prop_name] = self._generate_sample_value(prop_name, prop_schema)

            return body

        # Primitive → return a single sample value
        return self._generate_sample_value("value", schema)

    def _generate_sample_value(self, field_name, schema):
        """
        Generates a single sample value for a schema field.

        Uses the field name and schema type/format/constraints to pick
        a realistic value. For example:
          - "email" field with format:"email" → "sample@example.com"
          - "id" field with type:"integer" → 1
          - "name" field with type:"string" → "Sample User"

        Args:
            field_name: The name of the field (used for smart defaults).
            schema: The OpenAPI schema for this field.

        Returns:
            A sample value (str, int, float, bool, dict, or list).
        """
        # Check for enum values — use the first one
        if "enum" in schema:
            return schema["enum"][0]

        # Check for example value in the spec
        if "example" in schema:
            return schema["example"]

        schema_type = schema.get("type", "string")
        schema_format = schema.get("format", "")

        # Integer types
        if schema_type == "integer":
            if field_name.lower() in ("id", "userid", "user_id"):
                return 1
            if field_name.lower() in ("quantity", "count", "amount"):
                return 1
            return 1

        # Number types (float/double)
        if schema_type == "number":
            if field_name.lower() in ("price", "amount", "cost"):
                return 29.99
            return 1.0

        # Boolean
        if schema_type == "boolean":
            return True

        # String types — use format and field name for smart defaults
        if schema_type == "string":
            # Format-based defaults
            if schema_format == "email" or "email" in field_name.lower():
                return "sample@example.com"
            if schema_format == "date-time":
                return "2026-01-15T10:30:00Z"
            if schema_format == "date":
                return "2026-01-15"
            if schema_format == "uri" or schema_format == "url":
                return "https://example.com"
            if schema_format == "uuid":
                return "550e8400-e29b-41d4-a716-446655440000"

            # Field-name-based defaults
            field_lower = field_name.lower()
            if field_lower in self.SAMPLE_STRINGS:
                return self.SAMPLE_STRINGS[field_lower]

            # Fallback: generic sample string
            return f"Sample {field_name}"

        # Array
        if schema_type == "array":
            items = schema.get("items", {})
            return [self._generate_sample_value(field_name, items)]

        # Object
        if schema_type == "object" or "properties" in schema:
            return self._generate_sample_body(schema, exclude_id=False)

        return "sample_value"

    def _generate_matchers(self, schema, prefix="$"):
        """
        Generates SCC response body matchers from a schema.

        Matchers use JSON Path and regex to validate response structure
        without checking exact values. This makes contracts resilient
        to data changes while still enforcing field existence and types.

        For example, instead of asserting name == "Alice Johnson",
        we assert that name matches ".+" (any non-empty string).

        Args:
            schema: Resolved OpenAPI schema.
            prefix: JSON Path prefix (starts with "$").

        Returns:
            list[dict]: List of matcher dicts with path, type, value.
        """
        matchers = []
        schema_type = schema.get("type", "object")

        # Array — generate matchers for the first item's properties
        if schema_type == "array":
            items_schema = schema.get("items", {})
            if "properties" in items_schema:
                for prop_name, prop_schema in items_schema["properties"].items():
                    matcher = self._create_matcher(
                        f"{prefix}[0].{prop_name}", prop_schema
                    )
                    if matcher:
                        matchers.append(matcher)
            return matchers

        # Object — generate a matcher for each property
        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                matcher = self._create_matcher(f"{prefix}.{prop_name}", prop_schema)
                if matcher:
                    matchers.append(matcher)

        return matchers

    def _create_matcher(self, json_path, schema):
        """
        Creates a single matcher dict for one field.

        Args:
            json_path: JSON Path expression (e.g., "$.name", "$.id")
            schema: The field's OpenAPI schema.

        Returns:
            dict: A matcher dict like:
                  {"path": "$.id", "type": "by_regex", "value": "[0-9]+"}
                  or None if no matcher is needed.
        """
        schema_type = schema.get("type", "string")
        schema_format = schema.get("format", "")
        field_name = json_path.split(".")[-1].rstrip("]")

        # Enum → match any of the enum values
        if "enum" in schema:
            enum_regex = "(" + "|".join(str(v) for v in schema["enum"]) + ")"
            return {"path": json_path, "type": "by_regex", "value": enum_regex}

        # Integer
        if schema_type == "integer":
            return {"path": json_path, "type": "by_regex", "value": "[0-9]+"}

        # Number (float/double)
        if schema_type == "number":
            return {"path": json_path, "type": "by_regex", "value": "[0-9]+\\.?[0-9]*"}

        # Boolean
        if schema_type == "boolean":
            return {"path": json_path, "type": "by_regex", "value": "(true|false)"}

        # String types
        if schema_type == "string":
            if schema_format == "email" or "email" in field_name.lower():
                return {
                    "path": json_path,
                    "type": "by_regex",
                    "value": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}",
                }
            if schema_format == "date-time":
                return {"path": json_path, "type": "by_regex", "value": ".+"}
            if schema_format == "date":
                return {
                    "path": json_path,
                    "type": "by_regex",
                    "value": "[0-9]{4}-[0-9]{2}-[0-9]{2}",
                }
            if schema_format == "uuid":
                return {
                    "path": json_path,
                    "type": "by_regex",
                    "value": "[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
                }

            # Generic non-empty string
            return {"path": json_path, "type": "by_regex", "value": ".+"}

        return None

    def _generate_contract_name(self, method, path, summary=""):
        """
        Generates a human-readable contract name and file name.

        Examples:
            GET  /api/users      → "should_return_all_users"
            GET  /api/users/{id} → "should_return_user_by_id"
            POST /api/users      → "should_create_a_new_user"
            PUT  /api/users/{id} → "should_update_user_by_id"
            DELETE /api/users/{id} → "should_delete_user_by_id"

        Args:
            method: HTTP method (get, post, put, delete)
            path: URL path (/api/users, /api/users/{id})
            summary: Optional operation summary from OpenAPI spec.

        Returns:
            str: Contract name like "should_return_user_by_id"
        """
        verb = self.METHOD_VERB_MAP.get(method, method)

        # Extract the resource name from the path
        # /api/users → "users", /api/users/{id} → "users"
        parts = [p for p in path.split("/") if p and not p.startswith("{") and p != "api"]
        resource = parts[-1] if parts else "resource"

        # Singularize simple cases: "users" → "user"
        resource_singular = resource.rstrip("s") if resource.endswith("s") else resource

        # Check if path has a parameter (like {id})
        has_param = bool(re.search(r"\{(\w+)\}", path))
        param_match = re.search(r"\{(\w+)\}", path)
        param_name = param_match.group(1) if param_match else ""

        # Build the contract name
        if method == "get" and not has_param:
            name = f"should_{verb}_all_{resource}"
        elif method == "get" and has_param:
            name = f"should_{verb}_{resource_singular}_by_{param_name}"
        elif method == "post":
            name = f"should_{verb}_a_new_{resource_singular}"
        elif method == "put" and has_param:
            name = f"should_{verb}_{resource_singular}_by_{param_name}"
        elif method == "delete" and has_param:
            name = f"should_{verb}_{resource_singular}_by_{param_name}"
        else:
            # Fallback: use method + resource
            name = f"should_{verb}_{resource_singular}"

        return name

    def _build_file_path(self, endpoint):
        """Builds the output file path for a contract."""
        method = endpoint["method"]
        path = endpoint["path"]
        summary = endpoint.get("summary", "")

        contract_name = self._generate_contract_name(method, path, summary)

        # Determine subdirectory from the path (more reliable than tags)
        # /api/users → "user", /api/orders → "order"
        parts = [p for p in path.split("/") if p and not p.startswith("{") and p != "api"]
        if parts:
            # Use the first path segment and singularize: "users" → "user"
            resource = parts[0]
            subdir = resource.rstrip("s") if resource.endswith("s") else resource
        else:
            subdir = "general"

        return os.path.join(self.output_dir, subdir, f"{contract_name}.yml")

    def _substitute_path_params(self, path, path_params):
        """
        Replaces path parameter placeholders with sample values.

        Example: /api/users/{id} → /api/users/1

        Args:
            path: URL path with {param} placeholders.
            path_params: List of parameter dicts from spec reader.

        Returns:
            str: URL with placeholders replaced by sample values.
        """
        url = path
        for param in path_params:
            placeholder = "{" + param["name"] + "}"
            param_type = param.get("type", "string")

            if param_type in ("integer", "number"):
                sample = "1"
            else:
                sample = "sample"

            url = url.replace(placeholder, sample)

        # Also replace any remaining {param} not in the param list
        url = re.sub(r"\{(\w+)\}", "1", url)

        return url

    def _get_success_status(self, endpoint):
        """
        Determines the success status code for an endpoint.

        Checks the OpenAPI responses first, falls back to method defaults.
        """
        method = endpoint["method"]
        responses = endpoint.get("responses", {})

        # Prefer explicit success codes from the spec
        for code in ("200", "201", "204"):
            if code in responses:
                return int(code)

        # Fall back to method-based defaults
        return self.METHOD_STATUS_MAP.get(method, 200)

    def _build_header_comment(self, endpoint):
        """Builds a descriptive YAML comment header for the contract file."""
        method = endpoint["method"].upper()
        path = endpoint["path"]
        summary = endpoint.get("summary", "")
        name = self._generate_contract_name(
            endpoint["method"], path, summary
        )

        lines = [
            "# ============================================================",
            f"# Contract: {name}.yml",
            "# ============================================================",
            f"# AUTO-GENERATED by AI Agent from OpenAPI specification",
            f"# Endpoint: {method} {path}",
        ]
        if summary:
            lines.append(f"# Summary:  {summary}")
        lines.extend([
            "#",
            "# This contract was generated from the Provider's OpenAPI spec.",
            "# It defines the expected request/response pair for this endpoint.",
            "# Matchers use regex to validate response structure (not exact values).",
            "#",
            "# To regenerate: python main.py generate --overwrite",
            "# ============================================================",
            "",
        ])
        return "\n".join(lines) + "\n"
