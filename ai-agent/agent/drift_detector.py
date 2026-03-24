# ============================================================
# drift_detector.py — Contract Drift Detector
# ============================================================
# PURPOSE:
#   Compares existing contract YAML files against the current
#   OpenAPI spec to detect "drift" — situations where the API
#   has changed but the contracts haven't been updated.
#
# WHAT IS CONTRACT DRIFT?
#   Drift happens when:
#   - A new endpoint is added to the API but no contract exists
#   - An endpoint is removed from the API but the contract remains
#   - An endpoint's request/response schema changes (fields added,
#     removed, or type changed) but the contract is outdated
#
# WHY IS THIS IMPORTANT?
#   Contract drift is dangerous because:
#   - Stale contracts give a FALSE sense of safety
#   - New endpoints are untested
#   - Schema changes may break consumers silently
#   The drift detector catches these issues BEFORE they reach production.
#
# HOW IT WORKS:
#   1. Reads all existing contract YAML files from the contracts directory
#   2. Reads the current API spec from the spec reader
#   3. Compares them to find:
#      - UNCOVERED: Endpoints in the spec with no contract
#      - ORPHANED:  Contracts with no matching endpoint in the spec
#      - DRIFTED:   Contracts where the schema has changed
#   4. Returns a structured report of all drift findings
# ============================================================

import os
import re

import yaml


