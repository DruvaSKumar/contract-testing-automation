# ============================================================
# negative_contract_generator.py — Negative/Error Contract Generator
# ============================================================
# PURPOSE:
#   Generates SCC YAML contracts for ERROR scenarios (400, 404, etc.)
#   that complement the happy-path contracts from contract_generator.py.
#
# WHY IS THIS NEEDED?
#   Happy-path contracts only test successful responses (200, 201, 204).
#   But most production bugs hide in error handling:
#     - Missing validation (invalid data accepted)
#     - Wrong status codes (500 instead of 400)
#     - Inconsistent error response format
#     - Missing fields in error body
#
#   Negative contracts catch these by verifying:
#     - 404 when requesting non-existent resources
#     - 400 when sending invalid/missing fields
#     - Correct error response body structure
#
# HOW IT WORKS:
#   For each endpoint, generates scenario-specific error contracts:
#     GET  /api/users/{id}  → 404 (non-existent ID)
#     POST /api/users       → 400 (missing required fields)
#     POST /api/users       → 400 (invalid email format)
#     PUT  /api/users/{id}  → 404 (non-existent ID)
#     PUT  /api/users/{id}  → 400 (invalid body)
#     DELETE /api/users/{id} → 404 (non-existent ID)
# ============================================================

import os
import re

import yaml


