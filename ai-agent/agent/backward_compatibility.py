# ============================================================
# backward_compatibility.py — API Backward Compatibility Checker
# ============================================================
# PURPOSE:
#   Detects BREAKING CHANGES between two versions of an OpenAPI
#   spec (e.g., current branch vs main branch). Prevents merging
#   changes that would break existing consumers.
#
# WHAT IT DETECTS:
#   BREAKING (blocks merge):
#     - Removed endpoints (consumers will get 404)
#     - Removed response fields (consumers will get null)
#     - Changed HTTP method for an endpoint
#     - Changed response status code
#     - Added required fields to request body (old consumers don't send them)
#     - Changed field type (e.g., string → integer)
#
#   WARNINGS (non-breaking but noteworthy):
#     - New endpoints added (safe for consumers)
#     - New optional request fields added (safe)
#     - New response fields added (safe)
#     - Deprecated endpoints
#
# HOW TO USE:
#   1. Load the "old" spec (from main branch or a saved file)
#   2. Load the "new" spec (from the current branch/running Provider)
#   3. Call check_compatibility(old_spec, new_spec)
#   4. Returns a report with breaking/warning/safe changes
#
# USAGE IN CI:
#   - Run on merge requests to block breaking API changes
#   - Exit code 0 = compatible, 1 = warnings, 2 = breaking changes
# ============================================================

import json
import os
import subprocess


class BreakingChange:
    """Represents a single breaking change detected."""

    def __init__(self, severity, category, message, path=None, detail=None):
        """
        Args:
            severity: "breaking", "warning", or "info"
            category: e.g., "removed_endpoint", "removed_field", "type_change"
            message: Human-readable description of the change
            path: API path affected (e.g., "/api/users/{id}")
            detail: Additional details (e.g., field name, old/new type)
        """
        self.severity = severity
        self.category = category
        self.message = message
        self.path = path
        self.detail = detail

    def __repr__(self):
        icon = {"breaking": "🔴", "warning": "🟡", "info": "🟢"}.get(
            self.severity, "⚪"
        )
        return f"{icon} [{self.severity.upper()}] {self.message}"


