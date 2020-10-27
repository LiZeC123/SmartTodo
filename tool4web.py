from urllib.parse import urlparse

from tool4log import logger

timeout = 10
headers = {"User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9.1.6) ",
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "en-us",
           "Connection": "keep-alive",
           "Accept-Charset": "GB2312,utf-8;q=0.7,*;q=0.7"}


def extract_host(url: str) -> str:
    parse = urlparse(url)
    return parse.netloc


# noinspection PyBroadException
def extract_title(url: str) -> str:
    import requests
    from requests import HTTPError
    from bs4 import BeautifulSoup

    host = extract_host(url)
    if host != "":
        headers['Host'] = host

    try:
        r = requests.get(url, timeout=timeout, headers=headers)
        r.raise_for_status()  # 判断状态
        r.encoding = r.apparent_encoding
        obj = BeautifulSoup(r.text, "lxml")
        return obj.head.title.get_text()
    except HTTPError:
        logger.exception("Tool4Web: unknown HttpError")
        return str(host)
    except Exception:
        # 如果出现其他解析错误 返回Host
        logger.exception("Tool4Web: unknown Error")
        return str(host)


def download(url: str, base_dir: str):
    import wget
    return wget.download(url=url, out=base_dir)


def log_bar(current, total):
    import wget
    logger.info(f"")
    return wget.bar_adaptive(current=current, total=total)


if __name__ == '__main__':
    pass