class NegativeContractGenerator:
    """
    Generates Spring Cloud Contract YAML files for error/negative scenarios.
    Produces contracts that verify proper error handling (400, 404, etc.).
    """

    # Non-existent ID used in 404 tests — must not match pre-loaded test data
    NON_EXISTENT_ID = "999"

    def __init__(self, output_dir=None):
        """
        Args:
            output_dir: Directory where generated YAML files will be saved.
                        Defaults to provider-api/src/test/resources/contracts/
        """
        if output_dir is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(
                base, "..", "provider-api", "src", "test", "resources", "contracts"
            )
        self.output_dir = os.path.normpath(output_dir)

    def generate_all(self, endpoints, overwrite=False):
        """
        Generates negative contract YAML files for all applicable endpoints.

        Args:
            endpoints: List of endpoint dicts from OpenApiSpecReader.
            overwrite: If True, overwrite existing files.

        Returns:
            dict with keys: generated, skipped, errors
        """
        results = {"generated": [], "skipped": [], "errors": []}

        for endpoint in endpoints:
            try:
                scenarios = self._determine_scenarios(endpoint)
                for scenario in scenarios:
                    file_path = self._generate_one(endpoint, scenario, overwrite)
                    if file_path is None:
                        results["skipped"].append(
                            self._build_file_path(endpoint, scenario)
                        )
                    else:
                        results["generated"].append(file_path)
            except Exception as e:
                results["errors"].append((endpoint, str(e)))

        # Print summary
        print(f"\n[NEGATIVE CONTRACTS] Generation complete:")
        print(f"  Generated: {len(results['generated'])} negative contracts")
        print(f"  Skipped:   {len(results['skipped'])} (already exist)")
        print(f"  Errors:    {len(results['errors'])}")

        if results["generated"]:
            print(f"\n  New negative contract files:")
            for path in results["generated"]:
                print(f"    + {path}")

        return results

    def _determine_scenarios(self, endpoint):
        """
        Determines which negative test scenarios apply to an endpoint.

        Returns:
            list[dict]: Scenario definitions with type, status, description.
        """
        method = endpoint["method"]
        path = endpoint["path"]
        has_path_param = bool(re.search(r"\{(\w+)\}", path))
        has_request_body = endpoint.get("request_body_schema") is not None
        scenarios = []

        # --- 404 Not Found: endpoints with path parameters ---
        if has_path_param and method in ("get", "put", "delete"):
            scenarios.append({
                "type": "not_found",
                "status": 404,
                "description": f"should return 404 when resource not found",
            })

        # --- 400 Bad Request: endpoints with request bodies ---
        if has_request_body and method in ("post", "put", "patch"):
            # Scenario: empty/missing required fields
            scenarios.append({
                "type": "missing_fields",
                "status": 400,
                "description": f"should return 400 when required fields are missing",
            })

            # Scenario: invalid email format (if email field exists)
            schema = endpoint.get("request_body_schema", {})
            properties = schema.get("properties", {})
            if "email" in properties:
                scenarios.append({
                    "type": "invalid_email",
                    "status": 400,
                    "description": f"should return 400 when email format is invalid",
                })

        return scenarios

    def _generate_one(self, endpoint, scenario, overwrite=False):
        """Generates a single negative contract YAML file."""
        file_path = self._build_file_path(endpoint, scenario)

        if os.path.exists(file_path) and not overwrite:
            return None

        contract = self._build_contract(endpoint, scenario)

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        header = self._build_header_comment(endpoint, scenario)
        yaml_content = yaml.dump(
            contract, default_flow_style=False, sort_keys=False, allow_unicode=True
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(header)
            f.write(yaml_content)

        return file_path

    def _build_contract(self, endpoint, scenario):
        """Builds the contract dictionary for a negative scenario."""
        scenario_type = scenario["type"]

        if scenario_type == "not_found":
            return self._build_not_found_contract(endpoint)
        elif scenario_type == "missing_fields":
            return self._build_missing_fields_contract(endpoint)
        elif scenario_type == "invalid_email":
            return self._build_invalid_email_contract(endpoint)

        raise ValueError(f"Unknown scenario type: {scenario_type}")

    # ================================================================
    # 404 Not Found Contracts
    # ================================================================

    def _build_not_found_contract(self, endpoint):
        """
        Builds a 404 contract for requesting a non-existent resource.
        E.g., GET /api/users/999 → 404
        """
        method = endpoint["method"]
        path = endpoint["path"]

        # Replace path params with non-existent ID
        url = re.sub(r"\{(\w+)\}", self.NON_EXISTENT_ID, path)

        contract_name = self._generate_negative_name(method, path, "not_found")

        request = {"method": method.upper(), "url": url}

        # PUT/PATCH with non-existent ID still needs a valid body
        if method in ("put", "patch"):
            request["headers"] = {"Content-Type": "application/json"}
            request["body"] = self._build_valid_body(endpoint)

        response = {
            "status": 404,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "status": 404,
                "message": f"User not found with id: {self.NON_EXISTENT_ID}",
                "timestamp": "2026-01-15T10:30:00",
                "fieldErrors": None,
            },
            "matchers": {
                "body": [
                    {"path": "$.status", "type": "by_regex", "value": "404"},
                    {"path": "$.message", "type": "by_regex", "value": ".+"},
                    {"path": "$.timestamp", "type": "by_regex", "value": ".+"},
                ]
            },
        }

        return {
            "description": f"Returns 404 when {self._resource_name(path)} not found",
            "name": contract_name,
            "request": request,
            "response": response,
        }

    # ================================================================
    # 400 Bad Request — Missing Fields
    # ================================================================

    def _build_missing_fields_contract(self, endpoint):
        """
        Builds a 400 contract for sending an empty/invalid request body.
        E.g., POST /api/users with {} → 400
        """
        method = endpoint["method"]
        path = endpoint["path"]

        url = re.sub(r"\{(\w+)\}", "1", path)

        contract_name = self._generate_negative_name(method, path, "missing_fields")

        # Send empty body — all required fields missing
        request = {
            "method": method.upper(),
            "url": url,
            "headers": {"Content-Type": "application/json"},
            "body": {},
        }

        response = {
            "status": 400,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "status": 400,
                "message": "Validation failed: please check the field errors for details",
                "timestamp": "2026-01-15T10:30:00",
                "fieldErrors": {
                    "name": "Name is required and cannot be blank",
                },
            },
            "matchers": {
                "body": [
                    {"path": "$.status", "type": "by_regex", "value": "400"},
                    {"path": "$.message", "type": "by_regex", "value": ".+"},
                    {"path": "$.timestamp", "type": "by_regex", "value": ".+"},
                ]
            },
        }

        return {
            "description": f"Returns 400 when required fields are missing",
            "name": contract_name,
            "request": request,
            "response": response,
        }

    # ================================================================
    # 400 Bad Request — Invalid Email
    # ================================================================

    def _build_invalid_email_contract(self, endpoint):
        """
        Builds a 400 contract for sending an invalid email format.
        E.g., POST /api/users with {"email": "not-an-email"} → 400
        """
        method = endpoint["method"]
        path = endpoint["path"]

        url = re.sub(r"\{(\w+)\}", "1", path)

        contract_name = self._generate_negative_name(method, path, "invalid_email")

        # Send body with valid fields EXCEPT email is malformed
        body = self._build_valid_body(endpoint)
        body["email"] = "not-a-valid-email"

        request = {
            "method": method.upper(),
            "url": url,
            "headers": {"Content-Type": "application/json"},
            "body": body,
        }

        response = {
            "status": 400,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "status": 400,
                "message": "Validation failed: please check the field errors for details",
                "timestamp": "2026-01-15T10:30:00",
                "fieldErrors": {
                    "email": "Email must be a valid email address",
                },
            },
            "matchers": {
                "body": [
                    {"path": "$.status", "type": "by_regex", "value": "400"},
                    {"path": "$.message", "type": "by_regex", "value": ".+"},
                    {"path": "$.timestamp", "type": "by_regex", "value": ".+"},
                ]
            },
        }

        return {
            "description": f"Returns 400 when email format is invalid",
            "name": contract_name,
            "request": request,
            "response": response,
        }

    # ================================================================
    # Helper Methods
    # ================================================================

    def _build_valid_body(self, endpoint):
        """
        Builds a valid request body (used as base for PUT 404 scenarios
        where the body itself is valid but the ID doesn't exist).
        """
        schema = endpoint.get("request_body_schema", {})
        properties = schema.get("properties", {})
        body = {}

        for prop_name, prop_schema in properties.items():
            if prop_name.lower() == "id":
                continue  # Skip ID in request bodies

            prop_type = prop_schema.get("type", "string")
            prop_format = prop_schema.get("format", "")

            if prop_type == "integer":
                body[prop_name] = 1
            elif prop_type == "number":
                body[prop_name] = 29.99
            elif prop_type == "boolean":
                body[prop_name] = True
            elif prop_format == "email" or "email" in prop_name.lower():
                body[prop_name] = "test@example.com"
            elif prop_name.lower() == "name":
                body[prop_name] = "Test User"
            elif prop_name.lower() == "role":
                body[prop_name] = "USER"
            else:
                body[prop_name] = f"Sample {prop_name}"

        return body

    def _generate_negative_name(self, method, path, scenario_type):
        """Generates a descriptive contract name for negative scenarios."""
        parts = [p for p in path.split("/") if p and not p.startswith("{") and p != "api"]
        resource = parts[-1] if parts else "resource"
        resource_singular = resource.rstrip("s") if resource.endswith("s") else resource

        has_param = bool(re.search(r"\{(\w+)\}", path))

        # Include method to avoid filename collisions (GET/PUT/DELETE all have 404)
        method_verb = {
            "get": "getting", "put": "updating", "delete": "deleting",
            "post": "creating", "patch": "patching"
        }.get(method, method)

        if scenario_type == "not_found":
            return f"should_return_404_when_{method_verb}_{resource_singular}_not_found"
        elif scenario_type == "missing_fields":
            return f"should_return_400_when_{method_verb}_{resource_singular}_with_missing_fields"
        elif scenario_type == "invalid_email":
            return f"should_return_400_when_{method_verb}_{resource_singular}_with_invalid_email"

        return f"should_return_error_for_{method}_{resource_singular}"

    def _build_file_path(self, endpoint, scenario):
        """Builds the output file path for a negative contract."""
        method = endpoint["method"]
        path = endpoint["path"]
        contract_name = self._generate_negative_name(method, path, scenario["type"])

        parts = [p for p in path.split("/") if p and not p.startswith("{") and p != "api"]
        if parts:
            resource = parts[0]
            subdir = resource.rstrip("s") if resource.endswith("s") else resource
        else:
            subdir = "general"

        return os.path.join(self.output_dir, subdir, f"{contract_name}.yml")

    def _resource_name(self, path):
        """Extracts a human-readable resource name from a path."""
        parts = [p for p in path.split("/") if p and not p.startswith("{") and p != "api"]
        resource = parts[-1] if parts else "resource"
        return resource.rstrip("s") if resource.endswith("s") else resource

    def _build_header_comment(self, endpoint, scenario):
        """Builds a descriptive YAML comment header."""
        method = endpoint["method"].upper()
        path = endpoint["path"]
        contract_name = self._generate_negative_name(
            endpoint["method"], path, scenario["type"]
        )

        lines = [
            "# ============================================================",
            f"# Contract: {contract_name}.yml",
            "# ============================================================",
            f"# AUTO-GENERATED by AI Agent — NEGATIVE/ERROR scenario",
            f"# Endpoint: {method} {path}",
            f"# Scenario: {scenario['description']}",
            "#",
            "# This contract verifies proper error handling.",
            "# It ensures the Provider returns correct status codes and",
            "# a consistent error response body when things go wrong.",
            "#",
            "# To regenerate: python main.py generate --overwrite",
            "# ============================================================",
            "",
        ]
        return "\n".join(lines) + "\n"