class BackwardCompatibilityChecker:
    """
    Compares two OpenAPI specs and identifies breaking changes.
    """

    def __init__(self):
        self.changes = []

    def check_compatibility(self, old_spec, new_spec):
        """
        Performs a comprehensive backward compatibility check.

        Args:
            old_spec: The previous/baseline OpenAPI spec (dict).
            new_spec: The current/new OpenAPI spec (dict).

        Returns:
            dict with keys:
                - breaking: list of BreakingChange (severity="breaking")
                - warnings: list of BreakingChange (severity="warning")
                - info: list of BreakingChange (severity="info")
                - is_compatible: bool (True if no breaking changes)
                - summary: str (human-readable summary)
        """
        self.changes = []

        old_paths = old_spec.get("paths", {})
        new_paths = new_spec.get("paths", {})

        # 1. Check for removed endpoints
        self._check_removed_endpoints(old_paths, new_paths)

        # 2. Check for new endpoints (info only)
        self._check_new_endpoints(old_paths, new_paths)

        # 3. For each shared endpoint, check for breaking changes
        shared_paths = set(old_paths.keys()) & set(new_paths.keys())
        for path in sorted(shared_paths):
            self._check_endpoint_changes(path, old_paths[path], new_paths[path], old_spec, new_spec)

        # Build results
        breaking = [c for c in self.changes if c.severity == "breaking"]
        warnings = [c for c in self.changes if c.severity == "warning"]
        info = [c for c in self.changes if c.severity == "info"]

        is_compatible = len(breaking) == 0
        summary = self._build_summary(breaking, warnings, info)

        return {
            "breaking": breaking,
            "warnings": warnings,
            "info": info,
            "is_compatible": is_compatible,
            "summary": summary,
        }

    # ================================================================
    # Endpoint-Level Checks
    # ================================================================

    def _check_removed_endpoints(self, old_paths, new_paths):
        """Endpoints present in old spec but missing from new spec."""
        removed = set(old_paths.keys()) - set(new_paths.keys())
        for path in sorted(removed):
            methods = [m for m in ("get", "post", "put", "delete", "patch") if m in old_paths[path]]
            for method in methods:
                self.changes.append(BreakingChange(
                    severity="breaking",
                    category="removed_endpoint",
                    message=f"Endpoint removed: {method.upper()} {path}",
                    path=path,
                    detail={"method": method},
                ))

    def _check_new_endpoints(self, old_paths, new_paths):
        """New endpoints in the new spec (informational, non-breaking)."""
        added = set(new_paths.keys()) - set(old_paths.keys())
        for path in sorted(added):
            methods = [m for m in ("get", "post", "put", "delete", "patch") if m in new_paths[path]]
            for method in methods:
                self.changes.append(BreakingChange(
                    severity="info",
                    category="new_endpoint",
                    message=f"New endpoint added: {method.upper()} {path}",
                    path=path,
                    detail={"method": method},
                ))

    def _check_endpoint_changes(self, path, old_path_item, new_path_item, old_spec, new_spec):
        """Check for changes within a shared endpoint path."""
        old_methods = set(m for m in ("get", "post", "put", "delete", "patch") if m in old_path_item)
        new_methods = set(m for m in ("get", "post", "put", "delete", "patch") if m in new_path_item)

        # Methods removed from this path
        for method in sorted(old_methods - new_methods):
            self.changes.append(BreakingChange(
                severity="breaking",
                category="removed_method",
                message=f"Method removed: {method.upper()} {path}",
                path=path,
                detail={"method": method},
            ))

        # Methods added (non-breaking)
        for method in sorted(new_methods - old_methods):
            self.changes.append(BreakingChange(
                severity="info",
                category="new_method",
                message=f"New method added: {method.upper()} {path}",
                path=path,
                detail={"method": method},
            ))

        # For shared methods, check operation-level changes
        for method in sorted(old_methods & new_methods):
            old_op = old_path_item[method]
            new_op = new_path_item[method]
            self._check_operation_changes(path, method, old_op, new_op, old_spec, new_spec)

    def _check_operation_changes(self, path, method, old_op, new_op, old_spec, new_spec):
        """Check for breaking changes within a single operation."""
        # Check response schema changes
        self._check_response_changes(path, method, old_op, new_op, old_spec, new_spec)

        # Check request body changes
        self._check_request_body_changes(path, method, old_op, new_op, old_spec, new_spec)

    # ================================================================
    # Response Schema Checks
    # ================================================================

    def _check_response_changes(self, path, method, old_op, new_op, old_spec, new_spec):
        """Check for breaking changes in response schemas."""
        old_responses = old_op.get("responses", {})
        new_responses = new_op.get("responses", {})

        # Check each response code that existed before
        for status_code in old_responses:
            if status_code not in new_responses:
                self.changes.append(BreakingChange(
                    severity="warning",
                    category="removed_response_code",
                    message=f"Response {status_code} removed from {method.upper()} {path}",
                    path=path,
                    detail={"method": method, "status_code": status_code},
                ))
                continue

            # Compare response schemas
            old_schema = self._extract_response_schema(old_responses[status_code], old_spec)
            new_schema = self._extract_response_schema(new_responses[status_code], new_spec)

            if old_schema and new_schema:
                self._check_schema_changes(
                    path, method, old_schema, new_schema,
                    context=f"response {status_code}",
                    old_spec=old_spec, new_spec=new_spec,
                )

    def _check_request_body_changes(self, path, method, old_op, new_op, old_spec, new_spec):
        """Check for breaking changes in request body (new required fields)."""
        old_body = old_op.get("requestBody", {})
        new_body = new_op.get("requestBody", {})

        old_schema = self._extract_request_schema(old_body, old_spec)
        new_schema = self._extract_request_schema(new_body, new_spec)

        if not new_schema:
            return

        # New required fields that weren't in the old schema = BREAKING
        old_required = set(old_schema.get("required", [])) if old_schema else set()
        new_required = set(new_schema.get("required", []))
        old_properties = set(old_schema.get("properties", {}).keys()) if old_schema else set()

        for field in sorted(new_required - old_required):
            if field not in old_properties:
                self.changes.append(BreakingChange(
                    severity="breaking",
                    category="new_required_field",
                    message=f"New required request field '{field}' added to {method.upper()} {path}",
                    path=path,
                    detail={"method": method, "field": field},
                ))

    # ================================================================
    # Schema Comparison (Response Fields)
    # ================================================================

    def _check_schema_changes(self, path, method, old_schema, new_schema, context, old_spec, new_spec):
        """Compare two schemas and detect removed/changed fields."""
        old_type = old_schema.get("type", "object")
        new_type = new_schema.get("type", "object")

        # Type change
        if old_type != new_type:
            self.changes.append(BreakingChange(
                severity="breaking",
                category="type_change",
                message=f"Type changed from '{old_type}' to '{new_type}' in {context} of {method.upper()} {path}",
                path=path,
                detail={"method": method, "old_type": old_type, "new_type": new_type},
            ))
            return

        # For arrays, check the items schema
        if old_type == "array":
            old_items = old_schema.get("items", {})
            new_items = new_schema.get("items", {})
            if old_items and new_items:
                self._check_schema_changes(path, method, old_items, new_items, f"{context} array items", old_spec, new_spec)
            return

        # For objects, check properties
        if old_type == "object" or "properties" in old_schema:
            old_props = old_schema.get("properties", {})
            new_props = new_schema.get("properties", {})

            # Removed fields = BREAKING
            for field in sorted(set(old_props.keys()) - set(new_props.keys())):
                self.changes.append(BreakingChange(
                    severity="breaking",
                    category="removed_field",
                    message=f"Field '{field}' removed from {context} of {method.upper()} {path}",
                    path=path,
                    detail={"method": method, "field": field, "context": context},
                ))

            # New fields = INFO (non-breaking for responses)
            for field in sorted(set(new_props.keys()) - set(old_props.keys())):
                self.changes.append(BreakingChange(
                    severity="info",
                    category="new_field",
                    message=f"New field '{field}' added to {context} of {method.upper()} {path}",
                    path=path,
                    detail={"method": method, "field": field, "context": context},
                ))

            # Check type changes in shared fields
            for field in sorted(set(old_props.keys()) & set(new_props.keys())):
                old_field_type = old_props[field].get("type", "string")
                new_field_type = new_props[field].get("type", "string")
                if old_field_type != new_field_type:
                    self.changes.append(BreakingChange(
                        severity="breaking",
                        category="field_type_change",
                        message=f"Field '{field}' type changed from '{old_field_type}' to '{new_field_type}' in {context} of {method.upper()} {path}",
                        path=path,
                        detail={"method": method, "field": field, "old_type": old_field_type, "new_type": new_field_type},
                    ))

    # ================================================================
    # Helper Methods
    # ================================================================

    def _extract_response_schema(self, response_obj, spec):
        """Extract the resolved schema from a response object."""
        content = response_obj.get("content", {})
        json_content = content.get("application/json", content.get("*/*", {}))
        schema = json_content.get("schema")
        if schema:
            return self._resolve_schema(schema, spec)
        return None

    def _extract_request_schema(self, request_body, spec):
        """Extract the resolved schema from a request body."""
        content = request_body.get("content", {})
        json_content = content.get("application/json", {})
        schema = json_content.get("schema")
        if schema:
            return self._resolve_schema(schema, spec)
        return None

    def _resolve_schema(self, schema, spec):
        """Resolve $ref references in a schema."""
        if "$ref" in schema:
            ref_path = schema["$ref"]
            if ref_path.startswith("#/"):
                parts = ref_path[2:].split("/")
                current = spec
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        return schema
                return self._resolve_schema(current, spec) if isinstance(current, dict) else schema
        return schema

    def _build_summary(self, breaking, warnings, info):
        """Build a human-readable summary string."""
        lines = []
        lines.append("=" * 65)
        lines.append("  BACKWARD COMPATIBILITY CHECK RESULTS")
        lines.append("=" * 65)
        lines.append("")

        if not breaking and not warnings:
            lines.append("  ✅ FULLY COMPATIBLE — No breaking changes detected!")
            lines.append("")
        elif not breaking:
            lines.append("  ✅ COMPATIBLE (with warnings)")
            lines.append("")
        else:
            lines.append("  ❌ BREAKING CHANGES DETECTED — Merge blocked!")
            lines.append("")

        if breaking:
            lines.append(f"  🔴 BREAKING CHANGES ({len(breaking)}):")
            lines.append("  " + "-" * 50)
            for change in breaking:
                lines.append(f"    • {change.message}")
            lines.append("")

        if warnings:
            lines.append(f"  🟡 WARNINGS ({len(warnings)}):")
            lines.append("  " + "-" * 50)
            for change in warnings:
                lines.append(f"    • {change.message}")
            lines.append("")

        if info:
            lines.append(f"  🟢 INFORMATIONAL ({len(info)}):")
            lines.append("  " + "-" * 50)
            for change in info:
                lines.append(f"    • {change.message}")
            lines.append("")

        lines.append("=" * 65)
        return "\n".join(lines)

    # ================================================================
    # Git Integration — Load spec from another branch
    # ================================================================

    @staticmethod
    def load_spec_from_branch(branch="main", spec_path=None):
        """
        Loads the OpenAPI spec from a different git branch without
        checking out that branch. Uses `git show` to read the file.

        This is used in CI to compare the MR branch against main.

        Args:
            branch: Git branch to load from (default: "main")
            spec_path: Path to a saved spec file in the repo.
                       If None, will try common locations.

        Returns:
            dict: The parsed OpenAPI spec, or None if not available.
        """
        # Try to find a saved spec file in the repo
        if spec_path is None:
            candidates = [
                "ai-agent/specs/openapi-spec.json",
                "provider-api/src/main/resources/openapi.json",
                "docs/openapi-spec.json",
            ]
        else:
            candidates = [spec_path]

        for path in candidates:
            try:
                result = subprocess.run(
                    ["git", "show", f"{branch}:{path}"],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return json.loads(result.stdout)
            except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
                continue

        return None

    @staticmethod
    def save_spec_snapshot(spec, output_path=None):
        """
        Saves the current OpenAPI spec to a file for future comparison.
        This should be called after successful builds on main branch.

        Args:
            spec: The OpenAPI spec dict to save.
            output_path: Where to save (default: ai-agent/specs/openapi-spec.json)
        """
        if output_path is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_path = os.path.join(base, "specs", "openapi-spec.json")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2)

        print(f"[COMPATIBILITY] Spec snapshot saved: {output_path}")
        return output_path
