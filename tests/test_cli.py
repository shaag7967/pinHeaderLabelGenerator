"""Command line interface."""

import io
import json

import pytest

from pin_header_label import __version__
from pin_header_label.cli import CommandLineInterface, main
from pin_header_label.model import Project

from conftest import EXAMPLES


def run(*argv: str) -> tuple[int, str, str]:
    """Run the CLI; English unless the arguments select another language."""
    out, err = io.StringIO(), io.StringIO()
    args = list(argv) if "--lang" in argv else ["--lang", "en", *argv]
    code = CommandLineInterface(out, err).run(args)
    return code, out.getvalue(), err.getvalue()


def test_no_command_prints_help():
    code, out, _ = run()
    assert code == 0
    assert "export" in out and "import" in out


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_german_help(capsys):
    with pytest.raises(SystemExit):
        main(["--lang", "de", "export", "--help"])
    assert "PDF-Datei schreiben" in capsys.readouterr().out


class TestImport:
    def test_creates_project_next_to_pin_list(self, tmp_path):
        pin_list = tmp_path / "pins.txt"
        pin_list.write_text("GND\nVCC\nSDA\n", encoding="utf-8")
        code, out, _ = run("import", str(pin_list), "--title", "J2", "--pitch", "2.0")
        assert code == 0
        assert "pins.json" in out
        project = Project.load(tmp_path / "pins.json")
        assert project.title == "J2"
        assert project.pitch == 2.0
        assert (project.rows, project.cols) == (2, 2)
        assert project.pin(1, 0).label == "SDA"

    def test_options_affect_placement(self, tmp_path):
        output = tmp_path / "p.json"
        code, *_ = run(
            "import", str(EXAMPLES / "ftdi_uart.txt"), "-o", str(output), "--cols", "2", "--numbering", "dip"
        )
        assert code == 0
        project = Project.load(output)
        assert project.pin(0, 1).label == "RTS"

    def test_template(self, tmp_path):
        output = tmp_path / "p.json"
        code, *_ = run(
            "import", str(EXAMPLES / "sensor_board.csv"), "-o", str(output),
            "--template", str(EXAMPLES / "example_header.json"),
        )  # fmt: skip
        assert code == 0
        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["font_family"] == "Montserrat SemiBold"
        assert data["rows"] == 4

    def test_refuses_to_overwrite(self, tmp_path):
        output = tmp_path / "p.json"
        output.write_text("{}", encoding="utf-8")
        code, _, err = run("import", str(EXAMPLES / "ftdi_uart.txt"), "-o", str(output))
        assert code == 1
        assert "--force" in err
        assert run("import", str(EXAMPLES / "ftdi_uart.txt"), "-o", str(output), "--force")[0] == 0

    def test_invalid_pin_list(self, tmp_path):
        bad = tmp_path / "bad.csv"
        bad.write_text("pin,label\n1,A\n1,B\n", encoding="utf-8")
        code, _, err = run("import", str(bad))
        assert code == 1
        assert "error:" in err and "twice" in err

    def test_german_messages(self, tmp_path):
        bad = tmp_path / "bad.csv"
        bad.write_text("pin,label\n1,A\n1,B\n", encoding="utf-8")
        _, _, err = run("--lang", "de", "import", str(bad))
        assert "Fehler:" in err and "doppelt" in err


@pytest.mark.usefixtures("qapp")
class TestExport:
    def test_all_formats(self, tmp_path):
        code, out, _ = run(
            "export", str(EXAMPLES / "example_header.json"),
            "--pdf", str(tmp_path / "a.pdf"), "--png", str(tmp_path / "a.png"), "--dpi", "72",
            "--svg", str(tmp_path / "a.svg"),
        )  # fmt: skip
        assert code == 0
        assert out.count("Written") == 3
        assert all((tmp_path / f"a.{ext}").stat().st_size > 0 for ext in ("pdf", "png", "svg"))

    def test_export_pin_list_directly(self, tmp_path):
        code, *_ = run("export", str(EXAMPLES / "raspberry_pi_gpio.csv"), "--png", str(tmp_path / "pi.png"),
                       "--dpi", "72", "--label-only")  # fmt: skip
        assert code == 0
        assert (tmp_path / "pi.png").exists()

    def test_warns_when_copies_do_not_fit(self, tmp_path):
        project = Project.load(EXAMPLES / "example_header.json")
        project.copies = 60
        project.save(tmp_path / "many.json")
        code, _, err = run("export", str(tmp_path / "many.json"), "--pdf", str(tmp_path / "many.pdf"))
        assert code == 0
        assert "Warning" in err

    def test_needs_an_output(self):
        code, _, err = run("export", str(EXAMPLES / "example_header.json"))
        assert code == 1
        assert "--pdf" in err

    @pytest.mark.parametrize("name", ["missing.json", "pins.xlsx"])
    def test_bad_input(self, tmp_path, name):
        code, _, err = run("export", str(tmp_path / name), "--pdf", str(tmp_path / "x.pdf"))
        assert code == 1
        assert name in err
