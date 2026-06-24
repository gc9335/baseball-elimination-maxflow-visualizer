from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts.download_datasets import extract_text_datasets


def make_zip(path: Path, members: dict[str, str]) -> Path:
    with ZipFile(path, "w") as archive:
        for name, text in members.items():
            archive.writestr(name, text)
    return path


def test_extract_text_datasets_extracts_txt_files_only(tmp_path):
    archive = make_zip(
        tmp_path / "baseball.zip",
        {
            "baseball/teams4.txt": "4\n",
            "baseball/README.md": "ignored",
        },
    )
    destination = tmp_path / "data"

    extracted = extract_text_datasets(archive, destination)

    assert extracted == [destination / "teams4.txt"]
    assert (destination / "teams4.txt").read_text(encoding="utf-8") == "4\n"
    assert not (destination / "README.md").exists()


def test_extract_text_datasets_rejects_path_traversal(tmp_path):
    archive = make_zip(
        tmp_path / "bad.zip",
        {"../teams4.txt": "malicious"},
    )

    with pytest.raises(ValueError, match="unsafe"):
        extract_text_datasets(archive, tmp_path / "data")
