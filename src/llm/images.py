"""Build Anthropic image content blocks from files or raw bytes.

Vision calls take base64 image blocks. Keeping the encoding here means the
Designer agent stays agnostic about where images come from (upload, disk, URL),
and the logic is unit-testable without the network.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def media_type_for(path: str | Path) -> str:
    """Map a file extension to a Claude-supported image media type."""
    ext = Path(path).suffix.lower()
    try:
        return _MEDIA_TYPES[ext]
    except KeyError:
        raise ValueError(
            f"Unsupported image type '{ext}'. "
            f"Supported: {', '.join(sorted(set(_MEDIA_TYPES)))}"
        ) from None


def image_block_from_bytes(data: bytes, media_type: str) -> dict[str, Any]:
    """Wrap raw image bytes in an Anthropic base64 image content block."""
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.standard_b64encode(data).decode("ascii"),
        },
    }


def image_block_from_path(path: str | Path) -> dict[str, Any]:
    """Read an image file and return its Anthropic image content block."""
    path = Path(path)
    return image_block_from_bytes(path.read_bytes(), media_type_for(path))
