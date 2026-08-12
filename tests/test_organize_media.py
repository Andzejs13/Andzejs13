import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from organize_media import build_plan, execute, media_type


class OrganizeMediaTests(unittest.TestCase):
    def test_recognizes_media_case_insensitively(self):
        self.assertEqual(media_type(Path("photo.JPEG")), "atteli")
        self.assertEqual(media_type(Path("clip.MP4")), "video")
        self.assertIsNone(media_type(Path("notes.txt")))

    def test_builds_month_folders_and_ignores_other_files(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            photo = source / "holiday.jpg"
            video = source / "nested" / "movie.mov"
            other = source / "notes.txt"
            video.parent.mkdir()
            for path in (photo, video, other):
                path.write_text("test")
            timestamp = datetime(2024, 3, 15).timestamp()
            os.utime(photo, (timestamp, timestamp))
            os.utime(video, (timestamp, timestamp))

            plan = build_plan(source, source / "sakartots")

            self.assertEqual(len(plan), 2)
            destinations = {move.destination.relative_to(source) for move in plan}
            self.assertEqual(
                destinations,
                {
                    Path("sakartots/atteli/2024-03/holiday.jpg"),
                    Path("sakartots/video/2024-03/movie.mov"),
                },
            )

    def test_execute_preserves_duplicate_names(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "one").mkdir()
            (source / "two").mkdir()
            (source / "one" / "photo.png").write_text("first")
            (source / "two" / "photo.png").write_text("second")
            output = source / "sakartots"

            plan = build_plan(source, output)
            execute(plan)

            files = sorted((output / "atteli").rglob("*.png"))
            self.assertEqual([path.name for path in files], ["photo.png", "photo_1.png"])
            self.assertEqual({path.read_text() for path in files}, {"first", "second"})


if __name__ == "__main__":
    unittest.main()
