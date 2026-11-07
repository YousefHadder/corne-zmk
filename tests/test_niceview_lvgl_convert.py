from argparse import Namespace
from contextlib import redirect_stderr
import importlib.util
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "niceview", ROOT / "scripts/niceview_lvgl_convert.py"
)
niceview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(niceview)


class ImageGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.assets = self.root / "assets"
        self.assets.mkdir()
        self.art = self.root / "art.c"
        self.widget = self.root / "peripheral_status.c"
        self.art.write_text("original artwork\n")
        self.original_widget = (
            '#include "peripheral_status.h"\n\n'
            "LV_IMG_DECLARE(old);\n\n"
            "const lv_img_dsc_t *anim_imgs[] = {\n    &old,\n};\n\n"
            "static int handwritten_code;\n"
        )
        self.widget.write_text(self.original_widget)
        self.args = Namespace(
            outdir=self.root / "converted", width=68, height=140,
            no_rotate=False, no_dither=False, lsb_first=False, bytes_per_line=12,
            update_firmware=True, art_file=self.art, peripheral_file=self.widget,
        )

    def image(self, name, color=255):
        path = self.assets / name
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("L", (68, 140), color).save(path)
        return path

    def assert_unchanged(self):
        self.assertEqual(self.art.read_text(), "original artwork\n")
        self.assertEqual(self.widget.read_text(), self.original_widget)
        self.assertFalse(Path(self.args.outdir).exists())

    def test_valid_images_are_sorted_and_generation_is_idempotent(self):
        self.image("zebra.png", 0)
        self.image("alpha.PNG")
        paths = niceview.discover_images(self.assets)
        self.assertEqual([path.name for path in paths], ["alpha.PNG", "zebra.png"])
        niceview.generate_images(paths, self.args)
        art = self.art.read_text()
        widget = self.widget.read_text()
        self.assertLess(art.index("nice_view_art_img_alpha"), art.index("nice_view_art_img_zebra"))
        self.assertIn(".header.w = 140", art)
        self.assertIn(".header.h = 68", art)
        self.assertIn("&nice_view_art_img_alpha", widget)
        self.assertIn("static int handwritten_code;", widget)
        niceview.generate_images(list(reversed(paths)), self.args)
        self.assertEqual(self.art.read_text(), art)
        self.assertEqual(self.widget.read_text(), widget)

    def test_corrupt_images_never_publish_partial_output(self):
        valid = self.image("alpha.png")
        corrupt = self.assets / "zebra.png"
        corrupt.write_bytes(b"not an image")
        for paths in ([corrupt], [valid, corrupt]):
            with self.subTest(paths=paths):
                with self.assertRaises(OSError):
                    niceview.generate_images(paths, self.args)
                self.assert_unchanged()

    def test_invalid_and_missing_inputs_leave_outputs_unchanged(self):
        for name in ("bad-name.png", "123.png", "caf\u00e9.png"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "Invalid image filename"):
                    niceview.generate_images([self.image(name)], self.args)
                self.assert_unchanged()
        with self.assertRaisesRegex(ValueError, "regular image file"):
            niceview.generate_images([self.assets / "missing.png"], self.args)
        self.assert_unchanged()

    def test_duplicate_stems_are_rejected_across_directories_and_case(self):
        first = self.image("a/logo.png")
        for name in ("b/logo.jpg", "b/Logo.png"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "Duplicate image stem"):
                    niceview.generate_images([first, self.image(name)], self.args)
                self.assert_unchanged()

    def test_image_and_data_symbols_have_separate_namespaces(self):
        niceview.generate_images(
            [self.image("logo.png"), self.image("logo_map.png"), self.image("bolt.png")],
            self.args,
        )
        art = self.art.read_text()
        for stem in ("logo", "logo_map", "bolt"):
            self.assertIn(f"nice_view_art_data_{stem}[]", art)
            self.assertIn(f"const lv_img_dsc_t nice_view_art_img_{stem} =", art)
        self.assertNotIn("const lv_img_dsc_t bolt =", art)
        compiler = shutil.which("cc")
        if compiler:
            (self.root / "lvgl.h").write_text(
                "#include <stdint.h>\n"
                "#define LV_ATTRIBUTE_LARGE_CONST\n"
                "#define LV_IMG_CF_INDEXED_1BIT 1\n"
                "typedef struct {\n"
                "  struct { unsigned cf, always_zero, reserved, w, h; } header;\n"
                "  unsigned data_size; const uint8_t *data;\n"
                "} lv_img_dsc_t;\n"
            )
            result = subprocess.run(
                [compiler, "-std=c11", "-fsyntax-only", "-I", str(self.root), str(self.art)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_empty_assets_fail_instead_of_leaving_a_successful_stale_state(self):
        with self.assertRaisesRegex(ValueError, "No images found"):
            niceview.generate_images(niceview.discover_images(self.assets), self.args)
        self.assert_unchanged()

    def test_nested_inputs_preserve_stem_order_and_ignore_stale_conversions(self):
        zebra = self.image("a/zebra.png", 0)
        alpha = self.image("z/alpha.png")
        self.args.outdir.mkdir()
        (self.args.outdir / "stale.c").write_text("stale image data")
        niceview.generate_images([zebra, alpha], self.args)
        widget = self.widget.read_text()
        self.assertLess(widget.index("nice_view_art_img_alpha"), widget.index("nice_view_art_img_zebra"))
        self.assertNotIn("stale image data", self.art.read_text())

    def test_widget_mismatch_and_duplicate_blocks_fail_without_insertion(self):
        image = self.image("logo.png")
        variants = (
            self.original_widget.replace("const lv_img_dsc_t", "static const lv_img_dsc_t"),
            self.original_widget + "\n" + self.original_widget,
        )
        for content in variants:
            with self.subTest(content=content):
                self.widget.write_text(content)
                with self.assertRaisesRegex(ValueError, "exactly one"):
                    niceview.generate_images([image], self.args)
                self.assertEqual(self.widget.read_text(), content)
                self.assertEqual(self.art.read_text(), "original artwork\n")
                self.assertFalse(Path(self.args.outdir).exists())

    def test_failed_publication_restores_existing_files(self):
        self.args.outdir.mkdir()
        existing = self.args.outdir / "logo.c"
        existing.write_text("previous converted image\n")
        replace = niceview.os.replace

        def fail_on_widget(source, destination):
            if destination == self.widget:
                raise OSError("simulated replacement failure")
            return replace(source, destination)

        with patch.object(niceview.os, "replace", side_effect=fail_on_widget):
            with self.assertRaisesRegex(OSError, "simulated"):
                niceview.generate_images([self.image("logo.png")], self.args)
        self.assertEqual(existing.read_text(), "previous converted image\n")
        self.assertEqual(self.art.read_text(), "original artwork\n")
        self.assertEqual(self.widget.read_text(), self.original_widget)
        self.assertEqual(list(self.root.rglob("*.tmp")), [])

    def test_cli_failures_exit_nonzero_without_publishing(self):
        image = self.image("logo.png")
        for arguments in (
            [],
            [str(self.assets / "missing.png")],
            [str(image), "--width", "0"],
            [str(image), "--bytes-per-line", "0"],
            [str(image), "--assets-dir", str(self.assets)],
        ):
            with self.subTest(arguments=arguments):
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    niceview.main(arguments)
                self.assertNotEqual(error.exception.code, 0)
                self.assert_unchanged()

    def test_discovered_symlink_inputs_are_rejected(self):
        image = self.image("logo.png")
        link = self.assets / "linked.png"
        link.symlink_to(image)
        with self.assertRaisesRegex(ValueError, "regular image file"):
            niceview.generate_images(niceview.discover_images(self.assets), self.args)
        self.assert_unchanged()

    def test_overlapping_output_paths_are_rejected_before_publication(self):
        self.args.outdir = self.root
        with self.assertRaisesRegex(ValueError, "paths overlap"):
            niceview.generate_images([self.image("art.png")], self.args)
        self.assertEqual(self.art.read_text(), "original artwork\n")
        self.assertEqual(self.widget.read_text(), self.original_widget)

    def test_image_count_respects_pinned_lvgl_animation_limit(self):
        paths = []
        for index in range(128):
            path = self.assets / f"image_{index}.png"
            path.touch()
            paths.append(path)
        with self.assertRaisesRegex(ValueError, "at most 127"):
            niceview.generate_images(paths, self.args)
        self.assert_unchanged()

    def test_packing_preserves_row_padding_and_bit_order(self):
        image = Image.new("1", (9, 2))
        image.putdata(
            [255, 0, 0, 0, 0, 0, 0, 0, 255, 0, 255, 0, 255, 0, 255, 0, 255, 0]
        )
        self.assertEqual(niceview.pack_bits_1bpp(image), bytes([128, 128, 85, 0]))
        self.assertEqual(
            niceview.pack_bits_1bpp(image, lsb_first=True), bytes([1, 1, 170, 0])
        )


if __name__ == "__main__":
    unittest.main()
