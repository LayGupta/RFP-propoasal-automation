"""test_rfp.py — File parser tests"""

from app.services.file_parser import extract_text_from_upload
import pytest


def test_extract_text_from_txt():
    content = b"This is a sample RFP document with cable specifications."
    result = extract_text_from_upload(content, "test.txt")
    assert "cable specifications" in result


def test_extract_text_empty_raises():
    with pytest.raises(ValueError, match="No text"):
        extract_text_from_upload(b"   ", "empty.txt")


def test_extract_text_fallback_decode():
    content = "Some UTF-8 text content with specs".encode("utf-8")
    result = extract_text_from_upload(content, "document.xyz")
    assert "specs" in result
