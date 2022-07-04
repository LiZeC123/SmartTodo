from tool4web import *


def test_extract_host():
    assert extract_host("https://github.com/ABCD") == "github.com"


def test_extract_title():
    assert extract_title("https://lizec.top/") == "LiZeC的博客"
