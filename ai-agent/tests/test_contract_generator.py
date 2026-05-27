# ============================================================
# test_contract_generator.py — Unit Tests for Contract Generator
# ============================================================

import os
import pytest
import yaml

from agent.contract_generator import ContractGenerator


class TestContractGenerator:
    """Tests for the ContractGenerator module."""

    # ---- Initialization Tests ----

    def test_init_custom_dir(self, contracts_dir):
        """Should accept a custom output directory."""
        gen = ContractGenerator(output_dir=contracts_dir)
        assert gen.output_dir == os.path.normpath(contracts_dir)

    # ---- generate_all Tests ----

    def test_generate_all_creates_files(self, contracts_dir, sample_endpoints):
        """Should generate YAML files for all endpoints."""
        gen = ContractGenerator(output_dir=contracts_dir)
        results = gen.generate_all(sample_endpoints, overwrite=True)

        assert len(results["generated"]) > 0
        assert len(results["errors"]) == 0

    def test_generate_all_skips_existing(self, contracts_dir, sample_endpoints):
        """Should skip existing contracts when overwrite=False."""
        gen = ContractGenerator(output_dir=contracts_dir)

        # Generate once
        gen.generate_all(sample_endpoints, overwrite=True)

        # Generate again without overwrite
        results = gen.generate_all(sample_endpoints, overwrite=False)
        assert len(results["skipped"]) > 0
        assert len(results["generated"]) == 0

    def test_generate_all_overwrites_existing(self, contracts_dir, sample_endpoints):
        """Should overwrite existing contracts when overwrite=True."""
        gen = ContractGenerator(output_dir=contracts_dir)

        # Generate twice with overwrite
        gen.generate_all(sample_endpoints, overwrite=True)
        results = gen.generate_all(sample_endpoints, overwrite=True)

        assert len(results["generated"]) > 0
        assert len(results["skipped"]) == 0

    def test_generated_contract_is_valid_yaml(self, contracts_dir, sample_endpoints):
        """Should produce valid YAML files."""
        gen = ContractGenerator(output_dir=contracts_dir)
        results = gen.generate_all(sample_endpoints, overwrite=True)

        for filepath in results["generated"]:
            with open(filepath, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
            assert content is not None

    def test_generated_contract_has_required_fields(self, contracts_dir, sample_endpoints):
        """Generated contracts should have request and response sections."""
        gen = ContractGenerator(output_dir=contracts_dir)
        results = gen.generate_all(sample_endpoints, overwrite=True)

        for filepath in results["generated"]:
            with open(filepath, "r", encoding="utf-8") as f:
                contract = yaml.safe_load(f)

            assert "request" in contract, f"Missing 'request' in {filepath}"
            assert "response" in contract, f"Missing 'response' in {filepath}"
            assert "method" in contract["request"]
            assert "status" in contract["response"]

    def test_generated_contract_correct_method(self, contracts_dir, sample_endpoints):
        """Generated contracts should map methods correctly."""
        gen = ContractGenerator(output_dir=contracts_dir)
        results = gen.generate_all(sample_endpoints, overwrite=True)

        # Check that each contract has a valid HTTP method
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH"}
        for filepath in results["generated"]:
            with open(filepath, "r", encoding="utf-8") as f:
                contract = yaml.safe_load(f)
            assert contract["request"]["method"] in valid_methods

    def test_generated_contract_correct_status_code(self, contracts_dir, sample_endpoints):
        """Generated contracts should have appropriate status codes."""
        gen = ContractGenerator(output_dir=contracts_dir)
        results = gen.generate_all(sample_endpoints, overwrite=True)

        for filepath in results["generated"]:
            with open(filepath, "r", encoding="utf-8") as f:
                contract = yaml.safe_load(f)
            status = contract["response"]["status"]
            assert 100 <= status <= 599, f"Invalid status {status} in {filepath}"

    def test_post_contract_has_request_body(self, contracts_dir, sample_endpoints):
        """POST contracts should include a request body."""
        gen = ContractGenerator(output_dir=contracts_dir)
        results = gen.generate_all(sample_endpoints, overwrite=True)

        for filepath in results["generated"]:
            with open(filepath, "r", encoding="utf-8") as f:
                contract = yaml.safe_load(f)
            if contract["request"]["method"] == "POST":
                assert "body" in contract["request"], \
                    f"POST contract missing body: {filepath}"

    def test_get_contract_has_no_request_body(self, contracts_dir, sample_endpoints):
        """GET contracts should not include a request body."""
        gen = ContractGenerator(output_dir=contracts_dir)
        results = gen.generate_all(sample_endpoints, overwrite=True)

        for filepath in results["generated"]:
            with open(filepath, "r", encoding="utf-8") as f:
                contract = yaml.safe_load(f)
            if contract["request"]["method"] == "GET":
                assert "body" not in contract["request"], \
                    f"GET contract should not have body: {filepath}"

    def test_delete_contract_returns_204(self, contracts_dir, sample_endpoints):
        """DELETE contracts should return 204 No Content."""
        gen = ContractGenerator(output_dir=contracts_dir)
        results = gen.generate_all(sample_endpoints, overwrite=True)

        for filepath in results["generated"]:
            with open(filepath, "r", encoding="utf-8") as f:
                contract = yaml.safe_load(f)
            if contract["request"]["method"] == "DELETE":
                assert contract["response"]["status"] == 204

    def test_generated_has_name_field(self, contracts_dir, sample_endpoints):
        """Each contract should have a descriptive name field."""
        gen = ContractGenerator(output_dir=contracts_dir)
        results = gen.generate_all(sample_endpoints, overwrite=True)

        for filepath in results["generated"]:
            with open(filepath, "r", encoding="utf-8") as f:
                contract = yaml.safe_load(f)
            assert "name" in contract
            assert len(contract["name"]) > 0

    def test_creates_subdirectory_by_tag(self, contracts_dir, sample_endpoints):
        """Should organize contracts into tag-based subdirectories."""
        gen = ContractGenerator(output_dir=contracts_dir)
        gen.generate_all(sample_endpoints, overwrite=True)

        # Should have created a subdirectory (e.g., "user" from "user-controller" tag)
        subdirs = [
            d for d in os.listdir(contracts_dir)
            if os.path.isdir(os.path.join(contracts_dir, d))
        ]
        assert len(subdirs) > 0
