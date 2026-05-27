# ============================================================
# test_backward_compatibility.py — Unit Tests for Backward Compat
# ============================================================

import pytest

from agent.backward_compatibility import BackwardCompatibilityChecker, BreakingChange


class TestBackwardCompatibilityChecker:
    """Tests for the BackwardCompatibilityChecker module."""

    @pytest.fixture
    def checker(self):
        return BackwardCompatibilityChecker()

    @pytest.fixture
    def base_spec(self, sample_spec):
        """A baseline spec (the 'old' version)."""
        return sample_spec

    @pytest.fixture
    def compatible_spec(self, sample_spec):
        """A new spec with only non-breaking additions."""
        spec = sample_spec.copy()
        import copy
        spec = copy.deepcopy(sample_spec)
        # Add a new optional field (non-breaking)
        spec["components"]["schemas"]["User"]["properties"]["phone"] = {
            "type": "string",
            "description": "Phone number (optional)",
        }
        return spec

    @pytest.fixture
    def breaking_spec_removed_endpoint(self, sample_spec):
        """A new spec with a removed endpoint (BREAKING)."""
        import copy
        spec = copy.deepcopy(sample_spec)
        # Remove DELETE endpoint
        del spec["paths"]["/api/users/{id}"]["delete"]
        return spec

    @pytest.fixture
    def breaking_spec_removed_field(self, sample_spec):
        """A new spec with a removed response field (BREAKING)."""
        import copy
        spec = copy.deepcopy(sample_spec)
        # Remove 'email' field from User schema
        del spec["components"]["schemas"]["User"]["properties"]["email"]
        return spec

    # ---- Compatibility Check Tests ----

    def test_no_changes_compatible(self, checker, base_spec):
        """Identical specs should be fully compatible."""
        result = checker.check_compatibility(base_spec, base_spec)

        assert result["is_compatible"] is True
        assert len(result["breaking"]) == 0

    def test_new_optional_field_compatible(self, checker, base_spec, compatible_spec):
        """Adding an optional field should not be breaking."""
        result = checker.check_compatibility(base_spec, compatible_spec)

        assert len(result["breaking"]) == 0

    def test_removed_endpoint_is_breaking(self, checker, base_spec, breaking_spec_removed_endpoint):
        """Removing an endpoint should be a breaking change."""
        result = checker.check_compatibility(base_spec, breaking_spec_removed_endpoint)

        assert len(result["breaking"]) >= 1
        assert result["is_compatible"] is False

    def test_removed_field_is_breaking(self, checker, base_spec, breaking_spec_removed_field):
        """Removing a response field should be a breaking change."""
        result = checker.check_compatibility(base_spec, breaking_spec_removed_field)

        assert len(result["breaking"]) >= 1
        assert result["is_compatible"] is False

    def test_new_endpoint_is_info(self, checker, base_spec):
        """Adding a new endpoint should be info/safe."""
        import copy
        new_spec = copy.deepcopy(base_spec)
        new_spec["paths"]["/api/health"] = {
            "get": {
                "summary": "Health check",
                "responses": {"200": {"description": "OK"}},
            }
        }

        result = checker.check_compatibility(base_spec, new_spec)

        assert len(result["breaking"]) == 0
        assert result["is_compatible"] is True

    def test_result_is_dict(self, checker, base_spec):
        """check_compatibility should return a dict."""
        result = checker.check_compatibility(base_spec, base_spec)
        assert isinstance(result, dict)
        assert "breaking" in result
        assert "warnings" in result
        assert "is_compatible" in result

    # ---- BreakingChange Model Tests ----

    def test_breaking_change_repr(self):
        """BreakingChange should have a readable repr."""
        change = BreakingChange(
            severity="breaking",
            category="removed_endpoint",
            message="DELETE /api/users/{id} was removed",
            path="/api/users/{id}",
        )
        rep = repr(change)
        assert "BREAKING" in rep
        assert "removed" in rep.lower()

    def test_breaking_change_fields(self):
        """BreakingChange should store all fields."""
        change = BreakingChange(
            severity="warning",
            category="new_optional_field",
            message="New field 'phone' added",
            path="/api/users",
            detail={"field": "phone", "type": "string"},
        )
        assert change.severity == "warning"
        assert change.category == "new_optional_field"
        assert change.path == "/api/users"
        assert change.detail["field"] == "phone"
