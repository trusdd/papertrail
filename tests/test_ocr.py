from pathlib import Path

import pytest

from papertrail.ocr import detect_language


@pytest.mark.parametrize(
    "text,expected",
    [
        ("", "unknown"),
        ("   ", "unknown"),
        ("hello world", "eng"),
        ("Привет мир", "rus"),
        ("Hello Привет", "rus"),
    ],
)
def test_detect_language(text: str, expected: str) -> None:
    assert detect_language(text) == expected


def test_detect_language_numbers_only() -> None:
    assert detect_language("12345 !!!") == "unknown"
