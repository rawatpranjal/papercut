"""Tests for table extraction."""

import pytest

from papercut.core.tables import ExtractedTable


class TestExtractedTable:
    """Tests for ExtractedTable dataclass."""

    def test_to_csv_basic(self):
        """Should convert table to CSV format."""
        table = ExtractedTable(
            page=0,
            data=[
                ["Name", "Value"],
                ["Alice", "100"],
                ["Bob", "200"],
            ],
        )

        csv_output = table.to_csv()

        assert "Name,Value" in csv_output
        assert "Alice,100" in csv_output
        assert "Bob,200" in csv_output

    def test_to_csv_handles_none_values(self):
        """Should handle None values in cells."""
        table = ExtractedTable(
            page=0,
            data=[
                ["Name", "Value"],
                ["Alice", None],
            ],
        )

        csv_output = table.to_csv()

        # None should become empty string
        assert "Alice," in csv_output

    def test_to_json_includes_metadata(self):
        """Should include page and size in JSON."""
        table = ExtractedTable(
            page=5,
            data=[
                ["A", "B"],
                ["1", "2"],
            ],
        )

        json_output = table.to_json()

        assert '"page": 5' in json_output
        assert '"rows": 2' in json_output
        assert '"cols": 2' in json_output

    def test_headers_returns_first_row(self):
        """Should return first row as headers."""
        table = ExtractedTable(
            page=0,
            data=[
                ["Header1", "Header2"],
                ["Value1", "Value2"],
            ],
        )

        assert table.headers == ["Header1", "Header2"]

    def test_to_dict_rows(self):
        """Should convert to list of dictionaries."""
        table = ExtractedTable(
            page=0,
            data=[
                ["Name", "Age"],
                ["Alice", "30"],
                ["Bob", "25"],
            ],
        )

        rows = table.to_dict_rows()

        assert len(rows) == 2
        assert rows[0] == {"Name": "Alice", "Age": "30"}
        assert rows[1] == {"Name": "Bob", "Age": "25"}

    def test_rows_and_cols_properties(self):
        """Should return correct row and column counts."""
        table = ExtractedTable(
            page=0,
            data=[
                ["A", "B", "C"],
                ["1", "2", "3"],
            ],
        )

        assert table.rows == 2
        assert table.cols == 3

    def test_empty_table(self):
        """Should handle empty table data."""
        table = ExtractedTable(page=0, data=[])

        assert table.rows == 0
        assert table.cols == 0
        assert table.headers == []
        assert table.to_dict_rows() == []
