import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from organize_media import available_path, build_plan, execute, media_type


class OrganizeMediaTests(unittest.TestCase):
    def make_link(self, link, target, **kwargs):
        try:
            link.symlink_to(target, **kwargs)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"Symlinks unavailable: {error}")

    def test_case_only_planned_names_preserve_both_files(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory).resolve()
            for folder, name, content in (
                ("one", "Photo.JPG", "first"),
                ("two", "photo.jpg", "second"),
            ):
                path = source / folder / name
                path.parent.mkdir()
                path.write_text(content)
                timestamp = datetime(2024, 3, 15).timestamp()
                os.utime(path, (timestamp, timestamp))
            plan = build_plan(source, source / "output")
            self.assertEqual([m.destination.name for m in plan],
                             ["Photo.JPG", "photo_1.jpg"])
            execute(plan)
            self.assertEqual([m.destination.read_text() for m in plan],
                             ["first", "second"])

    def test_existing_case_variants_and_reserved_suffix_are_occupied(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            (parent / "Photo.JPG").write_text("existing")
            (parent / "PHOTO_1.JPG").mkdir()
            result = available_path(parent / "photo.jpg", {parent / "PHOTO_2.JPG"})
            self.assertEqual(result, parent / "photo_3.jpg")
            self.assertEqual((parent / "Photo.JPG").read_text(), "existing")

    def test_output_ancestor_allows_moving_source_files(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory).resolve()
            source = output / "import"
            source.mkdir()
            photo = source / "photo.jpg"
            photo.write_text("original")
            plan = build_plan(source, output)
            self.assertEqual(len(plan), 1)
            execute(plan)
            self.assertEqual(plan[0].destination.read_text(), "original")
            self.assertFalse(photo.exists())

    def test_equal_output_is_rejected_without_changing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory).resolve()
            photo = source / "photo.jpg"
            photo.write_text("original")
            with self.assertRaises(ValueError):
                build_plan(source, source / ".")
            self.assertEqual(photo.read_text(), "original")

    def test_execute_refuses_destination_created_after_planning(self):
        for kind in ("file", "case_variant", "dangling_link"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                source = Path(directory).resolve()
                photo = source / "photo.jpg"
                photo.write_text("original")
                plan = build_plan(source, source / "output")
                destination = plan[0].destination
                destination.parent.mkdir(parents=True)
                occupied = destination
                if kind == "dangling_link":
                    self.make_link(occupied, "missing")
                else:
                    if kind == "case_variant":
                        occupied = destination.with_name("PHOTO.JPG")
                    occupied.write_text("existing")
                with self.assertRaises(FileExistsError):
                    execute(plan)
                self.assertEqual(photo.read_text(), "original")
                if kind == "dangling_link":
                    self.assertEqual(os.readlink(occupied), "missing")
                else:
                    self.assertEqual(occupied.read_text(), "existing")

    def test_execute_refuses_source_replaced_by_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            photo = root / "photo.jpg"
            photo.write_text("original")
            plan = build_plan(root, root / "output")
            external = root / "target.txt"
            external.write_text("external")
            photo.unlink()
            self.make_link(photo, external)
            with self.assertRaises(ValueError):
                execute(plan)
            self.assertTrue(photo.is_symlink())
            self.assertEqual(external.read_text(), "external")
            self.assertFalse(plan[0].destination.exists())

    def test_nested_output_is_excluded_and_planning_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory).resolve()
            output = source / "output"
            output.mkdir()
            existing = output / "existing.jpg"
            existing.write_text("existing")
            photo = source / "photo.jpg"
            photo.write_text("new")
            plan = build_plan(source, output)
            self.assertEqual([m.source for m in plan], [photo])
            self.assertEqual(existing.read_text(), "existing")
            self.assertTrue(photo.exists())
            self.assertFalse(plan[0].destination.parent.exists())

    def test_dangling_destination_links_are_preserved(self):
        for name in ("photo.jpg", "PHOTO.JPG"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                source = Path(directory).resolve()
                photo = source / "photo.jpg"
                photo.write_text("new")
                output = source / "output"
                destination = build_plan(source, output)[0].destination
                destination.parent.mkdir(parents=True)
                link = destination.with_name(name)
                self.make_link(link, "missing-target")
                plan = build_plan(source, output)
                self.assertEqual(plan[0].destination.name, "photo_1.jpg")
                execute(plan)
                self.assertTrue(link.is_symlink())
                self.assertEqual(os.readlink(link), "missing-target")
                self.assertFalse((link.parent / "missing-target").exists())
                self.assertEqual(plan[0].destination.read_text(), "new")

    def test_source_links_are_skipped_without_touching_external_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "import"
            nested = source / "nested"
            nested.mkdir(parents=True)
            photo = source / "original.jpg"
            photo.write_text("original")
            external = root / "outside.jpg"
            external.write_text("external")
            links = {
                nested / "relative.jpg": "../original.jpg",
                nested / "absolute.jpg": str(external),
                nested / "broken.jpg": "missing.jpg",
            }
            for link, target in links.items():
                self.make_link(link, target)
            original_links = {link: os.readlink(link) for link in links}
            linked_directory = source / "linked-directory"
            self.make_link(linked_directory, root, target_is_directory=True)
            plan = build_plan(source, source / "output")
            self.assertEqual([m.source for m in plan], [photo])
            execute(plan)
            self.assertEqual(plan[0].destination.read_text(), "original")
            self.assertEqual(external.read_text(), "external")
            for link, target in original_links.items():
                self.assertTrue(link.is_symlink())
                self.assertEqual(os.readlink(link), target)

    def test_source_symlink_loop_is_skipped_before_resolving(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory).resolve()
            self.make_link(source / "loop.jpg", "loop.jpg")
            self.assertEqual(build_plan(source, source / "output"), [])

    def test_recognizes_media_case_insensitively(self):
        self.assertEqual(media_type(Path("photo.JPEG")), "atteli")
        self.assertEqual(media_type(Path("clip.MP4")), "video")
        self.assertIsNone(media_type(Path("notes.txt")))

    def test_builds_month_folders_and_ignores_other_files(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory).resolve()
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
            source = Path(directory).resolve()
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
