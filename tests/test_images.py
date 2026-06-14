"""Offline tests for image-block encoding (no network)."""
import base64

import pytest

from src.llm.images import image_block_from_bytes, image_block_from_path, media_type_for


def test_media_type_for_known_extensions():
    assert media_type_for("a.jpg") == "image/jpeg"
    assert media_type_for("a.JPEG") == "image/jpeg"
    assert media_type_for("a.png") == "image/png"
    assert media_type_for("a.webp") == "image/webp"


def test_media_type_for_rejects_unknown():
    with pytest.raises(ValueError):
        media_type_for("a.bmp")


def test_image_block_from_bytes_shape_and_base64():
    block = image_block_from_bytes(b"hello", "image/png")
    assert block["type"] == "image"
    assert block["source"]["type"] == "base64"
    assert block["source"]["media_type"] == "image/png"
    assert base64.standard_b64decode(block["source"]["data"]) == b"hello"


def test_image_block_from_path_reads_file(tmp_path):
    f = tmp_path / "ref.png"
    f.write_bytes(b"\x89PNG\r\n\x1a\n fake")
    block = image_block_from_path(f)
    assert block["source"]["media_type"] == "image/png"
    assert base64.standard_b64decode(block["source"]["data"]) == b"\x89PNG\r\n\x1a\n fake"
