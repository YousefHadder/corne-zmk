#!/usr/bin/env python3
"""
niceview_lvgl_convert.py

Convert images to fixed size 1-bit indexed LVGL C arrays.
Pipeline:
  - Resize to width x height (defaults 68x140)
  - (Optional) Rotate 90° clockwise (default: rotate)
  - Convert to 1-bit (Floyd–Steinberg dither by default)
  - Pack pixels (8 px / byte), MSB-first by default
  - Emit a .c file whose name matches the source image stem
  - LVGL descriptor uses LV_IMG_CF_INDEXED_1BIT and includes a 2‑entry conditional palette

Usage examples:
  python3 niceview_lvgl_convert.py img.jpg
  python3 niceview_lvgl_convert.py img1.jpg img2.png --outdir out
  python3 niceview_lvgl_convert.py art.png --lsb-first
  python3 niceview_lvgl_convert.py logo.png --no-dither --no-rotate
"""

import argparse
from copy import copy
import os
from pathlib import Path
import re
import tempfile

from PIL import Image

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
WIDGET_DIRECTORY = Path("boards/shields/nice_view_custom/widgets")
ART_HEADER = """\
#include <lvgl.h>

#ifndef LV_ATTRIBUTE_MEM_ALIGN
#define LV_ATTRIBUTE_MEM_ALIGN
#endif

"""
WIDGET_BLOCK = re.compile(
    r"^(?:LV_IMG_DECLARE\([A-Za-z_][A-Za-z0-9_]*\);[ \t]*\n\s*)+"
    r"const[ \t]+lv_img_dsc_t[ \t]*\*[ \t]*anim_imgs\[\][ \t]*=[ \t]*\{[^}]*\};",
    re.MULTILINE,
)


def image_symbol(stem):
    return f"nice_view_art_img_{stem}"


def discover_images(directory):
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError(f"Asset directory must be a regular directory: {directory}")
    return sorted(
        (
            path for path in directory.rglob("*")
            if path.suffix.lower() in IMAGE_EXTENSIONS
            and (path.is_file() or path.is_symlink())
        ),
        key=lambda path: path.as_posix(),
    )


def validate_inputs(paths):
    if not paths:
        raise ValueError("No images found; existing artwork was not changed")
    stems = set()
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Input must be a regular image file: {path}")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", path.stem):
            raise ValueError(
                f"Invalid image filename: {path.name}; use letters, digits, and "
                "underscores, and do not start with a digit"
            )
        key = path.stem.casefold()
        if key in stems:
            raise ValueError(f"Duplicate image stem: {path.stem}")
        stems.add(key)


def update_widget(content, stems):
    matches = list(WIDGET_BLOCK.finditer(content))
    arrays = re.findall(r"\banim_imgs\s*\[\s*\]\s*=", content)
    if len(matches) != 1 or len(arrays) != 1:
        raise ValueError(
            "Expected exactly one LV_IMG_DECLARE/anim_imgs block in "
            "peripheral_status.c; existing artwork was not changed"
        )
    declarations = "\n".join(f"LV_IMG_DECLARE({image_symbol(stem)});" for stem in stems)
    array = "const lv_img_dsc_t *anim_imgs[] = {\n"
    array += "".join(f"    &{image_symbol(stem)},\n" for stem in stems)
    array += "};"
    return WIDGET_BLOCK.sub(lambda match: declarations + "\n\n" + array, content, count=1)


def publish_files(files):
    destinations = [path.resolve() for path, _ in files]
    if len(set(destinations)) != len(destinations):
        raise ValueError("Generated output paths overlap")
    staged = []
    published = []
    originals = {}
    try:
        for path, content in files:
            if path.is_symlink():
                raise ValueError(f"Output must not be a symlink: {path}")
            originals[path] = path.read_bytes() if path.exists() else None
            mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
            ) as temporary:
                staged.append((path, Path(temporary.name)))
                temporary.write(content)
            os.chmod(temporary.name, mode)
        for path, temporary in staged:
            os.replace(temporary, path)
            published.append(path)
    except OSError:
        for path in reversed(published):
            if originals[path] is None:
                path.unlink()
            else:
                path.write_bytes(originals[path])
        raise
    finally:
        for _, temporary in staged:
            temporary.unlink(missing_ok=True)


