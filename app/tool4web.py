import html
import re
from urllib.parse import urlparse

import requests
import wget

from tool4log import logger

timeout = 3
headers = {"User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9.1.6) ",
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "en-us",
           "Connection": "keep-alive",
           }

title_pattern = re.compile("<title.*?>(.*?)</title>")
encoding_pattern = re.compile('<meta charset=(.*?)>')


def extract_host(url: str) -> str:
    parse = urlparse(url)
    return parse.netloc


# noinspection PyBroadException
def extract_title(url: str) -> str:
    host = extract_host(url)
    if host != "":
        headers['Host'] = host

    try:
        r = requests.get(url, timeout=timeout, headers=headers)
        r.raise_for_status()  # 判断状态
        r.encoding = parse_encoding(r.text, r.apparent_encoding)
        title = parse_title(r.text)
        return title
    except Exception as e:
        # 如果出现其他解析错误 返回Host
        logger.exception(e)
        return url


def parse_encoding(text: str, apparent_encoding: str) -> str:
    match = encoding_pattern.search(text)
    encoding = apparent_encoding
    if match:
        encoding = match.group(1)
        encoding = encoding.strip("'\"")
    return encoding


def parse_title(text: str) -> str:
    match = title_pattern.search(text)
    if match:
        title = match.group(1)
        return html.unescape(title)  # 解析#&格式编码的字符
    else:
        raise Exception("HTML file not contain title tag")


def download(url: str, base_dir: str):
    return wget.download(url=url, out=base_dir)
