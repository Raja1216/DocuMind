from __future__ import annotations

import json
import tempfile
import unittest

from pathlib import Path

from src.models.alignment_validation import (
    AlignmentValidationCode,
    AlignmentValidationIssue,
    AlignmentValidationReport,
    AlignmentValidationSeverity,
)
from src.utils.alignment_validation_report_writer import (
    AlignmentValidationReportWriter,
)


class AlignmentValidationReportWriterTests(
    unittest.TestCase
):

    def test_report_is_written_as_json(
        self,
    ) -> None:
        report = AlignmentValidationReport(
            page_count=2,
            paragraph_count=5,
            result_count=5,
            alignment_counts={
                "left": 3,
                "center": 2,
            },
            passed=True,
        )

        report.add_issue(
            AlignmentValidationIssue(
                page_number=1,
                paragraph_region_number=2,
                code=(
                    AlignmentValidationCode
                    .LOW_CONFIDENCE
                ),
                severity=(
                    AlignmentValidationSeverity
                    .WARNING
                ),
                message=(
                    "Alignment confidence is low."
                ),
                metrics={
                    "confidence": 0.40,
                },
            )
        )

        with tempfile.TemporaryDirectory() as temp_directory:
            output_path = (
                Path(temp_directory)
                / "alignment-report.json"
            )

            written_path = (
                AlignmentValidationReportWriter
                .write(
                    report=report,
                    output_path=output_path,
                )
            )

            self.assertTrue(
                written_path.exists()
            )

            with written_path.open(
                mode="r",
                encoding="utf-8",
            ) as report_file:
                data = json.load(
                    report_file
                )

            self.assertEqual(
                data["page_count"],
                2,
            )

            self.assertEqual(
                data["alignment_counts"],
                {
                    "left": 3,
                    "center": 2,
                },
            )

            self.assertEqual(
                data["issues"][0]["code"],
                "low_confidence",
            )

            self.assertEqual(
                data["issues"][0]["severity"],
                "warning",
            )


if __name__ == "__main__":
    unittest.main()