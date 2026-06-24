"""Download Princeton's public baseball-elimination test datasets."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen
from zipfile import ZipFile


DEFAULT_URL = (
    "https://coursera.cs.princeton.edu/algs4/assignments/baseball/baseball.zip"
)


def safe_member_path(filename: str) -> PurePosixPath:
    """Normalize ZIP separators and reject absolute or parent paths."""

    member_path = PurePosixPath(filename.replace("\\", "/"))
    has_drive = bool(member_path.parts and member_path.parts[0].endswith(":"))
    if member_path.is_absolute() or has_drive or ".." in member_path.parts:
        raise ValueError(f"unsafe ZIP member path: {filename}")
    return member_path


def extract_text_datasets(archive_path: Path, destination: Path) -> list[Path]:
    """Safely extract text datasets from an assignment ZIP archive."""

    destination.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    with ZipFile(archive_path) as archive:
        for member in archive.infolist():
            member_path = safe_member_path(member.filename)
            if member.is_dir() or member_path.suffix.lower() != ".txt":
                continue

            target = destination / member_path.name
            temporary = target.with_suffix(target.suffix + ".tmp")
            with archive.open(member) as source, temporary.open("wb") as output:
                shutil.copyfileobj(source, output)
            temporary.replace(target)
            extracted.append(target)
    return sorted(extracted)


def download_datasets(url: str, destination: Path) -> list[Path]:
    """Download an archive to the destination directory and extract datasets."""

    destination.mkdir(parents=True, exist_ok=True)
    temporary_archive = destination / ".baseball-download.tmp"
    request = Request(url, headers={"User-Agent": "algorithm-lab/1.0"})
    try:
        with urlopen(request, timeout=60) as response, temporary_archive.open(
            "wb"
        ) as output:
            shutil.copyfileobj(response, output)
        return extract_text_datasets(temporary_archive, destination)
    finally:
        temporary_archive.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path("data/princeton"),
    )
    args = parser.parse_args()
    try:
        files = download_datasets(args.url, args.destination)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    for path in files:
        print(path)
    print(f"downloaded {len(files)} text datasets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
