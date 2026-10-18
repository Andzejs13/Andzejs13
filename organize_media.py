#!/usr/bin/env python3
"""Atrod un sakārto attēlus un video pa tipiem un mēnešiem."""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

IMAGE_EXTENSIONS = {
    ".avif", ".bmp", ".gif", ".heic", ".jpeg", ".jpg", ".png", ".raw",
    ".svg", ".tif", ".tiff", ".webp",
}
VIDEO_EXTENSIONS = {
    ".3gp", ".avi", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg",
    ".webm",
}


@dataclass(frozen=True)
class Move:
    source: Path
    destination: Path


def media_type(path: Path) -> str | None:
    """Atgriež faila kategoriju, balstoties uz paplašinājumu."""
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "atteli"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    return None


def available_path(path: Path, reserved: set[Path]) -> Path:
    """Izveido unikālu mērķa nosaukumu, nepārrakstot esošus failus."""
    # Directory entries include dangling symlinks. Use the same conservative
    # case-insensitive policy on every platform, including for planned names.
    occupied = {str(item).casefold() for item in reserved}
    if path.parent.is_dir():
        occupied.update(str(item).casefold() for item in path.parent.iterdir())
    candidate = path
    counter = 1
    while (candidate.exists() or candidate.is_symlink()
           or str(candidate).casefold() in occupied):
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        counter += 1
    return candidate


def build_plan(source: Path, output: Path) -> list[Move]:
    """Izveido determinētu visu atrasto multivides failu pārvietošanas plānu."""
    source = source.resolve()
    output = output.resolve()
    if source == output:
        raise ValueError("Avota un rezultāta mape nedrīkst būt viena un tā pati.")
    output_is_nested = source in output.parents
    reserved: set[Path] = set()
    plan: list[Move] = []

    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            continue
        resolved = path.resolve()
        if not path.is_file() or resolved == Path(__file__).resolve():
            continue
        if output_is_nested and (output == resolved or output in resolved.parents):
            continue
        category = media_type(path)
        if category is None:
            continue
        month = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m")
        destination = available_path(output / category / month / path.name, reserved)
        reserved.add(destination)
        plan.append(Move(path, destination))
    return plan


def execute(plan: list[Move]) -> None:
    for move in plan:
        if move.source.is_symlink():
            raise ValueError(f"Avots ir simboliskā saite: {move.source}")
        move.destination.parent.mkdir(parents=True, exist_ok=True)
        if available_path(move.destination, set()) != move.destination:
            raise FileExistsError(f"Mērķis jau ir aizņemts: {move.destination}")
        shutil.move(str(move.source), str(move.destination))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Atrod un sakārto visus attēlus un video pa mēnešiem."
    )
    parser.add_argument("source", type=Path, help="mape, kurā meklēt failus")
    parser.add_argument(
        "--output", type=Path, help="rezultāta mape (noklusējums: SOURCE/sakartots)"
    )
    parser.add_argument(
        "--apply", action="store_true", help="pārvietot failus; bez šī slēdža rāda plānu"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.expanduser()
    if not source.is_dir():
        raise SystemExit(f"Mērķis nav mape: {source}")
    output = (args.output or source / "sakartots").expanduser()
    try:
        plan = build_plan(source, output)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    for move in plan:
        print(f"{move.source} -> {move.destination}")
    if args.apply:
        execute(plan)
        print(f"Pārvietoti faili: {len(plan)}")
    else:
        print(f"Atrasti faili: {len(plan)}. Pievieno --apply, lai tos pārvietotu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
