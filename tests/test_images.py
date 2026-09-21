import base64
import io

import pytest
from PIL import Image

from trivia_images import to_data_uri


def png(size=(1200, 400), mode="RGB", color=(200, 30, 30)):
    out = io.BytesIO()
    Image.new(mode, size, color).save(out, format="PNG")
    return out.getvalue()


def decode(uri):
    assert uri.startswith("data:image/jpeg;base64,")
    return Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1])))


def test_result_is_a_small_grayscale_jpeg():
    img = decode(to_data_uri(png(), 300))
    assert img.mode == "L"
    assert img.size == (300, 100)                # longest side capped, aspect ratio kept


def test_small_images_are_not_enlarged():
    assert decode(to_data_uri(png((40, 20)), 300)).size == (40, 20)


def test_transparent_areas_become_white():
    img = decode(to_data_uri(png((10, 10), "RGBA", (0, 0, 0, 0)), 300))
    assert img.getpixel((5, 5)) > 240


@pytest.mark.parametrize("junk", [b"", b"not an image", b"<svg></svg>", b"\x89PNG\r\n\x1a\ntruncated"])
def test_unreadable_files_raise_value_error(junk):
    with pytest.raises(ValueError):
        to_data_uri(junk, 300)
