import pytest

from app.tools.web import *


def test_extract_host():
    assert extract_host("https://github.com/ABCD") == "github.com"


def test_extract_title():
    # 其他Error
    assert extract_title("not URL") == "not URL"


def test_parse_encoding():
    assert parse_encoding("<meta charset=\"utf-8\">", 'gbk') == 'utf-8'
    assert parse_encoding("<meta charset='utf-8'>", 'gbk') == 'utf-8'
    assert parse_encoding("<meta name=\"viewport\" content=\"width=device-width\">", 'utf-8') == 'utf-8'
    assert parse_encoding("", 'gbk') == 'gbk'


def test_parse_title():
    assert parse_title("<title>LiZeC的博客</title>") == "LiZeC的博客"

    with pytest.raises(Exception):
        assert parse_title("not a title")

    with pytest.raises(Exception):
        assert parse_title("")


