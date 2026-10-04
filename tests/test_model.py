"""Project data model and pin numbering."""

import json

import pytest

from pin_header_label.model import (
    ColorStyle,
    LeaderMode,
    Numbering,
    Pin,
    PinNumbering,
    Project,
    ProjectFormatError,
    SideMode,
)
from pin_header_label.model.project import MAX_ROWS


class TestPinNumbering:
    @pytest.mark.parametrize(
        ("scheme", "expected"),
        [
            (Numbering.ZIGZAG, [[1, 2], [3, 4], [5, 6]]),
            (Numbering.DIP, [[1, 6], [2, 5], [3, 4]]),
            (Numbering.COLUMN, [[1, 4], [2, 5], [3, 6]]),
        ],
    )
    def test_two_row_schemes(self, scheme, expected):
        numbering = PinNumbering(scheme, rows=3, cols=2)
        assert [[numbering.number(r, c) for c in range(2)] for r in range(3)] == expected

    def test_none_has_no_numbers(self):
        assert PinNumbering(Numbering.NONE, 3, 2).number(1, 1) is None

    @pytest.mark.parametrize("scheme", [Numbering.ZIGZAG, Numbering.DIP, Numbering.COLUMN])
    def test_single_row_is_top_to_bottom(self, scheme):
        numbering = PinNumbering(scheme, rows=4, cols=1)
        assert [numbering.number(r, 0) for r in range(4)] == [1, 2, 3, 4]

    @pytest.mark.parametrize("scheme", list(Numbering))
    @pytest.mark.parametrize("cols", [1, 2])
    def test_position_is_inverse_of_number(self, scheme, cols):
        numbering = PinNumbering(scheme, rows=5, cols=cols)
        effective = PinNumbering(Numbering.ZIGZAG if scheme == Numbering.NONE else scheme, 5, cols)
        for n in range(1, numbering.pin_count + 1):
            row, col = numbering.position(n)
            assert effective.number(row, col) == n

    def test_position_out_of_range(self):
        with pytest.raises(ValueError):
            PinNumbering(Numbering.ZIGZAG, 2, 2).position(5)
        with pytest.raises(ValueError):
            PinNumbering(Numbering.ZIGZAG, 2, 2).position(0)

    @pytest.mark.parametrize(("count", "cols", "rows"), [(10, 2, 5), (11, 2, 6), (7, 1, 7), (0, 2, 1)])
    def test_rows_for(self, count, cols, rows):
        assert PinNumbering.rows_for(count, cols) == rows


class TestProjectBasics:
    def test_defaults_create_pin_storage(self):
        project = Project()
        assert len(project.pins) == project.rows
        assert all(len(row) == 2 for row in project.pins)

    def test_iter_pins_respects_columns(self):
        project = Project(rows=3, cols=1)
        assert [(r, c) for r, c, _ in project.iter_pins()] == [(0, 0), (1, 0), (2, 0)]

    def test_label_count(self, small_project):
        assert small_project.label_count == 4
        small_project.cols = 1
        assert small_project.label_count == 2

    def test_normalize_clamps_values(self):
        project = Project(
            rows=1000, cols=5, pitch=0.1, font_pt=99, gap_mm=0, copies=0, scale_x=10, scale_y=500
        )
        project.normalize()
        assert project.rows == MAX_ROWS
        assert project.cols == 2
        assert project.pitch == 0.5
        assert project.font_pt == 14.0
        assert project.gap_mm == 0.3
        assert project.copies == 1
        assert (project.scale_x, project.scale_y) == (50.0, 150.0)