def generate_images(paths, args):
    paths = sorted(paths, key=lambda path: path.stem)
    validate_inputs(paths)
    widget = None
    if args.update_firmware:
        # The pinned LVGL stores its animation frame count in int8_t.
        if len(paths) > 127:
            raise ValueError("The Nice!View animation supports at most 127 images")
        widget = update_widget(
            args.peripheral_file.read_text(encoding="utf-8"),
            [path.stem for path in paths],
        )
    outputs = []
    total_bytes = 0
    with tempfile.TemporaryDirectory(prefix="niceview-images-") as directory:
        staged_args = copy(args)
        staged_args.outdir = directory
        for path in paths:
            out_path, nbytes = process_image(path, staged_args)
            outputs.append((Path(args.outdir) / out_path.name, out_path.read_bytes()))
            total_bytes += nbytes
        if args.update_firmware:
            art = ART_HEADER + "".join(content.decode("utf-8") + "\n" for _, content in outputs)
            outputs.extend(
                [
                    (args.art_file, art.encode("utf-8")),
                    (args.peripheral_file, widget.encode("utf-8")),
                ]
            )
        publish_files(outputs)
    return [path for path, _ in outputs], total_bytes


def to_1bpp(img, dither=True, invert=True):
    """Convert a PIL image to 1-bit;"""
    if dither:
        bw = img.convert("1")  # 1-bit with FS dither
    else:
        # Threshold
        bw = img.convert("L").point(lambda p: 255 if p >= 128 else 0, mode="1")
    if invert:
        bw = bw.point(lambda p: 255 - p, mode="1")
    return bw

def pack_bits_1bpp(img_1bit, lsb_first=False):
    """
    Pack a mode '1' image into bytes (8 pixels per byte).
    MSB-first (bit 7 is leftmost pixel) by default; LSB-first if requested.
    """
    if img_1bit.mode != "1":
        raise ValueError("pack_bits_1bpp expects a mode '1' image")
    w, h = img_1bit.size
    pix = img_1bit.load()
    out = bytearray()
    for y in range(h):
        bit_acc = 0
        bit_count = 0
        for x in range(w):
            bit = 1 if pix[x, y] == 255 else 0
            if lsb_first:
                bit_acc |= (bit & 1) << bit_count
            else:
                bit_acc = (bit_acc << 1) | (bit & 1)
            bit_count += 1
            if bit_count == 8:
                out.append(bit_acc & 0xFF)
                bit_acc = 0
                bit_count = 0
        if bit_count:
            if not lsb_first:
                bit_acc <<= (8 - bit_count)
            out.append(bit_acc & 0xFF)
    return bytes(out)

def make_macro_name(s: str) -> str:
    """Make a valid macro name (uppercase, only A-Z, 0-9, _) from a string."""
    return "".join(ch.upper() if ch.isalnum() else "_" for ch in s)

