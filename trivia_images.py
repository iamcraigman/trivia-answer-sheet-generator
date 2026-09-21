"""Turns uploaded pictures into small grayscale inline images for printing."""
import base64
import io

from PIL import Image, ImageOps

LOGO_MAX_PX = 300
PICTURE_MAX_PX = 700


def to_data_uri(data, max_px):
    """Return a grayscale JPEG `data:` URI no larger than `max_px` on a side.

    Raises ValueError if `data` is not a readable image.
    """
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            flat = Image.new("RGBA", img.size, "white")
            flat.alpha_composite(img)
            img = flat
        img = img.convert("L")
        img.thumbnail((max_px, max_px))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=82)
    except Exception as exc:  # Pillow raises many different types for bad input
        raise ValueError("Couldn't read that file as an image.") from exc
    return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode("ascii")