class TestProjectEditing:
    def test_resize_keeps_hidden_rows(self, small_project):
        small_project.resize(2)
        small_project.resize(4)
        assert small_project.pin(3, 1).label == "SCL"

    def test_insert_row(self, small_project):
        assert small_project.insert_row(1)
        assert small_project.rows == 5
        assert small_project.pin(1, 0).is_empty
        assert small_project.pin(2, 0).label == "SDA"

    def test_insert_row_drops_hidden_rows(self, small_project):
        small_project.resize(2)
        small_project.insert_row(0)
        assert small_project.rows == 3
        assert len(small_project.pins) == 3

    def test_insert_row_at_maximum(self):
        project = Project(rows=MAX_ROWS)
        assert not project.insert_row(0)
        assert project.rows == MAX_ROWS

    def test_delete_row(self, small_project):
        assert small_project.delete_row(0)
        assert small_project.rows == 3
        assert small_project.pin(0, 0).label == "SDA"

    def test_delete_last_remaining_row_is_refused(self):
        project = Project(rows=1)
        assert not project.delete_row(0)
        assert not Project(rows=3).delete_row(5)

    def test_clear_pins_and_colors(self, small_project):
        small_project.clear_colors()
        assert small_project.pin(1, 0).color == ""
        assert small_project.pin(1, 0).label == "SDA"
        small_project.clear_pins()
        assert small_project.label_count == 0

    def test_apply_auto_colors(self, small_project):
        assert small_project.apply_auto_colors() == 2
        assert small_project.pin(0, 0).color == "#1b1b1b"
        assert small_project.pin(0, 1).color == "#d32f2f"
        assert small_project.pin(1, 0).color == "#1565c0"  # unchanged
        assert small_project.apply_auto_colors() == 0

    def test_set_column_labels_fits_rows(self, small_project):
        small_project.set_column_labels([["A", "- B", "leer"], ["X", "Y", "Z", "W", "V"]])
        assert small_project.rows == 5
        assert [small_project.pin(r, 0).label for r in range(5)] == ["A", "B", "", "", ""]
        assert [small_project.pin(r, 1).label for r in range(5)] == ["X", "Y", "Z", "W", "V"]
        assert small_project.pin(1, 0).color == "#1565c0"  # colors are kept

    def test_set_column_labels_without_fitting(self, small_project):
        small_project.set_column_labels([["A"] * 10], fit_rows=False)
        assert small_project.rows == 4

    def test_paste_labels_grows_rows_and_ignores_extra_columns(self, small_project):
        small_project.paste_labels(3, 1, [["a", "ignored"], ["b"], ["* c"]])
        assert small_project.rows == 6
        assert [small_project.pin(r, 1).label for r in (3, 4, 5)] == ["a", "b", "c"]
        assert small_project.pin(3, 0).label == ""

    def test_paste_labels_two_columns(self):
        project = Project(rows=2)
        project.paste_labels(0, 0, [["L1", "R1"], ["L2", "R2"]])
        assert [[p.label for p in row] for row in project.pins] == [["L1", "R1"], ["L2", "R2"]]


class TestProjectSerialization:
    def test_round_trip(self, small_project):
        small_project.title = "J1 – Sensor"
        small_project.numbering = Numbering.DIP
        small_project.color_style = ColorStyle.OUTLINE
        restored = Project.from_json(small_project.to_json())
        assert restored == small_project

    def test_json_contains_plain_values(self, small_project):
        data = json.loads(small_project.to_json())
        assert data["format_version"] == 1
        assert data["side_mode"] == "right"
        assert len(data["pins"]) == 4
        assert data["pins"][1][0] == {"label": "SDA", "color": "#1565c0"}

    def test_hidden_rows_and_columns_are_not_saved(self, small_project):
        small_project.resize(2)
        small_project.cols = 1
        data = small_project.to_dict()
        assert len(data["pins"]) == 2
        assert all(len(row) == 1 for row in data["pins"])

    def test_from_dict_coerces_and_falls_back(self):
        project = Project.from_dict(
            {
                "rows": "3",
                "cols": 1.0,
                "bold": "true",
                "outline": 0,
                "pitch": "2.0",
                "side_mode": "alternate",
                "leaders": "sometimes",  # invalid -> default
                "font_pt": None,  # invalid -> default
                "unknown_key": 42,
                "pins": [[{"label": "A"}], [{"label": "B", "color": "#ff0000"}, {"label": "C"}], "bad"],
            }
        )
        assert project.rows == 3
        assert project.cols == 1
        assert project.bold is True
        assert project.outline is False
        assert project.pitch == 2.0
        assert project.side_mode is SideMode.ALTERNATE
        assert project.leaders is LeaderMode.AUTO
        assert project.font_pt == 6.0
        assert project.pin(1, 0) == Pin("B", "#ff0000")
        assert project.pin(1, 1).label == "C"
        assert len(project.pins) == 3

    @pytest.mark.parametrize("text", ["not json", "[1, 2]", '{"pins": 5}'])
    def test_invalid_files(self, text):
        with pytest.raises(ProjectFormatError):
            Project.from_json(text)

    def test_save_and_load(self, tmp_path, small_project):
        path = tmp_path / "p.json"
        small_project.save(path)
        assert Project.load(path) == small_project

    def test_example_file_loads(self, example_project):
        assert example_project.rows == 15
        assert example_project.cols == 2
        assert example_project.label_count == 19