def emit_indexed1bit_lvgl_c_file(filename_stem, width, height, image_bytes, bytes_per_line=12):
    macro_name = make_macro_name(filename_stem)
    array_name = f"nice_view_art_data_{filename_stem}"
    img_var_name = image_symbol(filename_stem)

    # Conditional palette (index 0 / index 1) – unchanged from previous requirement.
    palette_block = """\
#if CONFIG_NICE_VIEW_WIDGET_INVERTED
    0xff, 0xff, 0xff, 0xff, /*Color of index 0*/
    0x00, 0x00, 0x00, 0xff, /*Color of index 1*/
#else
    0x00, 0x00, 0x00, 0xff, /*Color of index 0*/
    0xff, 0xff, 0xff, 0xff, /*Color of index 1*/
#endif
"""

    hexes = [f"0x{b:02X}" for b in image_bytes]
    lines = [", ".join(hexes[i:i+bytes_per_line]) for i in range(0, len(hexes), bytes_per_line)]
    image_array_literal = ",\n    ".join(lines)
    array_block = f"{palette_block}\n{image_array_literal}"

    c_content = f"""\
#ifndef LV_ATTRIBUTE_IMG_{macro_name}
#define LV_ATTRIBUTE_IMG_{macro_name}
#endif

const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_LARGE_CONST LV_ATTRIBUTE_IMG_{macro_name} uint8_t
    {array_name}[] = {{
    {array_block}
}};

const lv_img_dsc_t {img_var_name} = {{
    .header.cf = LV_IMG_CF_INDEXED_1BIT,
    .header.always_zero = 0,
    .header.reserved = 0,
    .header.w = {width},
    .header.h = {height},
    .data_size = sizeof({array_name}),
    .data = {array_name},
}};
"""
    return c_content

def process_image(path: Path, args):
    filename_stem = path.stem

    with Image.open(path) as im:
        im = im.convert("L")
        im = im.resize((args.width, args.height), Image.LANCZOS)

        if not args.no_rotate:
            im = im.transpose(Image.ROTATE_270)

        bw = to_1bpp(im, dither=not args.no_dither, invert=False)
        packed = pack_bits_1bpp(bw, lsb_first=args.lsb_first)

        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        out_c = outdir / f"{filename_stem}.c"

        final_w, final_h = (args.height, args.width) if not args.no_rotate else (args.width, args.height)

        c_file_contents = emit_indexed1bit_lvgl_c_file(filename_stem, final_w, final_h, packed, bytes_per_line=args.bytes_per_line)

        with open(out_c, "w", encoding="utf-8") as f:
            f.write(c_file_contents)

        return out_c, len(packed)

def main(argv=None):
    p = argparse.ArgumentParser(description="Convert images to 1bpp indexed LVGL arrays.")
    p.add_argument("inputs", nargs="*", help="Input image files (png/jpg/gif/bmp/...)")
    p.add_argument("--assets-dir", type=Path, help="Recursively discover images in this directory")
    p.add_argument("--outdir", default="out", help="Output directory (default: out)")
    p.add_argument("--width", type=int, default=68, help="Resize target width (default: 68)")
    p.add_argument("--height", type=int, default=140, help="Resize target height (default: 140)")
    p.add_argument("--no-dither", action="store_true", help="Disable Floyd–Steinberg dithering (use threshold)")
    p.add_argument("--lsb-first", action="store_true", help="Pack bits with LSB-first (bit 0 is leftmost pixel)")
    p.add_argument("--no-rotate", action="store_true", help="Do NOT rotate 90° clockwise")
    p.add_argument("--bytes-per-line", type=int, default=12, help="C array formatting: bytes per line")
    p.add_argument("--update-firmware", action="store_true", help="Also update art.c and peripheral_status.c")
    p.add_argument("--art-file", type=Path, default=WIDGET_DIRECTORY / "art.c")
    p.add_argument("--peripheral-file", type=Path, default=WIDGET_DIRECTORY / "peripheral_status.c")
    args = p.parse_args(argv)
    if args.assets_dir is not None and args.inputs:
        p.error("Use input filenames or --assets-dir, not both")
    if args.width <= 0 or args.height <= 0 or args.bytes_per_line <= 0:
        p.error("Width, height, and bytes per line must be positive")
    try:
        paths = discover_images(args.assets_dir) if args.assets_dir is not None else [
            Path(value) for value in args.inputs
        ]
        outputs, total_bytes = generate_images(paths, args)
    except (OSError, ValueError) as error:
        p.exit(1, f"error: {error}\n")

    print(f"Done. Wrote {len(outputs)} file(s), total {total_bytes} bytes of packed 1bpp data.")
    for o in outputs:
        print(f" - {o}")

if __name__ == "__main__":
    main()
