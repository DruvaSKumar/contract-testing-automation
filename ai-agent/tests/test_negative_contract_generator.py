# ============================================================
# test_negative_contract_generator.py — Unit Tests for Negative Contracts
# ============================================================

import os
import pytest
import yaml

from agent.negative_contract_generator import NegativeContractGenerator


class TestNegativeContractGenerator:
    """Tests for the NegativeContractGenerator module."""

    # ---- Initialization ----

    def test_init_custom_dir(self, contracts_dir):
        """Should accept a custom output directory."""
        gen = NegativeContractGenerator(output_dir=contracts_dir)
        assert gen.output_dir == os.path.normpath(contracts_dir)

    # ---- generate_all Tests ----

    def test_generate_negative_contracts(self, contracts_dir, sample_endpoints):
        """Should generate negative (error case) contracts."""
        gen = NegativeContractGenerator(output_dir=contracts_dir)
        results = gen.generate_all(sample_endpoints, overwrite=True)

        assert len(results["generated"]) > 0
        assert len(results["errors"]) == 0

    def test_negative_contracts_have_error_status(self, contracts_dir, sample_endpoints):
        """Negative contracts should have 4xx status codes."""
        gen = NegativeContractGenerator(output_dir=contracts_dir)
        results = gen.generate_all(sample_endpoints, overwrite=True)

        for filepath in results["generated"]:
            with open(filepath, "r", encoding="utf-8") as f:
                contract = yaml.safe_load(f)
            status = contract["response"]["status"]
            assert 400 <= status <= 499, \
                f"Expected 4xx status, got {status} in {filepath}"

    def test_negative_contracts_are_valid_yaml(self, contracts_dir, sample_endpoints):
        """Negative contracts should be valid YAML."""
        gen = NegativeContractGenerator(output_dir=contracts_dir)
        results = gen.generate_all(sample_endpoints, overwrite=True)

        for filepath in results["generated"]:
            with open(filepath, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
            assert content is not None
            assert "request" in content
            assert "response" in content

    def test_negative_contracts_include_validation_errors(self, contracts_dir, sample_endpoints):
        """Should generate contracts for invalid request bodies (400)."""
        gen = NegativeContractGenerator(output_dir=contracts_dir)
        results = gen.generate_all(sample_endpoints, overwrite=True)

        # At least one 400 contract for POST (invalid body)
        has_400 = False
        for filepath in results["generated"]:
            with open(filepath, "r", encoding="utf-8") as f:
                contract = yaml.safe_load(f)
            if contract["response"]["status"] == 400:
                has_400 = True
                break
        assert has_400, "Expected at least one 400 Bad Request contract"

    def test_negative_contracts_include_not_found(self, contracts_dir, sample_endpoints):
        """Should generate 404 contracts for GET/PUT/DELETE with {id}."""
        gen = NegativeContractGenerator(output_dir=contracts_dir)
        results = gen.generate_all(sample_endpoints, overwrite=True)

        has_404 = False
        for filepath in results["generated"]:
            with open(filepath, "r", encoding="utf-8") as f:
                contract = yaml.safe_load(f)
            if contract["response"]["status"] == 404:
                has_404 = True
                break
        assert has_404, "Expected at least one 404 Not Found contract"

    def test_skips_existing_when_no_overwrite(self, contracts_dir, sample_endpoints):
        """Should skip existing negative contracts when overwrite=False."""
        gen = NegativeContractGenerator(output_dir=contracts_dir)

        # Generate once
        gen.generate_all(sample_endpoints, overwrite=True)

        # Generate again without overwrite
        results = gen.generate_all(sample_endpoints, overwrite=False)
        assert len(results["skipped"]) > 0
        assert len(results["generated"]) == 0
