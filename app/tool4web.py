import html
from urllib.parse import urlparse
import re

import requests
from requests import HTTPError
from requests import Response
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
        r.encoding = parse_encoding(r)
        title = parse_title(r)
        return title
    except HTTPError:
        logger.exception(f"Tool4Web: Unknown HttpError for URL {url}")
        return url
    except Exception:
        # 如果出现其他解析错误 返回Host
        logger.exception(f"Tool4Web: Unknown Exception for URL {url}")
        return url


def parse_encoding(r: Response) -> str:
    match = encoding_pattern.search(r.text)
    if match:
        encoding = match.group(1)
        encoding = encoding.replace('"', "").replace("'", "").strip()
    else:
        encoding = r.apparent_encoding
    return encoding


def parse_title(r: Response) -> str:
    match = title_pattern.search(r.text)
    if match:
        title = match.group(1)
        return html.unescape(title)  # 解析#&格式编码的字符
    else:
        raise Exception("HTML file not contain title tag")


def download(url: str, base_dir: str):
    return wget.download(url=url, out=base_dir)


if __name__ == '__main__':
    pass