class DriftDetector:
    """
    Detects drift between existing contract files and the current
    OpenAPI specification.
    """

    def __init__(self, contracts_dir=None):
        """
        Args:
            contracts_dir: Directory containing existing contract YAML files.
                           Defaults to provider-api/src/test/resources/contracts/
        """
        if contracts_dir is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            contracts_dir = os.path.join(
                base, "..", "provider-api", "src", "test", "resources", "contracts"
            )
        self.contracts_dir = os.path.normpath(contracts_dir)

    def load_existing_contracts(self):
        """
        Loads all existing contract YAML files from the contracts directory.

        Returns:
            list[dict]: A list of dicts, each containing:
                - file_path: Path to the YAML file
                - file_name: Just the filename
                - contract: The parsed YAML content
                - method: HTTP method from the contract
                - url: URL from the contract
        """
        contracts = []

        if not os.path.exists(self.contracts_dir):
            print(f"[DRIFT DETECTOR] Contracts directory not found: {self.contracts_dir}")
            return contracts

        for root, _dirs, files in os.walk(self.contracts_dir):
            for filename in sorted(files):
                if not filename.endswith((".yml", ".yaml")):
                    continue

                file_path = os.path.join(root, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = yaml.safe_load(f)

                    if content and "request" in content:
                        request = content["request"]
                        contracts.append({
                            "file_path": file_path,
                            "file_name": filename,
                            "contract": content,
                            "method": request.get("method", "").upper(),
                            "url": request.get("url", ""),
                        })
                except Exception as e:
                    print(f"[DRIFT DETECTOR] WARNING: Could not parse {file_path}: {e}")

        print(f"[DRIFT DETECTOR] Loaded {len(contracts)} existing contracts")
        return contracts

    def detect_drift(self, spec_endpoints):
        """
        Compares existing contracts against the current OpenAPI spec
        to detect drift.

        Args:
            spec_endpoints: List of endpoint dicts from OpenApiSpecReader.extract_endpoints()

        Returns:
            dict: Drift report with keys:
                - uncovered: Endpoints in spec with no matching contract
                - orphaned:  Contracts with no matching endpoint in spec
                - drifted:   Contracts with schema mismatches
                - covered:   Endpoints with valid contracts (no drift)
                - summary:   Human-readable summary statistics
        """
        existing_contracts = self.load_existing_contracts()

        uncovered = []
        orphaned = []
        drifted = []
        covered = []

        # Build a set of (METHOD, normalized_url_pattern) from contracts
        contract_lookup = {}
        for contract_info in existing_contracts:
            key = self._normalize_endpoint_key(
                contract_info["method"],
                contract_info["url"]
            )
            contract_lookup[key] = contract_info

        # Build a set of (METHOD, url_pattern) from spec
        spec_lookup = {}
        for endpoint in spec_endpoints:
            key = self._normalize_endpoint_key(
                endpoint["method"].upper(),
                endpoint["path"]
            )
            spec_lookup[key] = endpoint

        # --- Find UNCOVERED endpoints (in spec but no contract) ---
        for key, endpoint in spec_lookup.items():
            if key not in contract_lookup:
                uncovered.append({
                    "method": endpoint["method"].upper(),
                    "path": endpoint["path"],
                    "summary": endpoint.get("summary", ""),
                    "reason": "No contract exists for this endpoint",
                })

        # --- Find ORPHANED contracts (contract exists but not in spec) ---
        for key, contract_info in contract_lookup.items():
            if key not in spec_lookup:
                orphaned.append({
                    "method": contract_info["method"],
                    "url": contract_info["url"],
                    "file": contract_info["file_name"],
                    "file_path": contract_info["file_path"],
                    "reason": "Endpoint no longer exists in API spec",
                })

        # --- Find DRIFTED contracts (both exist but schema mismatch) ---
        for key in set(contract_lookup.keys()) & set(spec_lookup.keys()):
            contract_info = contract_lookup[key]
            endpoint = spec_lookup[key]

            drift_issues = self._check_schema_drift(contract_info, endpoint)
            if drift_issues:
                drifted.append({
                    "method": contract_info["method"],
                    "url": contract_info["url"],
                    "file": contract_info["file_name"],
                    "file_path": contract_info["file_path"],
                    "issues": drift_issues,
                })
            else:
                covered.append({
                    "method": contract_info["method"],
                    "url": contract_info["url"],
                    "file": contract_info["file_name"],
                })

        # Build summary
        total_spec = len(spec_lookup)
        total_contracts = len(contract_lookup)
        summary = {
            "total_spec_endpoints": total_spec,
            "total_contracts": total_contracts,
            "covered_count": len(covered),
            "uncovered_count": len(uncovered),
            "orphaned_count": len(orphaned),
            "drifted_count": len(drifted),
            "coverage_percent": round(
                (len(covered) / total_spec * 100) if total_spec > 0 else 0, 1
            ),
            "health": self._calculate_health(
                len(covered), len(uncovered), len(orphaned), len(drifted)
            ),
        }

        return {
            "uncovered": uncovered,
            "orphaned": orphaned,
            "drifted": drifted,
            "covered": covered,
            "summary": summary,
        }

    def _check_schema_drift(self, contract_info, endpoint):
        """
        Checks if a contract's response body fields match the current
        API spec's response schema.

        This compares the fields in the contract's response body against
        the properties defined in the OpenAPI schema.

        Returns:
            list[str]: List of drift issue descriptions, or empty if no drift.
        """
        issues = []
        contract = contract_info["contract"]
        contract_response = contract.get("response", {})
        contract_body = contract_response.get("body")

        # Get the expected response schema from the spec
        responses = endpoint.get("responses", {})

        # Find the matching success response
        contract_status = str(contract_response.get("status", "200"))
        spec_response = responses.get(contract_status, {})
        spec_schema = spec_response.get("schema")

        # If the contract has a body but spec has no schema (or vice versa)
        if contract_body and not spec_schema:
            issues.append(
                f"Contract has response body but spec has no schema for status {contract_status}"
            )
            return issues

        if not contract_body:
            # No body to compare — skip schema checks
            return issues

        if not spec_schema:
            return issues

        # Compare fields
        spec_properties = spec_schema.get("properties", {})

        # Handle array responses — check the first item
        if spec_schema.get("type") == "array":
            items_schema = spec_schema.get("items", {})
            spec_properties = items_schema.get("properties", {})
            # Use first item from contract body if it's a list
            if isinstance(contract_body, list) and contract_body:
                contract_body = contract_body[0]

        if spec_properties and isinstance(contract_body, dict):
            contract_fields = set(contract_body.keys())
            spec_fields = set(spec_properties.keys())

            # Fields in spec but missing from contract
            missing_in_contract = spec_fields - contract_fields
            for field in missing_in_contract:
                issues.append(f"Field '{field}' is in API spec but missing from contract")

            # Fields in contract but not in spec (possible removed field)
            extra_in_contract = contract_fields - spec_fields
            for field in extra_in_contract:
                issues.append(f"Field '{field}' is in contract but not in API spec")

        return issues

    def _normalize_endpoint_key(self, method, url_or_path):
        """
        Creates a normalized key for matching contracts to spec endpoints.

        Contracts use concrete URLs (/api/users/1) while specs use
        templates (/api/users/{id}). This normalizes both to a
        comparable format.

        Examples:
            ("GET", "/api/users/1")     → ("GET", "/api/users/{param}")
            ("GET", "/api/users/{id}")  → ("GET", "/api/users/{param}")
        """
        method = method.upper()

        # Replace path params: {id} → {param}, and concrete IDs → {param}
        # First handle spec-style: {id}, {userId}, etc.
        normalized = re.sub(r"\{[^}]+\}", "{param}", url_or_path)

        # Then handle contract-style concrete values: /api/users/1 → /api/users/{param}
        # Only replace trailing numeric segments (not things like /v3/)
        parts = normalized.split("/")
        normalized_parts = []
        for i, part in enumerate(parts):
            # Replace purely numeric segments that are after an API resource name
            if part.isdigit() and i > 0 and not parts[i - 1].startswith("v"):
                normalized_parts.append("{param}")
            else:
                normalized_parts.append(part)
        normalized = "/".join(normalized_parts)

        return (method, normalized)

    def _calculate_health(self, covered, uncovered, orphaned, drifted):
        """
        Calculates an overall health status.

        Returns:
            str: "HEALTHY", "WARNING", or "CRITICAL"
        """
        if uncovered == 0 and orphaned == 0 and drifted == 0:
            return "HEALTHY"
        if drifted > 0 or uncovered > covered:
            return "CRITICAL"
        return "WARNING"
