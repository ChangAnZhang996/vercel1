import re
from collections import Counter
from urllib.parse import urlparse

import jieba
import requests
from bs4 import BeautifulSoup

STOPWORDS = set([
    "的", "了", "在", "是", "我", "你", "他", "她", "它", "们", "就", "都", "而", "及", "与", "或",
    "也", "又", "不", "没", "有", "着", "过", "啊", "呀", "哦", "呢", "吧", "吗", "这", "那",
    "此", "彼", "之", "于", "以", "为", "因", "由", "随", "和", "跟", "同", "对", "对于", "关于",
    "还", "更", "最", "很", "非常", "比较", "稍微", "一点", "一些", "全部", "所有", "每个", "各个",
    "这里", "那里", "哪里", "怎么", "怎样", "如何", "什么", "为何", "因为", "所以", "但是", "然而",
    "如果", "假如", "要是", "只要", "只有", "既然", "尽管", "虽然", "即使", "倘使", "一旦", "当",
    "则", "便", "才", "刚", "正", "将", "会", "能", "可", "可以", "要", "应", "应该", "得",
    "到", "去", "来", "上来", "下去", "进来", "出去", "起来", "过来", "过去", "嗯", "哈",
    "哼", "哎", "喂", "呃", "网址", "链接", "页面", "内容", "文章", "作者", "发布", "时间",
    "一个", "两个", "三个", "四个", "五个", "几个", "多少", "若干", "其他", "另外", "还有", "以及"
])


def is_valid_url(url: str) -> bool:
    """检查是否为有效的 HTTP/HTTPS 链接。"""
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def fetch_web_text(url: str):
    """抓取网页正文，供 Vercel API 使用。"""
    if not url or not isinstance(url, str):
        return "", "请输入文章地址后再开始分析。"

    cleaned_url = url.strip()
    if not is_valid_url(cleaned_url):
        return "", "请输入一个有效的 http:// 或 https:// 链接。"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    try:
        response = requests.get(cleaned_url, headers=headers, timeout=25)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"

        soup = BeautifulSoup(response.text, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        body = soup.body
        if body is None:
            return "", "页面结构异常，未能提取到正文内容。"

        text = body.get_text(strip=True, separator="\n")
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        if not text or len(text) < 30:
            return "", "抓取到的内容过短，建议更换其他文章链接。"

        return text, None
    except requests.exceptions.Timeout:
        return "", "访问超时，请稍后重试或换一个响应更快的页面。"
    except requests.exceptions.ConnectionError:
        return "", "网络连接失败，请检查当前网络或页面是否可访问。"
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "未知"
        return "", f"页面请求失败（HTTP {status}），请确认链接是否正确。"
    except Exception as exc:
        return "", f"抓取网页内容时出现异常：{exc}"


def word_segment_and_count(text: str, min_freq: int):
    """中文分词并统计词频。"""
    words = jieba.lcut(text)
    filtered_words = [
        word for word in words
        if len(word) > 1 and word not in STOPWORDS and not re.match(r"^\d+$", word)
    ]
    word_count = Counter(filtered_words)
    word_count = {word: count for word, count in word_count.items() if count >= min_freq}
    sorted_word_count = dict(sorted(word_count.items(), key=lambda x: x[1], reverse=True))
    top20 = list(sorted_word_count.items())[:20]
    return sorted_word_count, top20
