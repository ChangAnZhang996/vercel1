import io
import json
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import jieba
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyecharts.options as opts
import requests
import streamlit as st
from bs4 import BeautifulSoup
from pyecharts.charts import Bar, Funnel, HeatMap, Line, Pie, Radar, Scatter, WordCloud
from streamlit_echarts import st_pyecharts

# ----------------------------
# 基础配置与样式
# ----------------------------
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False

HISTORY_FILE = Path(__file__).with_name("analysis_history.json")

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


def apply_theme_css():
    """应用响应式样式、配色方案与加载动画。"""
    st.markdown(
        """
        <style>
            :root {
                --bg: #edf8f0;
                --panel: rgba(255, 255, 255, 0.76);
                --panel-2: rgba(244, 255, 248, 0.88);
                --accent: #7ecf8a;
                --accent-2: #5aa967;
                --text: #1f3a29;
                --muted: #4b6655;
                --success: #5aa967;
            }
            html, body, [data-testid="stAppViewContainer"] {
                background: linear-gradient(135deg, #f2fff6 0%, #ebfff1 45%, #f7fff9 100%);
                color: var(--text);
            }
            [data-testid="stHeader"] { background: rgba(237, 248, 240, 0.92); backdrop-filter: blur(8px); }
            .block-container { padding-top: 1rem; padding-bottom: 2rem; }
            .card {
                background: rgba(255, 255, 255, 0.45);
                border: 1px solid rgba(126, 207, 138, 0.18);
                border-radius: 18px;
                padding: 1rem;
                box-shadow: none;
            }
            .badge { display: inline-block; padding: 0.25rem 0.55rem; border-radius: 999px; background: rgba(76, 175, 80, 0.12); color: #2e7d32; font-size: 0.9rem; border: 1px solid rgba(76, 175, 80, 0.22); }
            .stButton > button, .stDownloadButton > button {
                border-radius: 12px !important; border: 0 !important; background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important; color: #fff !important; box-shadow: 0 8px 18px rgba(126, 207, 138, 0.25) !important; transition: transform 0.15s ease, box-shadow 0.15s ease !important;
            }
            .stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-1px); box-shadow: 0 12px 24px rgba(90, 169, 103, 0.26) !important; }
            [data-testid="stSidebar"] .stButton > button {
                background: linear-gradient(135deg, #edf7ef, #dfeee2) !important;
                color: #2b5033 !important;
                border: 1px solid rgba(90, 169, 103, 0.18) !important;
                box-shadow: none !important;
            }
            .stTextInput > div > div > input, .stSelectbox > div > div, .stSlider > div > div { background: #ffffff !important; color: var(--text) !important; border-radius: 10px !important; border: 1px solid rgba(76, 175, 80, 0.18) !important; }
            .stAlert { border-radius: 14px !important; }
            .loading-shell { display: inline-flex; align-items: center; gap: 8px; color: var(--muted); }
            .loading-dot { width: 10px; height: 10px; border-radius: 50%; background: linear-gradient(135deg, var(--accent), var(--accent-2)); animation: pulse 1.2s infinite ease-in-out; }
            .loading-dot:nth-child(2) { animation-delay: 0.15s; }
            .loading-dot:nth-child(3) { animation-delay: 0.30s; }
            @keyframes pulse { 0%, 80%, 100% { transform: scale(0.8); opacity: 0.4; } 40% { transform: scale(1.1); opacity: 1; } }
            @media (max-width: 768px) {
                .block-container { padding-left: 0.7rem; padding-right: 0.7rem; }
                .card { padding: 0.8rem; border-radius: 14px; }
                [data-testid="stSidebar"] { width: 92vw !important; max-width: 320px; }
                .stTextInput > div > div > input { font-size: 0.98rem; }
                h1 { font-size: 1.6rem !important; }
                h2 { font-size: 1.15rem !important; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def is_valid_url(url: str) -> bool:
    """检查是否为有效的 HTTP/HTTPS 链接。"""
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def load_history() -> list:
    """从本地文件加载最近的分析历史。"""
    try:
        if not HISTORY_FILE.exists():
            return []
        with HISTORY_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_history_list(history: list) -> None:
    """将历史记录写回本地文件。"""
    with HISTORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def save_history(url: str, word_count: dict, top20: list, text_len: int) -> None:
    """保存最近 10 次分析记录。"""
    history = load_history()
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "url": url,
        "total_words": len(word_count),
        "text_len": text_len,
        "top20": top20,
        "summary": top20[:5] if top20 else [],
    }
    history.insert(0, entry)
    history = history[:10]
    save_history_list(history)


def fetch_web_text(url: str):
    """抓取网页内容，并提供更友好的错误提示。"""
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
    """中文分词并统计词频，过滤停用词与低频词。"""
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


def create_wordcloud(word_count: dict):
    """生成词云图。"""
    data = list(word_count.items())[:100]
    return (
        WordCloud()
        .add(series_name="词频", data_pair=data, word_size_range=[10, 100])
        .set_global_opts(
            title_opts=opts.TitleOpts(title="文章词汇词云图", title_textstyle_opts=opts.TextStyleOpts(font_size=20)),
            tooltip_opts=opts.TooltipOpts(trigger="item", formatter="{a} <br/>{b}: {c}")
        )
    )


def create_chart(chart_type: str, top20: list):
    """根据图表类型生成对应的图表。"""
    words = [item[0] for item in top20]
    counts = [item[1] for item in top20]

    if chart_type == "柱状图":
        return (
            Bar().add_xaxis(words).add_yaxis("词频", counts).reversal_axis().set_global_opts(
                title_opts=opts.TitleOpts(title="词频前20词汇柱状图", title_textstyle_opts=opts.TextStyleOpts(font_size=18)),
                xaxis_opts=opts.AxisOpts(name="词频"),
                yaxis_opts=opts.AxisOpts(name="词汇"),
                tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="shadow"),
            )
        )
    if chart_type == "折线图":
        return (
            Line().add_xaxis(words).add_yaxis("词频", counts, markpoint_opts=opts.MarkPointOpts(data=[opts.MarkPointItem(type_="max"), opts.MarkPointItem(type_="min")])).set_global_opts(
                title_opts=opts.TitleOpts(title="词频前20词汇折线图", title_textstyle_opts=opts.TextStyleOpts(font_size=18)),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-45)),
                yaxis_opts=opts.AxisOpts(name="词频"),
            )
        )
    if chart_type == "饼图":
        return (
            Pie().add("", list(zip(words, counts))).set_global_opts(
                title_opts=opts.TitleOpts(title="词频前20词汇饼图", title_textstyle_opts=opts.TextStyleOpts(font_size=18)),
                legend_opts=opts.LegendOpts(orient="vertical", pos_top="15%", pos_left="80%"),
            ).set_series_opts(tooltip_opts=opts.TooltipOpts(trigger="item", formatter="{b}: {c} ({d}%)"))
        )
    if chart_type == "雷达图":
        radar_words = words[:8]
        radar_counts = counts[:8]
        if not radar_words:
            return None
        max_val = max(radar_counts) if max(radar_counts) > 0 else 1
        schema = [opts.RadarIndicatorItem(name=word, max_=max_val) for word in radar_words]
        return Radar().add_schema(schema=schema).add("词频", [radar_counts]).set_global_opts(
            title_opts=opts.TitleOpts(title="词频前8词汇雷达图", title_textstyle_opts=opts.TextStyleOpts(font_size=18)),
            legend_opts=opts.LegendOpts(selected_mode="single"),
        )
    if chart_type == "散点图":
        return Scatter().add_xaxis(words).add_yaxis("词频", counts).set_global_opts(
            title_opts=opts.TitleOpts(title="词频前20词汇散点图", title_textstyle_opts=opts.TextStyleOpts(font_size=18)),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-45)),
            yaxis_opts=opts.AxisOpts(name="词频"),
        )
    if chart_type == "热力图":
        wx = words[:10]
        wy = words[:10]
        vc = counts[:10]
        if not wx or not vc:
            return None
        heat_data = [[i, j, vc[j]] for i in range(len(wx)) for j in range(len(wy))]
        return HeatMap().add_xaxis(wx).add_yaxis("词频", wy, heat_data).set_global_opts(
            title_opts=opts.TitleOpts(title="词频前10词汇热力图", title_textstyle_opts=opts.TextStyleOpts(font_size=18)),
            visualmap_opts=opts.VisualMapOpts(min_=min(vc), max_=max(vc)),
        )
    if chart_type == "漏斗图":
        return Funnel().add("词频", list(zip(words, counts))).set_global_opts(
            title_opts=opts.TitleOpts(title="词频前20词汇漏斗图", title_textstyle_opts=opts.TextStyleOpts(font_size=18)),
            tooltip_opts=opts.TooltipOpts(trigger="item", formatter="{b}: {c}"),
        )
    return None


def export_to_excel(word_count: dict, top20: list):
    """导出词频统计结果为 Excel 文件。"""
    full_df = pd.DataFrame(sorted(word_count.items(), key=lambda x: x[1], reverse=True), columns=["词汇", "词频"])
    top_df = pd.DataFrame(top20, columns=["词汇", "词频"])

    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            full_df.to_excel(writer, sheet_name="全部词频", index=False)
            top_df.to_excel(writer, sheet_name="TOP20", index=False)
        output.seek(0)
        return output
    except Exception as exc:
        st.error(f"Excel 导出失败：{exc}")
        return None


def render_analysis_result(result: dict, chart_type: str) -> None:
    """根据缓存结果渲染分析页面，支持切换图表而无需重新抓取。"""
    text = result["text"]
    word_count = result["word_count"]
    top20 = result["top20"]

    with st.expander("查看抓取到的文本（点击展开）", expanded=False):
        st.text_area("抓取内容预览", value=text, height=220)

    st.success(f"✅ 词频统计完成！共统计到 {len(word_count)} 个有效词汇")

    with st.expander("查看全部词频（点击展开）", expanded=False):
        md = "\n".join(f"- {w}: {c}" for w, c in word_count.items())
        st.markdown(md)

    st.subheader("🏆 词频排名前20的词汇")
    st.dataframe(pd.DataFrame(top20, columns=["词汇", "词频"]), use_container_width=True)

    st.subheader("☁️ 词汇词云图")
    st_pyecharts(create_wordcloud(word_count), width="100%", height="500px")

    st.subheader(f"📈 {chart_type}")
    chart = create_chart(chart_type, top20)
    if chart:
        st_pyecharts(chart, width="100%", height="500px")
    else:
        st.warning("当前图表类型暂不可用，请切换其他类型。")

    excel_file = export_to_excel(word_count, top20)
    if excel_file is not None:
        st.download_button(
            label="📥 导出词频结果为 Excel",
            data=excel_file.getvalue(),
            file_name="词频分析结果.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


def analyze_url(url: str, min_freq: int, chart_type: str):
    """执行抓取、分词、统计与可视化的完整流程。"""
    text, error = fetch_web_text(url)
    if error:
        st.warning(error)
        return None

    word_count, top20 = word_segment_and_count(text, min_freq)
    if not word_count:
        st.warning("分词结果为空，请适当降低筛选阈值后重试。")
        return None

    st.success("✅ 网页内容抓取成功，词频统计已完成。")

    with st.expander("查看抓取到的文本（点击展开）", expanded=False):
        st.text_area("抓取内容预览", value=text, height=220)

    st.success(f"✅ 词频统计完成！共统计到 {len(word_count)} 个有效词汇")

    with st.expander("查看全部词频（点击展开）", expanded=False):
        md = "\n".join(f"- {w}: {c}" for w, c in word_count.items())
        st.markdown(md)

    st.subheader("🏆 词频排名前20的词汇")
    top20_df = pd.DataFrame(top20, columns=["词汇", "词频"])
    st.dataframe(top20_df, use_container_width=True)

    save_history(url, word_count, top20, len(text))
    st.session_state["last_analysis"] = {"url": url, "text": text, "word_count": word_count, "top20": top20}

    st.subheader("☁️ 词汇词云图")
    st_pyecharts(create_wordcloud(word_count), width="100%", height="500px")

    st.subheader(f"📈 {chart_type}")
    chart = create_chart(chart_type, top20)
    if chart:
        st_pyecharts(chart, width="100%", height="500px")
    else:
        st.warning("当前图表类型暂不可用，请切换其他类型。")

    excel_file = export_to_excel(word_count, top20)
    if excel_file is not None:
        st.download_button(
            label="📥 导出词频结果为 Excel",
            data=excel_file.getvalue(),
            file_name="词频分析结果.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    return {"text": text, "word_count": word_count, "top20": top20}


def clear_url_input():
    """清空输入框、缓存结果与回看状态，避免残留旧分析。"""
    st.session_state["url_input"] = ""
    st.session_state["last_analysis"] = None
    st.session_state["auto_run"] = False
    st.rerun()


def select_history(url: str):
    """点击历史记录时加载该 URL 并触发重新分析。"""
    st.session_state["url_input"] = url
    st.session_state["auto_run"] = True


def main():
    st.set_page_config(page_title="文章词频分析工具", page_icon="📊", layout="wide", initial_sidebar_state="auto")
    apply_theme_css()

    st.markdown(
        "<div class='card'>"
        "<h1 style='margin-bottom:0.2rem; color:#1f3a29;'>📝 文章词频分析与可视化工具</h1>"
        "<p style='color:#4b6655; margin-top:0.2rem;'>支持网页抓取、词频统计、词云图、图表可视化、历史回看与 Excel 导出。</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption("💡 提示：页面已适配移动端显示，侧边栏会在手机上自动折叠，按钮与图表会自适应屏幕。", unsafe_allow_html=True)

    st.sidebar.title("🔧 筛选与设置")
    chart_types = ["柱状图", "折线图", "饼图", "雷达图", "散点图", "热力图", "漏斗图"]
    selected_chart = st.sidebar.selectbox("选择图表类型", chart_types, index=0)
    min_freq = st.sidebar.slider("低频词过滤阈值（最小词频）", min_value=1, max_value=10, value=2, step=1)

    history = load_history()
    st.sidebar.divider()
    st.sidebar.subheader("📚 最近分析历史（最多10条）")
    if history:
        for idx, item in enumerate(history):
            label = f"{item['timestamp']}｜{item['url'][:30]}..."
            c1, c2 = st.sidebar.columns([4, 1])
            with c1:
                c1.button(label, key=f"history_{idx}", use_container_width=True, on_click=select_history, args=(item["url"],))
            with c2:
                if c2.button("🗑", key=f"del_{idx}", help="删除这条历史记录", use_container_width=True):
                    history.pop(idx)
                    save_history_list(history)
                    st.rerun()
    else:
        st.sidebar.info("暂无历史记录，第一次分析后会自动保存。")

    st.sidebar.divider()
    st.sidebar.info("💡 点击左侧历史记录，可快速重新分析。")

    url = st.text_input("请输入文章URL", key="url_input", placeholder="例如：https://www.ncda.org.cn/list-7-1.html?typeid=55")
    col1, col2 = st.columns([1, 1])
    with col1:
        analyze_btn = st.button("🚀 开始分析", type="primary", use_container_width=True)
    with col2:
        clear_btn = st.button("🧹 清空输入", on_click=clear_url_input, use_container_width=True)

    last_analysis = st.session_state.get("last_analysis")
    if last_analysis and last_analysis.get("url") == url and not analyze_btn and not st.session_state.get("auto_run"):
        render_analysis_result(last_analysis, selected_chart)
        return

    if st.session_state.get("auto_run"):
        st.session_state["auto_run"] = False
        with st.spinner("正在回看历史记录并重新分析..."):
            time.sleep(0.2)
            analyze_url(st.session_state.get("url_input", url), min_freq, selected_chart)
        return

    if analyze_btn and url:
        with st.spinner("正在抓取网页内容并分析，请稍候..."):
            time.sleep(0.2)
            analyze_url(url, min_freq, selected_chart)
    elif analyze_btn and not url:
        st.warning("请输入有效的文章URL后再开始分析。")


if __name__ == "__main__":
    main()
