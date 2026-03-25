# ============================================================
# report_generator.py — Contract Report & Remediation Generator
# ============================================================
# PURPOSE:
#   Generates human-readable reports of contract generation results
#   and drift detection findings, complete with actionable
#   remediation suggestions.
#
# WHAT IT REPORTS:
#   - Contract generation summary (what was created, what was skipped)
#   - Drift detection summary (uncovered, orphaned, drifted, covered)
#   - Contract coverage percentage
#   - Health status (HEALTHY, WARNING, CRITICAL)
#   - Specific remediation steps for each issue found
#
# WHY IS THIS NEEDED?
#   Raw data from the generator and drift detector isn't very
#   readable. The report generator formats it into clear, actionable
#   output that developers can quickly act on. In CI/CD pipelines,
#   these reports help teams understand what needs fixing.
# ============================================================

import os
from datetime import datetime, timezone


class ReportGenerator:
    """
    Generates formatted reports for contract generation results
    and drift detection findings.
    """

    # ---- Separator lines for visual structure ----
    SEPARATOR = "=" * 65
    THIN_SEP = "-" * 65

    def generate_generation_report(self, generation_results):
        """
        Generates a report for contract generation results.

        Args:
            generation_results: Dict from ContractGenerator.generate_all()
                                with keys: generated, skipped, errors

        Returns:
            str: Formatted report string.
        """
        lines = []
        lines.append("")
        lines.append(self.SEPARATOR)
        lines.append("  CONTRACT GENERATION REPORT")
        lines.append(f"  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append(self.SEPARATOR)

        generated = generation_results.get("generated", [])
        skipped = generation_results.get("skipped", [])
        errors = generation_results.get("errors", [])

        # Summary counts
        lines.append("")
        lines.append(f"  Total Generated:  {len(generated)}")
        lines.append(f"  Total Skipped:    {len(skipped)}")
        lines.append(f"  Total Errors:     {len(errors)}")
        lines.append("")

        # Generated files
        if generated:
            lines.append(self.THIN_SEP)
            lines.append("  NEW CONTRACTS CREATED:")
            lines.append(self.THIN_SEP)
            for path in generated:
                filename = os.path.basename(path)
                lines.append(f"    [+] {filename}")
                lines.append(f"        {path}")
            lines.append("")

        # Skipped files
        if skipped:
            lines.append(self.THIN_SEP)
            lines.append("  SKIPPED (already exist):")
            lines.append(self.THIN_SEP)
            for path in skipped:
                filename = os.path.basename(path)
                lines.append(f"    [~] {filename}")
            lines.append("")
            lines.append("  TIP: Use --overwrite flag to regenerate existing contracts.")
            lines.append("")

        # Errors
        if errors:
            lines.append(self.THIN_SEP)
            lines.append("  ERRORS:")
            lines.append(self.THIN_SEP)
            for endpoint, error in errors:
                method = endpoint.get("method", "?").upper()
                path = endpoint.get("path", "?")
                lines.append(f"    [!] {method} {path}")
                lines.append(f"        Error: {error}")
            lines.append("")

        lines.append(self.SEPARATOR)

        # Next steps
        if generated:
            lines.append("")
            lines.append("  NEXT STEPS:")
            lines.append("  1. Review the generated contract files")
            lines.append("  2. Run Provider contract tests: cd provider-api && mvn clean install")
            lines.append("  3. Run Consumer contract tests: cd consumer-api && mvn clean test")
            lines.append("  4. If tests fail, adjust sample values in the contracts")
            lines.append("")

        return "\n".join(lines)

    def generate_drift_report(self, drift_results):
        """
        Generates a detailed report of drift detection findings.

        Args:
            drift_results: Dict from DriftDetector.detect_drift()
                           with keys: uncovered, orphaned, drifted, covered, summary

        Returns:
            str: Formatted report string.
        """
        lines = []
        summary = drift_results.get("summary", {})
        uncovered = drift_results.get("uncovered", [])
        orphaned = drift_results.get("orphaned", [])
        drifted = drift_results.get("drifted", [])
        covered = drift_results.get("covered", [])

        # Header
        lines.append("")
        lines.append(self.SEPARATOR)
        lines.append("  CONTRACT DRIFT DETECTION REPORT")
        lines.append(f"  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append(self.SEPARATOR)

        # Health status with visual indicator
        health = summary.get("health", "UNKNOWN")
        health_icon = {"HEALTHY": "[OK]", "WARNING": "[!!]", "CRITICAL": "[XX]"}.get(
            health, "[??]"
        )
        lines.append("")
        lines.append(f"  Health Status: {health_icon} {health}")
        lines.append("")

        # Summary table
        lines.append(self.THIN_SEP)
        lines.append("  SUMMARY")
        lines.append(self.THIN_SEP)
        lines.append(f"  API Endpoints (from spec):   {summary.get('total_spec_endpoints', 0)}")
        lines.append(f"  Existing Contracts:          {summary.get('total_contracts', 0)}")
        lines.append(f"  Covered (matching):          {summary.get('covered_count', 0)}")
        lines.append(f"  Uncovered (no contract):     {summary.get('uncovered_count', 0)}")
        lines.append(f"  Orphaned (no endpoint):      {summary.get('orphaned_count', 0)}")
        lines.append(f"  Drifted (schema mismatch):   {summary.get('drifted_count', 0)}")
        lines.append(f"  Coverage:                    {summary.get('coverage_percent', 0)}%")
        lines.append("")

        # Coverage bar
        coverage = summary.get("coverage_percent", 0)
        bar_filled = int(coverage / 5)  # 20 chars = 100%
        bar_empty = 20 - bar_filled
        bar = "#" * bar_filled + "." * bar_empty
        lines.append(f"  Coverage: [{bar}] {coverage}%")
        lines.append("")

        # Covered endpoints
        if covered:
            lines.append(self.THIN_SEP)
            lines.append("  COVERED ENDPOINTS (contracts match spec):")
            lines.append(self.THIN_SEP)
            for item in covered:
                lines.append(f"    [OK] {item['method']:6s} {item['url']}")
                lines.append(f"         Contract: {item['file']}")
            lines.append("")

        # Uncovered endpoints
        if uncovered:
            lines.append(self.THIN_SEP)
            lines.append("  UNCOVERED ENDPOINTS (need contracts):")
            lines.append(self.THIN_SEP)
            for item in uncovered:
                lines.append(f"    [!!] {item['method'].upper():6s} {item['path']}")
                if item.get("summary"):
                    lines.append(f"         {item['summary']}")
                lines.append(f"         Reason: {item['reason']}")
            lines.append("")
            lines.append("  REMEDIATION: Run 'python main.py generate' to create contracts")
            lines.append("               for uncovered endpoints.")
            lines.append("")

        # Orphaned contracts
        if orphaned:
            lines.append(self.THIN_SEP)
            lines.append("  ORPHANED CONTRACTS (endpoint no longer exists):")
            lines.append(self.THIN_SEP)
            for item in orphaned:
                lines.append(f"    [!!] {item['method']:6s} {item['url']}")
                lines.append(f"         File: {item['file']}")
                lines.append(f"         Reason: {item['reason']}")
            lines.append("")
            lines.append("  REMEDIATION: Review and delete orphaned contract files,")
            lines.append("               or restore the missing API endpoints.")
            lines.append("")

        # Drifted contracts
        if drifted:
            lines.append(self.THIN_SEP)
            lines.append("  DRIFTED CONTRACTS (schema mismatch detected):")
            lines.append(self.THIN_SEP)
            for item in drifted:
                lines.append(f"    [XX] {item['method']:6s} {item['url']}")
                lines.append(f"         File: {item['file']}")
                for issue in item.get("issues", []):
                    lines.append(f"         - {issue}")
            lines.append("")
            lines.append("  REMEDIATION: Run 'python main.py generate --overwrite' to")
            lines.append("               regenerate drifted contracts from the current spec.")
            lines.append("               Then re-run contract tests to verify.")
            lines.append("")

        # Overall recommendation
        lines.append(self.SEPARATOR)
        lines.append("  RECOMMENDATION")
        lines.append(self.SEPARATOR)

        if health == "HEALTHY":
            lines.append("")
            lines.append("  All contracts are in sync with the API spec.")
            lines.append("  No action needed. Keep monitoring for future drift.")
        elif health == "WARNING":
            lines.append("")
            lines.append("  Some issues detected but contracts are mostly in sync.")
            lines.append("  Review the findings above and address uncovered/orphaned items.")
        else:
            lines.append("")
            lines.append("  CRITICAL issues detected! Contracts are significantly out of sync.")
            lines.append("  Immediate action required:")
            lines.append("  1. Run: python main.py generate --overwrite")
            lines.append("  2. Review generated contracts")
            lines.append("  3. Run: cd provider-api && mvn clean install")
            lines.append("  4. Run: cd consumer-api && mvn clean test")
            lines.append("  5. Fix any remaining test failures")

        lines.append("")
        lines.append(self.SEPARATOR)
        lines.append("")

        return "\n".join(lines)

    def save_report(self, report_text, output_path):
        """
        Saves a report to a file.

        Args:
            report_text: The formatted report string.
            output_path: Path to save the report file.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"[REPORT] Saved report to: {output_path}")
