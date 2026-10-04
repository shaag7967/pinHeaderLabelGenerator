"""Import of pin lists from text and CSV files."""

import pytest

from pin_header_label.importers import (
    NumberedPinList,
    PinEntry,
    PinListFormatError,
    PinListReader,
    RowPinList,
)
from pin_header_label.model import Numbering, Project

from conftest import EXAMPLES


@pytest.fixture
def reader() -> PinListReader:
    return PinListReader()


def labels(project: Project) -> list[list[str]]:
    return [[project.pin(r, c).label for c in range(project.cols)] for r in range(project.rows)]


class TestTextFormat:
    def test_lines_are_pins_in_order(self, reader):
        result = reader.parse_text("GND\n* VCC\n-\nSDA\n\n")
        assert isinstance(result, NumberedPinList)
        assert result.entries == {1: PinEntry("GND"), 2: PinEntry("VCC"), 3: PinEntry(""), 4: PinEntry("SDA")}
        assert result.pin_count == 4
        assert result.label_count == 3

    def test_apply_zigzag_by_default(self, reader):
        project = Project()
        reader.parse_text("1\n2\n3\n4\n5").apply_to(project)
        assert project.rows == 3
        assert labels(project) == [["1", "2"], ["3", "4"], ["5", ""]]

    def test_apply_dip(self, reader):
        project = Project(numbering=Numbering.DIP)
        reader.parse_text("1\n2\n3\n4\n5\n6").apply_to(project)
        assert labels(project) == [["1", "6"], ["2", "5"], ["3", "4"]]

    def test_apply_single_row(self, reader):
        project = Project(cols=1)
        reader.parse_text("A\nB\nC").apply_to(project)
        assert labels(project) == [["A"], ["B"], ["C"]]

    def test_import_replaces_labels_and_colors(self, reader, small_project):
        reader.parse_text("X\nY").apply_to(small_project)
        assert small_project.rows == 1
        assert labels(small_project) == [["X", "Y"]]
        small_project.resize(4)
        assert small_project.pin(1, 0).color == ""

    def test_empty_text_is_rejected(self, reader):
        with pytest.raises(PinListFormatError):
            reader.parse_text("\n - \nleer\n")


class TestCsvWithHeader:
    def test_numbered_with_colors(self, reader):
        result = reader.parse_csv("Pin,Signal,Farbe\n2,VCC,red\n1,GND,#000\n4,SDA,\n")
        assert isinstance(result, NumberedPinList)
        assert result.entries[1] == PinEntry("GND", "#000000")
        assert result.entries[2] == PinEntry("VCC", "#d32f2f")
        project = Project()
        result.apply_to(project)
        assert labels(project) == [["GND", "VCC"], ["", "SDA"]]

    def test_left_right_columns(self, reader):
        result = reader.parse_csv("left;right;right_color\nA;B;blue\n;D;\nE;;\n")
        assert isinstance(result, RowPinList)
        assert result.columns == 2
        project = Project(cols=1)
        result.apply_to(project)
        assert project.cols == 2
        assert labels(project) == [["A", "B"], ["", "D"], ["E", ""]]
        assert project.pin(0, 1).color == "#1565c0"

    def test_single_column_with_label_header(self, reader):
        result = reader.parse_csv("label,color\nTX,green\nRX,\n")
        project = Project()
        result.apply_to(project)
        assert project.cols == 1
        assert labels(project) == [["TX"], ["RX"]]

    def test_header_aliases_are_case_and_separator_insensitive(self, reader):
        result = reader.parse_csv("PIN-NR\tName\n1\tA\n")
        assert isinstance(result, NumberedPinList)

    def test_tab_delimiter(self, reader):
        result = reader.parse_csv("pin\tlabel\n1\tA, B\n", delimiter="\t")
        assert result.entries[1].label == "A, B"

    @pytest.mark.parametrize(
        ("text", "message"),
        [
            ("pin,color\n1,red\n", "label"),
            ("pin,label\nx,A\n", "Line 2"),
            ("pin,label\n1,A\n1,B\n", "twice"),
            ("pin,label,color\n1,A,plaid\n", "unknown color"),
            ("pin,label\n,A\n", "missing"),
            ("color\nred\n", "label column"),
            ("pin,label\n1,\n", "no labels"),
        ],
    )
    def test_errors(self, reader, text, message):
        with pytest.raises(PinListFormatError, match=message):
            reader.parse_csv(text)

    def test_too_many_rows(self, reader):
        result = reader.parse_csv("pin,label\n999,A\n")
        with pytest.raises(PinListFormatError, match="Too many"):
            result.apply_to(Project())


class TestCsvWithoutHeader:
    def test_first_column_with_pin_numbers(self, reader):
        result = reader.parse_csv("1,GND,black\n2,VCC\nP3,SDA\n")
        assert isinstance(result, NumberedPinList)
        assert result.entries[3] == PinEntry("SDA")
        assert result.entries[1].color == "#1b1b1b"

    def test_two_label_columns(self, reader):
        result = reader.parse_csv("GND,VCC\nSDA,SCL\n")
        assert isinstance(result, RowPinList)
        assert result.columns == 2
        assert result.rows[1] == (PinEntry("SDA"), PinEntry("SCL"))

    def test_single_label_column(self, reader):
        result = reader.parse_csv("GND\nVCC\n")
        assert isinstance(result, RowPinList)
        assert result.columns == 1


class TestFiles:
    def test_read_dispatches_on_suffix(self, reader, tmp_path):
        (tmp_path / "a.txt").write_text("1,2\n", encoding="utf-8")
        (tmp_path / "a.csv").write_text("1,2\n", encoding="utf-8")
        assert isinstance(reader.read(tmp_path / "a.txt"), NumberedPinList)
        assert reader.read(tmp_path / "a.txt").entries[1].label == "1,2"
        assert isinstance(reader.read(tmp_path / "a.csv"), NumberedPinList)

    def test_utf8_bom_and_cp1252(self, reader, tmp_path):
        (tmp_path / "bom.csv").write_bytes("﻿label\nMasse\n".encode())
        assert reader.read(tmp_path / "bom.csv").rows[0][0].label == "Masse"
        (tmp_path / "excel.csv").write_bytes("label\nTür\n".encode("cp1252"))
        assert reader.read(tmp_path / "excel.csv").rows[0][0].label == "Tür"

    def test_examples(self, reader):
        pi = Project()
        reader.read(EXAMPLES / "raspberry_pi_gpio.csv").apply_to(pi)
        assert (pi.rows, pi.cols) == (20, 2)
        assert pi.pin(0, 0).label == "3V3"
        assert pi.pin(19, 1).label == "GPIO21"

        board = Project()
        reader.read(EXAMPLES / "sensor_board.csv").apply_to(board)
        assert labels(board) == [["VCC", "GND"], ["SDA", "SCL"], ["INT", "RESET"], ["", "LED"]]

        uart = Project(cols=1)
        reader.read(EXAMPLES / "ftdi_uart.txt").apply_to(uart)
        assert [row[0] for row in labels(uart)] == ["GND", "CTS", "VCC", "TXD", "RXD", "RTS"]
