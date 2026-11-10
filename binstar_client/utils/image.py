from __future__ import annotations

import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from os import PathLike
    from pathlib import Path
    from typing import IO

import png

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

from ..errors import PillowNotInstalled


THUMB_SIZE = (340, 210)


def resize_and_convert(path_or_buffer: str | bytes | PathLike[str] | PathLike[bytes] | IO[bytes]) -> io.BytesIO:
    """
    Fits an image into a bounding box while preserving ratio.
    If Pillow is not available, uses pypng for a simpler fallback.
    """
    if Image is None:
        # For known .png paths, we can fallback to pypng
        if isinstance(path_or_buffer, (str, Path)):
            if str(path_or_buffer).lower().endswith(".png"):
                return _resize_and_convert_pypng(path_or_buffer)
        raise PillowNotInstalled()
    image = Image.open(path_or_buffer)
    image.thumbnail(THUMB_SIZE)
    out = io.BytesIO()
    image.save(out, format='png')
    out.seek(0)
    # Comment this out to check written file
    # with open("out-pillow.png", "wb") as f:
    #     image.save(f, format="png")
    return out


def _resize_and_convert_pypng(path: str | Path) -> io.BytesIO:
    """
    pypng is pretty barebones when it comes to processing; it only
    handles decoding and encoding for us. Everything else is done
    needs to be done by hand on the pixel data.

    Pillow's Image.thumbnail() resizes without distorion. IOW,
    THUMB_SIZE is a bounding box. Pillow also defaults to bicubic
    downsampling (prettier), here we are only doing nearest neighbor,
    which is simpler but will result in less pretty outputs.
    """
    reader = png.Reader(filename=str(path))
    width, height, rows, info = reader.read()
    pixels = [list(row) for row in rows]
    planes = info['planes']  # 3 for RGB, 4 for RGBA

    x, y = THUMB_SIZE
    if width <= x and height <= y:
        # Already smaller, keep as is
        new_width, new_height = width, height
        scaled_pixels = pixels
    else:
        # Find dimensions in bounding box that preserve ratio
        aspect = width / height
        if x / y >= aspect:
            new_width = int(round(y * aspect))
            new_height = y
        else:
            new_width = x
            new_height = int(round(x / aspect))

        # downscale using nearest-neighbor
        scaled_pixels = []
        for out_y in range(new_height):
            orig_y = int(out_y * height / new_height)
            row = []
            for out_x in range(new_width):
                orig_x = int(out_x * width / new_width)
                start = orig_x * planes
                row.extend(pixels[orig_y][start : start + planes])
            scaled_pixels.append(row)

    out = io.BytesIO()
    info.pop("size", None)
    writer = png.Writer(width=new_width, height=new_height, **info)
    writer.write(out, scaled_pixels)
    out.seek(0)
    # Comment this out to check written file
    # with open("out-pypng.png", "wb") as f:
    #     writer.write(f, scaled_pixels)
    return out
