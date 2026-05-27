# ============================================================
# test_ci_config_generator.py — Unit Tests for CI Config Generator
# ============================================================

import os
import pytest
import yaml

from agent.ci_config_generator import CIConfigGenerator


class TestCIConfigGenerator:
    """Tests for the CIConfigGenerator module."""

    @pytest.fixture
    def project_root(self, tmp_path):
        """Create a minimal project structure for the generator."""
        # Create provider-api/pom.xml
        provider_dir = tmp_path / "provider-api"
        provider_dir.mkdir()
        (provider_dir / "pom.xml").write_text("<project/>")

        # Create consumer-api/pom.xml
        consumer_dir = tmp_path / "consumer-api"
        consumer_dir.mkdir()
        (consumer_dir / "pom.xml").write_text("<project/>")

        # Create ai-agent/main.py
        agent_dir = tmp_path / "ai-agent"
        agent_dir.mkdir()
        (agent_dir / "main.py").write_text("# main")

        return str(tmp_path)

    @pytest.fixture
    def generator(self, project_root):
        return CIConfigGenerator(project_root=project_root)

    @pytest.fixture
    def output_path(self, tmp_path):
        return str(tmp_path / ".gitlab-ci.yml")

    # ---- detect_project_structure Tests ----

    def test_detect_project_structure(self, generator):
        """Should detect provider, consumer, and ai-agent."""
        structure = generator.detect_project_structure()
        assert structure["has_provider"] is True
        assert structure["has_consumer"] is True
        assert structure["has_ai_agent"] is True

    # ---- generate Tests ----

    def test_generate_creates_file(self, generator, output_path):
        """Should create a .gitlab-ci.yml file."""
        generator.generate(output_path=output_path)
        assert os.path.exists(output_path)

    def test_generate_valid_yaml(self, generator, output_path):
        """Generated config should be valid YAML."""
        generator.generate(output_path=output_path)

        with open(output_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        assert content is not None

    def test_generate_has_stages(self, generator, output_path):
        """Generated config should define pipeline stages."""
        generator.generate(output_path=output_path)

        with open(output_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        assert "stages" in content
        assert len(content["stages"]) >= 4

    def test_generate_has_provider_build_job(self, generator, output_path):
        """Generated config should have a provider build job."""
        generator.generate(output_path=output_path)

        with open(output_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        assert "provider-build" in content

    def test_generate_has_test_jobs(self, generator, output_path):
        """Generated config should have contract test jobs."""
        generator.generate(output_path=output_path)

        with open(output_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        # Should have at least provider and consumer test jobs
        job_names = list(content.keys())
        assert any("provider" in j and "test" in j for j in job_names)
        assert any("consumer" in j and "test" in j for j in job_names)

    def test_generate_has_deploy_stage(self, generator, output_path):
        """Generated config should include a deploy stage."""
        generator.generate(output_path=output_path)

        with open(output_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        assert "deploy" in content["stages"]

    def test_generate_returns_content(self, generator, output_path):
        """generate() should return the YAML content string."""
        result = generator.generate(output_path=output_path)
        assert isinstance(result, str)
        assert "stages" in result
