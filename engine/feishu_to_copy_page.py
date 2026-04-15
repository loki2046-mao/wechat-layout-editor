#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import html
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / "自研公众号排版"
DEFAULT_FOOTER = ROOT / "签名图.png"

THEMES = {
    "赤铜橙": {
        "accent": "#B8623C", "warmBg": "#fff8f1", "warmPill": "#f5e0c5",
        "warmBorder": "#ead8c2", "warmLine": "#d6ab81", "warmPanel": "#fcf4ea",
        "warmPanelSoft": "#fff8ef",
        "ink": "#201a16", "text": "#4d443b", "muted": "#7c7065",
        "accent_soft": "#f8efe4", "line": "#eadac8", "paper": "#fffdfa", "paper_deep": "#fbf5ee",
    },
    "青石蓝": {
        "accent": "#4A7B9D", "warmBg": "#f0f5f8", "warmPill": "#d4e6f0",
        "warmBorder": "#b8d4e3", "warmLine": "#7ab0cc", "warmPanel": "#e8f0f5",
        "warmPanelSoft": "#edf3f7",
        "ink": "#1a2530", "text": "#3b4d5a", "muted": "#657c8a",
        "accent_soft": "#e4eff6", "line": "#c8dce8", "paper": "#fafcfd", "paper_deep": "#eef5f9",
    },
    "松绿": {
        "accent": "#3D8B6E", "warmBg": "#f0f8f4", "warmPill": "#d0ebde",
        "warmBorder": "#b2d8c5", "warmLine": "#6db898", "warmPanel": "#e5f3ec",
        "warmPanelSoft": "#eaf5ef",
        "ink": "#162a20", "text": "#3b4d44", "muted": "#657c70",
        "accent_soft": "#e2f2ea", "line": "#c5ddd0", "paper": "#fafdfc", "paper_deep": "#eef7f2",
    },
    "玫瑰红": {
        "accent": "#B85A6C", "warmBg": "#fdf2f4", "warmPill": "#f5d4da",
        "warmBorder": "#eac2c8", "warmLine": "#d68a98", "warmPanel": "#fae8eb",
        "warmPanelSoft": "#fceef0",
        "ink": "#2a161a", "text": "#4d3b40", "muted": "#7c656a",
        "accent_soft": "#f6e4e8", "line": "#eacdd2", "paper": "#fffafb", "paper_deep": "#f9eef0",
    },
    "琥珀黄": {
        "accent": "#B8923C", "warmBg": "#fdf8f0", "warmPill": "#f5e8c5",
        "warmBorder": "#eadcc2", "warmLine": "#d6c081", "warmPanel": "#f8f0e2",
        "warmPanelSoft": "#faf4e8",
        "ink": "#201a10", "text": "#4d4430", "muted": "#7c7050",
        "accent_soft": "#f6efe0", "line": "#eadcc2", "paper": "#fffdf8", "paper_deep": "#f8f2e6",
    },
    "石墨灰": {
        "accent": "#6B7280", "warmBg": "#f5f5f6", "warmPill": "#e0e2e5",
        "warmBorder": "#d1d5db", "warmLine": "#9ca3af", "warmPanel": "#ebedf0",
        "warmPanelSoft": "#eff0f2",
        "ink": "#1f2022", "text": "#3d3f44", "muted": "#6b6d75",
        "accent_soft": "#e8eaed", "line": "#d1d5db", "paper": "#fbfbfc", "paper_deep": "#f0f1f3",
    },
}

PALETTE = {
    "ink": "#201a16",
    "text": "#4d443b",
    "muted": "#7c7065",
    "accent": "#B8623C",
    "accent_soft": "#f8efe4",
    "line": "#eadac8",
    "paper": "#fffdfa",
    "paper_deep": "#fbf5ee",
}

WARM_BORDER = "#ead8c2"
WARM_PANEL = "#fcf4ea"
WARM_PANEL_SOFT = "#fff8ef"
WARM_PILL = "#f1dfcb"
WARM_LINE = "#d6ab81"

EMPHASIS_HINTS = (
    "本质",
    "关键",
    "核心",
    "重点",
    "前提",
    "门槛",
    "麻烦",
    "适合",
    "不适合",
    "值不值得",
    "真正",
    "普通人",
    "新手",
)

EMPHASIS_STOPWORDS = {
    "这个",
    "那个",
    "这里",
    "然后",
    "其实",
    "就是",
    "要求",
    "目标",
    "问题",
    "页面主题",
    "输出要求",
    "视觉要求",
    "技术要求",
}

ROLE_PREFIXES = (
    "你现在是一位",
    "你是一位",
    "你是一名",
    "请帮我",
    "请你",
    "请直接",
    "请围绕",
    "请为我",
)

FIELD_MARKERS = {
    "技术要求:",
    "页面主题:",
    "目标气质:",
    "视觉要求:",
    "输出要求:",
    "代码质量要求:",
    "项目背景:",
    "输出结构:",
    "要求:",
}

RESUME_MARKERS = (
    "(此处有视频)",
    "我觉得颜色有点太AI",
    "这个方案的输出也有",
    "然后再看看大家都很关心的生图",
    "真正让我眼前一亮的",
    "想看全文的后台发",
    "直接看效果",
)

UI_NOISE = (
    "登录/注册",
    "最新修改时间",
    "与我分享",
    "飞书云文档",
    "赛博小熊猫",
)

INTRO_KEYWORD_STOPWORDS = {
    "",
    "今天",
    "这篇",
    "一个",
    "一些",
    "我们",
    "你们",
    "他们",
    "自己",
    "一下",
    "这种",
    "那个",
    "这个",
    "什么",
    "为什么",
    "怎么",
    "然后",
    "如果",
    "但是",
    "因为",
    "以及",
    "已经",
    "还是",
    "就是",
    "不是",
    "真的",
    "内容",
    "主题",
    "标题",
    "文章",
    "导读",
}

INTRO_SEQUENCE_LABEL_RE = re.compile(
    r"^(?:case|案例|章节|chapter|section|part|step)\s*[\-_.::、]?\s*[0-9一二三四五六七八九十ivxIVX]+(?:\s*[::.\-、]\s*.*)?$",
    re.IGNORECASE,
)


MARK_SCROLL_ROOT_JS = r"""
() => {
  const candidates = Array.from(document.querySelectorAll("*"))
    .map((el) => {
      const style = getComputedStyle(el);
      const overflowY = style.overflowY;
      const delta = el.scrollHeight - el.clientHeight;
      const rect = el.getBoundingClientRect();
      const score =
        Math.max(delta, 0) +
        (/(auto|scroll)/.test(overflowY) ? 400 : 0) +
        Math.max(rect.width - 400, 0);
      return { el, score, delta, width: rect.width };
    })
    .filter((item) => item.delta > 600 && item.width > 420)
    .sort((a, b) => b.score - a.score);

  const root = candidates[0]?.el || document.scrollingElement || document.body;
  root.setAttribute("data-codex-scroll-root", "1");
  return {
    scrollHeight: root.scrollHeight,
    clientHeight: root.clientHeight,
  };
}
"""


COLLECT_BLOCKS_JS = r"""
() => {
  const root = document.querySelector('[data-codex-scroll-root="1"]');
  const scrollTop = root ? root.scrollTop : window.scrollY;
  const anchorLeft = (document.querySelector("h1")?.getBoundingClientRect().left || 0) - 80;

  const isVisible = (el) => {
    const rect = el.getBoundingClientRect();
    if (rect.width < 32 || rect.height < 10) return false;
    if (rect.bottom < -220 || rect.top > window.innerHeight + 260) return false;
    // 排除左侧目录/导航栏区域(anchorLeft 是正文左边界,左侧内容全过滤掉)
    if (rect.right < anchorLeft) return false;
    if (rect.left < anchorLeft - 20) return false;
    const style = getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity || "1") === 0) {
      return false;
    }
    // 排除 position:fixed 的元素(飞书顶部 toolbar、目录悬浮栏等)
    if (style.position === "fixed") return false;
    return true;
  };

  const meaningfulChildText = (el) => {
    return Array.from(el.children).some((child) => {
      if (!isVisible(child)) return false;
      const text = (child.innerText || "").trim();
      if (!text) return false;
      const display = getComputedStyle(child).display;
      return !["inline", "inline-block", "contents"].includes(display);
    });
  };

  const isOrangeYellowColor = (bg) => {
    if (!bg || bg === "transparent" || bg === "rgba(0, 0, 0, 0)") return false;
    const m = bg.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (!m) return false;
    const [r, g, b] = [+m[1], +m[2], +m[3]];
    if (r > 200 && g > 140 && b < 120 && r > g) return true;
    if (r > 240 && g > 220 && b > 180 && b < 230) return true;
    return false;
  };

  // 找飞书高亮色块的最外层容器:向上找到背景色为橙黄的最高层元素
  const findHighlightContainer = (el) => {
    let candidate = null;
    let cur = el;
    for (let depth = 0; depth < 10; depth++) {
      if (!cur || cur === document.body) break;
      const bg = getComputedStyle(cur).backgroundColor;
      if (isOrangeYellowColor(bg)) {
        candidate = cur;
      }
      cur = cur.parentElement;
    }
    return candidate;
  };

  // 收集所有橙黄色容器(去重,只取最外层)
  const highlightContainers = new Set();
  for (const el of document.querySelectorAll("*")) {
    const bg = getComputedStyle(el).backgroundColor;
    if (!isOrangeYellowColor(bg)) continue;
    const rect = el.getBoundingClientRect();
    if (rect.width < 100 || rect.height < 20) continue;
    // 找最外层容器
    const container = findHighlightContainer(el) || el;
    highlightContainers.add(container);
  }
  // 过滤:只保留没有被更外层橙黄容器包含的(最外层)
  const outerContainers = new Set();
  for (const c of highlightContainers) {
    let dominated = false;
    for (const other of highlightContainers) {
      if (other !== c && other.contains(c)) { dominated = true; break; }
    }
    if (!dominated) outerContainers.add(c);
  }

  // 检查某个元素是否在高亮容器内部
  const insideHighlightContainer = (el) => {
    for (const c of outerContainers) {
      if (c !== el && c.contains(el)) return c;
    }
    return null;
  };

  const classify = (el, text) => {
    const tag = el.tagName.toUpperCase();
    const style = getComputedStyle(el);
    const fontSize = parseFloat(style.fontSize || "0");
    const fontWeight = parseInt(style.fontWeight || "400", 10) || 400;
    if (tag === "H1") return "title";
    if (/^\d{1,2}月\d{1,2}日/.test(text)) return "meta";
    if (/^最新修改时间/.test(text)) return "meta";
    if (tag.startsWith("H")) return "heading";
    if (fontSize >= 23) return "heading";
    if (fontWeight >= 650 && text.length <= 26 && !/[。!?;,,.!?]$/.test(text)) return "heading";
    return "text";
  };

  const blocks = [];

  // 先把所有橙黄容器作为整体 highlight block 推入
  const pushedContainers = new Set();
  for (const container of outerContainers) {
    if (!isVisible(container)) continue;
    const text = (container.innerText || "").trim();
    if (!text) continue;
    const rect = container.getBoundingClientRect();
    blocks.push({
      type: "highlight",
      text,
      top: Math.round(rect.top + scrollTop),
      left: Math.round(rect.left),
      fontSize: 14,
      fontWeight: 400,
    });
    pushedContainers.add(container);
  }

  for (const img of document.querySelectorAll("img")) {
    if (!isVisible(img)) continue;
    const rect = img.getBoundingClientRect();
    const src = img.currentSrc || img.src || "";
    if (!src) continue;
    blocks.push({
      type: "image",
      src,
      alt: img.alt || "",
      width: img.naturalWidth || Math.round(rect.width),
      height: img.naturalHeight || Math.round(rect.height),
      top: Math.round(rect.top + scrollTop),
      left: Math.round(rect.left),
    });
  }

  for (const el of document.querySelectorAll("h1,h2,h3,h4,h5,h6,p,li,blockquote,pre,code,div,section,span")) {
    if (!isVisible(el)) continue;
    if (el.tagName.toUpperCase() === "IMG") continue;
    if (el.querySelector("img")) continue;
    if (meaningfulChildText(el)) continue;
    // 跳过已作为整体处理的橙黄容器内部元素
    if (insideHighlightContainer(el)) continue;
    // 跳过橙黄容器本身(已经在上面推入了)
    if (pushedContainers.has(el)) continue;
    const text = (el.innerText || "").trim();
    if (!text) continue;
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    blocks.push({
      type: classify(el, text),
      text,
      top: Math.round(rect.top + scrollTop),
      left: Math.round(rect.left),
      fontSize: parseFloat(style.fontSize || "0") || 0,
      fontWeight: parseInt(style.fontWeight || "400", 10) || 400,
    });
  }

  blocks.sort((a, b) => (a.top - b.top) || (a.left - b.left));
  return {
    title: (document.querySelector("h1")?.innerText || document.title || "").trim(),
    blocks,
  };
}
"""


FETCH_IMAGE_JS = r"""
async ({ sources, timeoutMs }) => {
  const fetchOne = async (src) => {
    if (!src || src.startsWith("data:")) {
      return { src, ok: true, passthrough: true };
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort("timeout"), timeoutMs);
    try {
      const response = await fetch(src, {
        credentials: "include",
        signal: controller.signal,
      });
      if (!response.ok) {
        return { src, ok: false, error: `http:${response.status}` };
      }
      const type = response.headers.get("content-type") || "image/png";
      const buffer = await response.arrayBuffer();
      const bytes = new Uint8Array(buffer);
      let binary = "";
      const step = 0x8000;
      for (let i = 0; i < bytes.length; i += step) {
        binary += String.fromCharCode(...bytes.slice(i, i + step));
      }
      return {
        src,
        ok: true,
        type,
        b64: btoa(binary),
      };
    } catch (error) {
      return { src, ok: false, error: String(error) };
    } finally {
      clearTimeout(timer);
    }
  };

  return Promise.all((sources || []).map(fetchOne));
}
"""


def escape_text(text: str) -> str:
  return html.escape(text)


def clean_text(text: str) -> str:
  return text.replace("\u200b", "").replace("\ufeff", "").replace("\xa0", " ").strip()


def normalize_text(text: str) -> str:
  return re.sub(r"\s+", " ", clean_text(text))


def truncate_text(text: str, limit: int) -> str:
  normalized = normalize_text(text)
  if len(normalized) <= limit:
    return normalized
  return normalized[: max(limit - 1, 1)].rstrip(",。!?、;:,.!?;: ") + "..."


def split_keyword_candidates(text: str) -> list[str]:
  normalized = normalize_text(text)
  if not normalized:
    return []
  return [
    part.strip("·#-- ")
    for part in re.split(r"[||/、,,。::;;""\"'''《》【】()()\s]+", normalized)
    if part.strip("·#-- ")
  ]


def text_from_block_for_intro(block: dict) -> str:
  block_type = block.get("type")
  if block_type in {"text", "heading", "subheading", "quote", "highlight", "meta"}:
    return normalize_text(block.get("text", ""))
  if block_type == "prompt":
    label = normalize_text(block.get("label", ""))
    if label:
      return label
    lines = [normalize_text(line) for line in str(block.get("text", "")).splitlines() if normalize_text(line)]
    return lines[0] if lines else ""
  if block_type == "list":
    items = [normalize_text(item) for item in block.get("items", []) if normalize_text(item)]
    return ";".join(items[:3])
  if block_type == "group":
    texts: list[str] = []
    for item in block.get("items", []):
      title = normalize_text(item.get("title", ""))
      body = normalize_text(item.get("text", ""))
      joined = ":".join(part for part in [title, body] if part)
      if joined:
        texts.append(joined)
    return ";".join(texts[:3])
  if block_type == "video":
    return normalize_text(block.get("title", "")) or normalize_text(block.get("summary", ""))
  if block_type == "hero":
    return normalize_text(block.get("summary", "")) or normalize_text(block.get("title", ""))
  return ""


def is_intro_sequence_label(text: str) -> bool:
  normalized = normalize_text(text)
  if not normalized:
    return False
  return bool(INTRO_SEQUENCE_LABEL_RE.match(normalized))


def intro_source_blocks(blocks: list[dict], *, max_items: int = 8) -> list[dict]:
  source: list[dict] = []
  heading_seen = 0
  for block in blocks:
    block_type = block.get("type")
    if block_type == "hero":
      continue
    if block_type == "image":
      if source:
        break
      continue
    text = text_from_block_for_intro(block)
    if is_intro_sequence_label(text):
      continue
    if block_type in {"heading", "subheading"}:
      heading_seen += 1
      if source and heading_seen >= 2:
        break
    source.append(block)
    if len(source) >= max_items:
      break
  return source or [block for block in blocks if block.get("type") != "hero"][:max_items]


def infer_intro_category(blocks: list[dict]) -> str:
  if any(block.get("type") == "video" for block in blocks):
    return "视频类"
  if any(block.get("type") == "prompt" for block in blocks):
    return "提示词类"
  image_count = sum(1 for block in blocks if block.get("type") == "image")
  if image_count >= 3:
    return "图片类"
  if any(block.get("type") in {"group", "list"} for block in blocks):
    return "结构类"
  return "观点类"


def infer_intro_keywords(title: str, blocks: list[dict]) -> list[str]:
  picked: list[str] = []
  source_blocks = intro_source_blocks(blocks)

  def add(keyword: str) -> None:
    normalized = normalize_text(keyword)
    if not normalized or normalized in picked or normalized in INTRO_KEYWORD_STOPWORDS:
      return
    if len(normalized) < 2 or len(normalized) > 12:
      return
    if is_intro_sequence_label(normalized):
      return
    picked.append(normalized)

  for piece in split_keyword_candidates(title):
    add(piece)

  for block in source_blocks:
    if block.get("type") in {"heading", "subheading", "highlight"}:
      add(text_from_block_for_intro(block))
    for piece in split_keyword_candidates(text_from_block_for_intro(block)):
      add(piece)
      if len(picked) >= 5:
        return picked[:5]

  return picked[:5] or [infer_intro_category(blocks), "主题拆解", "视觉重点"]


def infer_intro_summary(title: str, blocks: list[dict]) -> str:
  fragments: list[str] = []
  source_blocks = intro_source_blocks(blocks)
  priority_types = {"text", "quote", "highlight", "prompt"}
  for block in source_blocks:
    if block.get("type") not in priority_types:
      continue
    text = text_from_block_for_intro(block)
    if len(text) < 8:
      continue
    if is_intro_sequence_label(text):
      continue
    fragments.append(text)
    if len(fragments) >= 2:
      break

  if not fragments:
    for block in source_blocks:
      text = text_from_block_for_intro(block)
      if not text:
        continue
      if is_intro_sequence_label(text):
        continue
      fragments.append(text)
      if len(fragments) >= 2:
        break

  summary = " ".join(fragments).strip()
  if not summary:
    return ""
  return truncate_text(summary, 88)


def pick_intro_visual(blocks: list[dict]) -> tuple[str, str]:
  for block in intro_source_blocks(blocks, max_items=12):
    if block.get("type") == "image" and normalize_text(block.get("src", "")):
      return block.get("src", ""), normalize_text(block.get("alt", "")) or "今日主题视觉"
  return "", "今日主题视觉"


def ensure_intro_card(title: str, blocks: list[dict]) -> list[dict]:
  if blocks and blocks[0].get("type") == "hero":
    return blocks
  category = infer_intro_category(blocks)
  keywords = infer_intro_keywords(title, blocks)
  image_src, image_alt = pick_intro_visual(blocks)
  hero_block = {
    "type": "hero",
    "title": normalize_text(title) or "未命名文章",
    "category": category,
    "theme": keywords[0] if keywords else category,
    "summary": infer_intro_summary(title, blocks),
    "keywords": keywords,
    "image_src": image_src,
    "image_alt": image_alt,
  }
  return [hero_block, *blocks]


def canonicalize_src(src: str) -> str:
  parts = urlsplit(src)
  query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key not in {"width", "height", "policy", "format"}]
  return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def slugify(text: str) -> str:
  cleaned = re.sub(r'[\\/:*?"<>|]+', " ", clean_text(text))
  cleaned = re.sub(r"\s+", " ", cleaned).strip()
  return cleaned or "未命名文章"


def should_drop_text(text: str) -> bool:
  normalized = normalize_text(text)
  if not normalized:
    return True
  if normalized in {"❗", "💡", "•"}:
    return True
  return any(noise in normalized for noise in UI_NOISE)


def is_good_image(block: dict) -> bool:
  src = block.get("src", "")
  # blob URL是飞书临时渲染产物,页面关闭后失效,直接丢弃
  if src.startswith("blob:"):
    return False
  width = int(block.get("width", 0) or 0)
  height = int(block.get("height", 0) or 0)
  if width <= 0 or height <= 0:
    return True
  ratio = width / height
  if width < 180 or height < 110:
    return False
  return 0.45 <= ratio <= 3.4


def dedupe_blocks(blocks: list[dict]) -> list[dict]:
  merged: list[dict] = []
  seen_images: set[str] = set()
  recent_texts: list[str] = []
  for block in blocks:
    block_type = block.get("type")
    if block_type == "image":
      src = canonicalize_src(block.get("src", ""))
      if not src or src in seen_images:
        continue
      seen_images.add(src)
      merged.append(
        {
          "type": "image",
          "src": src,
          "alt": clean_text(block.get("alt", "")) or "文章配图",
          "width": int(block.get("width", 0) or 0),
          "height": int(block.get("height", 0) or 0),
          "top": int(block.get("top", 0) or 0),
          "left": int(block.get("left", 0) or 0),
        }
      )
      continue

    text = normalize_text(block.get("text", ""))
    if should_drop_text(text):
      continue
    token = f"{block_type}::{text}"
    if token in recent_texts[-120:]:
      continue
    recent_texts.append(token)
    merged.append(
      {
        "type": "heading" if block_type == "heading" else block_type,
        "text": text,
        "top": int(block.get("top", 0) or 0),
        "left": int(block.get("left", 0) or 0),
      }
    )
  return merged


def mark_scroll_root(page: Page) -> dict[str, int]:
  return page.evaluate(MARK_SCROLL_ROOT_JS)


def build_positions(metrics: dict[str, int]) -> list[int]:
  scroll_height = int(metrics.get("scrollHeight", 0) or 0)
  client_height = int(metrics.get("clientHeight", 0) or 0)
  max_top = max(scroll_height - client_height, 0)
  if max_top <= 0:
    return [0]
  step = max(int(client_height * 0.78), 720)
  positions = list(range(0, max_top + 1, step))
  if positions[-1] != max_top:
    positions.append(max_top)
  return positions


def fetch_image_data_urls(page: Page, blocks: list[dict]) -> dict[str, str]:
  sources: list[str] = []
  seen: set[str] = set()
  for block in blocks:
    if block["type"] != "image":
      continue
    src = block["src"]
    if src in seen:
      continue
    seen.add(src)
    sources.append(src)

  data_urls: dict[str, str] = {}
  if not sources:
    return data_urls

  payloads = page.evaluate(FETCH_IMAGE_JS, {"sources": sources, "timeoutMs": 12000})
  for payload in payloads:
    src = payload.get("src", "")
    if not src:
      continue
    if payload.get("ok") and payload.get("passthrough"):
      data_urls[src] = src
    elif payload.get("ok"):
      data_urls[src] = f"data:{payload['type']};base64,{payload['b64']}"
    else:
      data_urls[src] = src
  return data_urls


def _feishu_token_from_url(url: str) -> tuple[str, str]:
  """从飞书URL中提取token和类型(wiki/docx/doc)"""
  m = re.search(r"/wiki/([A-Za-z0-9_-]+)", url)
  if m:
    return m.group(1), "wiki"
  m = re.search(r"/docx/([A-Za-z0-9_-]+)", url)
  if m:
    return m.group(1), "docx"
  m = re.search(r"/doc/([A-Za-z0-9_-]+)", url)
  if m:
    return m.group(1), "doc"
  return "", ""


def _lark_cli(*args: str) -> dict:
  """调用lark-cli,返回解析后的JSON"""
  try:
    result = subprocess.run(
      ["lark-cli", *args],
      capture_output=True, text=True, timeout=30
    )
    return json.loads(result.stdout) if result.stdout.strip() else {}
  except Exception:
    return {}


def _fetch_callout_blocks(doc_token: str) -> dict[str, str]:
  """用飞书API获取文档所有callout块的完整文字,返回 {block_id: text}"""
  all_blocks: list[dict] = []
  page_token = ""
  while True:
    params = '{"page_size":500}'
    if page_token:
      params = f'{{"page_size":500,"page_token":"{page_token}"}}'
    d = _lark_cli("api", "GET",
                  f"/open-apis/docx/v1/documents/{doc_token}/blocks",
                  "--params", params)
    items = d.get("data", {}).get("items", [])
    all_blocks.extend(items)
    if not d.get("data", {}).get("has_more", False):
      break
    page_token = d.get("data", {}).get("page_token", "")

  if not all_blocks:
    return {}

  block_map = {b["block_id"]: b for b in all_blocks}

  def _get_text(b: dict) -> str:
    if "text" in b:
      elems = b["text"].get("elements", [])
      return "".join(e.get("text_run", {}).get("content", "") for e in elems)
    for key in ["paragraph", "heading1", "heading2", "heading3", "heading4",
                "heading5", "heading6", "heading7", "heading8", "heading9"]:
      if key in b:
        elems = b[key].get("elements", [])
        return "".join(e.get("text_run", {}).get("content", "") for e in elems)
    return ""

  def _collect(block_id: str, visited: set | None = None) -> list[str]:
    if visited is None:
      visited = set()
    if block_id in visited:
      return []
    visited.add(block_id)
    b = block_map.get(block_id)
    if not b:
      return []
    lines = []
    t = _get_text(b).strip()
    if t:
      lines.append(t)
    for cid in b.get("children", []):
      lines.extend(_collect(cid, visited))
    return lines

  result: dict[str, str] = {}
  for b in all_blocks:
    if b.get("block_type") == 19:  # callout
      lines = []
      for cid in b.get("children", []):
        lines.extend(_collect(cid))
      if lines:
        result[b["block_id"]] = "\n".join(lines)
  return result


def _get_docx_token(token: str, token_type: str) -> str:
  """将wiki token转为docx token"""
  if token_type == "wiki":
    d = _lark_cli("wiki", "spaces", "get_node", "--params", f'{{"token":"{token}"}}')
    node = d.get("data", {}).get("node", {})
    if node.get("obj_type") == "docx":
      return node.get("obj_token", "")
  return token if token_type == "docx" else ""


# ---------------------------------------------------------------------------
# 飞书API直读层(完全替代 playwright DOM 抓取)
# ---------------------------------------------------------------------------

_API_IMG_TMP_DIR = Path("/tmp/feishu_api_imgs")


def _fetch_all_blocks(doc_token: str) -> list[dict]:
  """分页获取文档所有 blocks"""
  all_blocks: list[dict] = []
  page_token = ""
  while True:
    params = '{"page_size":500}'
    if page_token:
      params = json.dumps({"page_size": 500, "page_token": page_token})
    d = _lark_cli("api", "GET",
                  f"/open-apis/docx/v1/documents/{doc_token}/blocks",
                  "--params", params)
    items = d.get("data", {}).get("items", [])
    all_blocks.extend(items)
    if not d.get("data", {}).get("has_more", False):
      break
    page_token = d.get("data", {}).get("page_token", "")
    if not page_token:
      break
  return all_blocks


def _block_text(b: dict) -> str:
  """从单个 block 提取文字,支持所有已知 key 格式"""
  # 新格式:直接有 text key
  if "text" in b:
    elems = b["text"].get("elements", [])
    return "".join(e.get("text_run", {}).get("content", "") for e in elems)
  # heading2..9
  for key in ["heading1", "heading2", "heading3", "heading4",
              "heading5", "heading6", "heading7", "heading8", "heading9"]:
    if key in b:
      elems = b[key].get("elements", [])
      return "".join(e.get("text_run", {}).get("content", "") for e in elems)
  # paragraph(旧格式偶有)
  if "paragraph" in b:
    elems = b["paragraph"].get("elements", [])
    return "".join(e.get("text_run", {}).get("content", "") for e in elems)
  # bullet / ordered(列表项)
  if "bullet" in b:
    elems = b["bullet"].get("elements", [])
    return "".join(e.get("text_run", {}).get("content", "") for e in elems)
  if "ordered" in b:
    elems = b["ordered"].get("elements", [])
    return "".join(e.get("text_run", {}).get("content", "") for e in elems)
  return ""


def _download_feishu_image(img_token: str) -> str:
  """下载飞书图片到 /tmp/feishu_imgs/,返回本地绝对路径;失败返回空字符串"""
  try:
    _API_IMG_TMP_DIR.mkdir(parents=True, exist_ok=True)
    # 先检查是否已下载(任意扩展名)
    for candidate in _API_IMG_TMP_DIR.glob(f"img_{img_token[:16]}.*"):
      if candidate.stat().st_size > 0:
        return str(candidate.resolve())
    out_name = f"img_{img_token[:16]}.png"
    out_path = _API_IMG_TMP_DIR / out_name
    result = subprocess.run(
      ["lark-cli", "docs", "+media-download",
       "--token", img_token,
       "--output", f"./{out_name}",
       "--overwrite"],
      capture_output=True, text=True, timeout=30,
      cwd=str(_API_IMG_TMP_DIR),
    )
    # 解析输出判断是否成功
    try:
      resp = json.loads(result.stdout) if result.stdout.strip() else {}
    except Exception:
      resp = {}
    # 检查实际文件(有时候扩展名会被自动调整)
    saved = resp.get("data", {}).get("saved_path", "")
    if saved:
      actual_path = Path(saved)
    else:
      actual_path = out_path
    if not actual_path.exists():
      # 尝试找同名不同扩展名的文件
      for candidate in _API_IMG_TMP_DIR.glob(f"img_{img_token[:16]}.*"):
        actual_path = candidate
        break
    if actual_path.exists() and actual_path.stat().st_size > 0:
      return str(actual_path.resolve())
  except Exception as e:
    print(f"[feishu_api] image download failed token={img_token}: {e}")
  return ""


def _collect_callout_text(callout_block: dict, block_map: dict) -> str:
  """递归收集 callout 块下所有子块的文字,合并成一段"""
  visited: set[str] = set()

  def _recurse(block_id: str) -> list[str]:
    if block_id in visited:
      return []
    visited.add(block_id)
    b = block_map.get(block_id)
    if not b:
      return []
    lines: list[str] = []
    t = _block_text(b).strip()
    if t:
      lines.append(t)
    for cid in b.get("children", []):
      lines.extend(_recurse(cid))
    return lines

  all_lines: list[str] = []
  for cid in callout_block.get("children", []):
    all_lines.extend(_recurse(cid))
  return "\n".join(all_lines)


def _api_blocks_to_raw(all_blocks: list[dict], doc_token: str) -> tuple[str, list[dict], dict[str, str]]:
  """
  把飞书 API blocks 转成和 DOM 抓取相同格式的 raw_blocks,
  同时下载图片并返回 image_data。
  返回: (title, raw_blocks, image_data)
  """
  block_map = {b["block_id"]: b for b in all_blocks}

  # 找根节点(block_type=1),确定顶层顺序
  root_block = next((b for b in all_blocks if b.get("block_type") == 1), None)
  if root_block:
    top_level_ids = root_block.get("children", [])
  else:
    # fallback:所有 parent_id == doc_token 的块,按原始顺序
    top_level_ids = [b["block_id"] for b in all_blocks
                     if b.get("parent_id") == doc_token]

  title = ""
  raw_blocks: list[dict] = []
  image_data: dict[str, str] = {}

  # 找标题(第一个 block_type=3 即 heading1,或者文档第一行文字)
  for b in all_blocks:
    if b.get("block_type") == 3:  # heading1
      title = _block_text(b).strip()
      break
  if not title:
    for bid in top_level_ids[:3]:
      b = block_map.get(bid, {})
      t = _block_text(b).strip()
      if t:
        title = t
        break

  def _process_block(block_id: str, depth: int = 0) -> None:
    """递归处理一个 block,向 raw_blocks append"""
    if depth > 12:  # 防止无限递归
      return
    b = block_map.get(block_id)
    if not b:
      return
    btype = b.get("block_type", 0)

    # --- 跳过:doc根、iframe ---
    if btype in (1, 25):
      # 但要继续处理 children(grid_col / 分栏列 里可能有图片)
      for cid in b.get("children", []):
        _process_block(cid, depth + 1)
      return

    # --- heading1 → title block(第一个处理,之后跳过)
    if btype == 3:
      text = _block_text(b).strip()
      if text:
        if not raw_blocks:  # 第一个 heading1 作为 title
          raw_blocks.append({"type": "title", "text": text})
        else:
          raw_blocks.append({"type": "heading", "text": text})
      return

    # --- heading2-9 → heading ---
    if 4 <= btype <= 11:
      text = _block_text(b).strip()
      if text:
        raw_blocks.append({"type": "heading", "text": text})
      # heading 可能包含 children(如嵌套的图片),递归处理
      for cid in b.get("children", []):
        child_b = block_map.get(cid)
        if child_b and child_b.get("block_type", 0) not in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11):
          _process_block(cid, depth + 1)
      return

    # --- paragraph (block_type=2) ---
    if btype == 2:
      text = _block_text(b).strip()
      if text:
        raw_blocks.append({"type": "text", "text": text})
      # paragraph 可能包含 inline_block children(如行内图片),需要递归处理
      for cid in b.get("children", []):
        child_b = block_map.get(cid)
        if child_b and child_b.get("block_type", 0) not in (2,):  # 避免重复处理段落文字
          _process_block(cid, depth + 1)
      return

    # --- ordered_list (block_type=12, key=bullet) ---
    # --- unordered_list (block_type=13, key=ordered) ---
    # 注意:飞书API里 12=bullet(无序), 13=ordered(有序)
    if btype == 12:
      text = _block_text(b).strip()
      if text:
        raw_blocks.append({"type": "text", "text": f"• {text}"})
      # 处理嵌套子列表
      for cid in b.get("children", []):
        _process_block(cid, depth + 1)
      return

    if btype == 13:
      text = _block_text(b).strip()
      seq = b.get("ordered", {}).get("style", {}).get("sequence", "")
      if text:
        prefix = f"{seq}. " if seq else "• "
        raw_blocks.append({"type": "text", "text": f"{prefix}{text}"})
      for cid in b.get("children", []):
        _process_block(cid, depth + 1)
      return

    # --- callout (block_type=19) → highlight + 内部图片/视频 ---
    if btype == 19:
      full_text = _collect_callout_text(b, block_map)
      if full_text.strip():
        raw_blocks.append({"type": "highlight", "text": full_text.strip()})
      # callout 内部可能包含图片、视频、或嵌套容器(grid等),递归处理非文字子块
      # 文字类子块已经被 _collect_callout_text 收集过了,跳过
      text_btypes = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13}  # paragraph, headings, lists
      for cid in b.get("children", []):
        child_b = block_map.get(cid)
        if not child_b:
          continue
        child_type = child_b.get("block_type", 0)
        if child_type not in text_btypes:
          _process_block(cid, depth + 1)
      return

    # --- image (block_type=27,key=image) ---
    if btype == 27:
      img_info = b.get("image", {})
      img_token = img_info.get("token", "")
      width = int(img_info.get("width", 0) or 0)
      height = int(img_info.get("height", 0) or 0)
      if img_token:
        src_key = f"feishu_img://{img_token}"
        raw_blocks.append({
          "type": "image",
          "src": src_key,
          "alt": "文章配图",
          "width": width,
          "height": height,
        })
        # 下载图片,image_data 值为 /api/local-image?path=<绝对路径>
        if src_key not in image_data:
          local_path = _download_feishu_image(img_token)
          if local_path:
            image_data[src_key] = f"/api/local-image?path={local_path}"
          else:
            image_data[src_key] = src_key  # 下载失败时保留原 key 作占位符
      return

    # --- grid (block_type=24) → 遍历 children(每列是 grid_col / block_type=25)---
    if btype == 24:
      for cid in b.get("children", []):
        _process_block(cid, depth + 1)
      return

    # --- grid_col (block_type=25) → 遍历 children ---
    if btype == 25:
      for cid in b.get("children", []):
        _process_block(cid, depth + 1)
      return

    # --- view/container (block_type=33) → 遍历 children ---
    if btype == 33:
      for cid in b.get("children", []):
        _process_block(cid, depth + 1)
      return

    # --- file / video (block_type=23) → 视频占位 ---
    if btype == 23:
      file_info = b.get("file", {})
      file_name = file_info.get("name", "")
      # 视频文件通常带有 .mp4/.mov 等后缀,或 mime 含 video
      mime = file_info.get("mime_type", "")
      is_video = any(ext in file_name.lower() for ext in (".mp4", ".mov", ".avi", ".webm", ".mkv")) or "video" in mime.lower()
      if is_video:
        raw_blocks.append({
          "type": "video",
          "title": file_name or "视频",
          "summary": "",
          "note": "(此处有视频,公众号暂不支持直接嵌入)",
          "link": "",
        })
      return

    # --- iframe (block_type=20) → 嵌入视频占位 ---
    if btype == 20:
      iframe_info = b.get("iframe", {})
      iframe_url = iframe_info.get("url", "") or iframe_info.get("component", {}).get("url", "")
      raw_blocks.append({
        "type": "video",
        "title": "嵌入视频",
        "summary": "",
        "note": "(此处有嵌入视频,公众号暂不支持直接嵌入)",
        "link": iframe_url,
      })
      return

    # --- file attachment (block_type=22) → 跳过非视频文件 ---
    # block_type=22: file attachment, skip

    # --- 其他未知类型:尝试提取文字 + 遍历 children ---
    print(f"[feishu_api] unhandled block_type={btype} id={block_id} children={len(b.get('children', []))}")
    text = _block_text(b).strip()
    if text:
      raw_blocks.append({"type": "text", "text": text})
    # 遍历 children,确保嵌套的图片/视频不会丢失
    for cid in b.get("children", []):
      _process_block(cid, depth + 1)

  # 按顶层顺序处理
  for bid in top_level_ids:
    _process_block(bid, 0)

  return title, raw_blocks, image_data


def _get_wiki_title(token: str) -> str:
  """从 wiki API 获取文档标题"""
  d = _lark_cli("wiki", "spaces", "get_node", "--params", f'{{"token":"{token}"}}')
  return d.get("data", {}).get("node", {}).get("title", "")


def _get_docx_title(doc_token: str) -> str:
  """从 docx API 获取文档标题"""
  d = _lark_cli("api", "GET",
                f"/open-apis/docx/v1/documents/{doc_token}",
                "--params", "{}")
  return d.get("data", {}).get("document", {}).get("title", "")


def extract_from_feishu_api(url: str) -> tuple[str, list[dict], dict[str, str]]:
  """
  用飞书API直读文档结构,完全替代 playwright DOM 抓取。
  返回格式和 extract_from_feishu 相同:(title, raw_blocks, image_data)
  """
  token, token_type = _feishu_token_from_url(url)
  if not token:
    raise ValueError(f"无法从 URL 提取飞书 token: {url}")

  # 获取 doc_token 和文档标题
  wiki_title = ""
  if token_type == "wiki":
    d = _lark_cli("wiki", "spaces", "get_node", "--params", f'{{"token":"{token}"}}')
    node = d.get("data", {}).get("node", {})
    wiki_title = node.get("title", "")
    if node.get("obj_type") == "docx":
      doc_token = node.get("obj_token", "")
    else:
      doc_token = ""
  else:
    doc_token = token if token_type == "docx" else ""

  if not doc_token:
    raise ValueError(f"无法获取 docx token(wiki token={token})")

  # 尝试从 docx API 获取标题(更直接)
  if not wiki_title:
    try:
      wiki_title = _get_docx_title(doc_token)
    except Exception:
      pass

  print(f"[feishu_api] doc_token={doc_token} title={wiki_title!r}")
  all_blocks = _fetch_all_blocks(doc_token)
  print(f"[feishu_api] fetched {len(all_blocks)} blocks")

  title, raw_blocks, image_data = _api_blocks_to_raw(all_blocks, doc_token)
  # 优先用 wiki title(比 block 里的 heading1 更可靠)
  if wiki_title:
    title = wiki_title

  print(f"[feishu_api] parsed title={title!r} raw_blocks={len(raw_blocks)} images={len(image_data)}")

  return title or "未命名文章", raw_blocks, image_data


def extract_from_feishu(url: str, *, fetch_images: bool = True) -> tuple[str, list[dict], dict[str, str]]:
  # 先用飞书API获取callout块的精确内容
  token, token_type = _feishu_token_from_url(url)
  callout_texts: dict[str, str] = {}
  if token:
    docx_token = _get_docx_token(token, token_type)
    if docx_token:
      callout_texts = _fetch_callout_blocks(docx_token)

  with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 2200})
    page.goto(url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(3500)
    metrics = mark_scroll_root(page)
    collected: list[dict] = []
    title = ""

    for top in build_positions(metrics):
      page.evaluate(
        """(top) => {
          const root = document.querySelector('[data-codex-scroll-root="1"]');
          if (root) root.scrollTop = top;
        }""",
        top,
      )
      page.wait_for_timeout(450)
      snapshot = page.evaluate(COLLECT_BLOCKS_JS)
      title = clean_text(snapshot.get("title", "")) or title
      collected.extend(snapshot.get("blocks", []))

    page.evaluate(
      """() => {
        const root = document.querySelector('[data-codex-scroll-root="1"]');
        if (root) root.scrollTop = 0;
      }"""
    )
    page.wait_for_timeout(500)
    blocks = dedupe_blocks(collected)

    # 如果拿到了callout数据,注入精确的highlight块
    if callout_texts:
      blocks = _inject_callout_blocks(blocks, callout_texts)

    image_data = fetch_image_data_urls(page, blocks) if fetch_images else {}
    browser.close()
  return title or "未命名文章", blocks, image_data


def _inject_callout_blocks(blocks: list[dict], callout_texts: dict[str, str]) -> list[dict]:
  """
  DOM抓取时高亮色块被拆散成多个text/heading,
  用飞书API的callout数据把它们合并回一个完整的highlight block。
  策略:把所有callout的文字特征注入,在auto_layout_blocks之前替换掉连续的散块。
  """
  if not callout_texts:
    return blocks

  # 把所有callout内容建成文字指纹集合(取每个callout的第一行作为定位锚)
  callout_anchors: list[tuple[str, str]] = []  # (first_line, full_text)
  for full_text in callout_texts.values():
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]
    if lines:
      callout_anchors.append((lines[0], full_text))

  if not callout_anchors:
    return blocks

  result: list[dict] = []
  i = 0
  while i < len(blocks):
    b = blocks[i]
    b_text = normalize_text(b.get("text", ""))

    # 检查当前block是否是某个callout的开头(精确匹配前30字)
    matched_callout = None
    for anchor_first, full_text in callout_anchors:
      anchor_norm = normalize_text(anchor_first)[:30]
      if anchor_norm and len(anchor_norm) >= 8 and b_text.startswith(anchor_norm):
        matched_callout = full_text
        break

    if matched_callout:
      # 把callout的所有行做成匹配集(用前20字做指纹)
      callout_fingerprints = {
        normalize_text(l)[:20]
        for l in matched_callout.splitlines()
        if l.strip() and len(l.strip()) >= 4
      }

      # 向前扫描,只跳过文字能在callout内容里匹配到的blocks
      # 遇到匹配不到的就停(说明已经是正文了)
      j = i + 1
      consecutive_misses = 0
      while j < len(blocks):
        bj = blocks[j]
        if bj.get("type") == "image":
          break
        bj_text = normalize_text(bj.get("text", ""))
        if not bj_text:
          j += 1
          continue
        # 检查这行是否属于callout
        bj_fp = bj_text[:20]
        if any(bj_fp in fp or fp in bj_text[:20] for fp in callout_fingerprints):
          consecutive_misses = 0
          j += 1
        else:
          consecutive_misses += 1
          if consecutive_misses >= 2:
            break
          j += 1

      # 用API拿到的精确内容插入一个highlight block
      result.append({
        "type": "highlight",
        "text": matched_callout,
      })
      i = j  # 跳过整个callout范围
    else:
      result.append(b)
      i += 1

  return result


def emphasis_candidates(text: str) -> list[str]:
  candidates: list[tuple[int, str]] = []

  def push(fragment: str, score: int) -> None:
    normalized = normalize_text(fragment).strip(",。!?;:、()()[]【】 ")
    if not normalized or len(normalized) < 2 or len(normalized) > 24:
      return
    if normalized in EMPHASIS_STOPWORDS:
      return
    if any(normalized in existing or existing in normalized for _, existing in candidates):
      return
    candidates.append((score, normalized))

  for fragment in re.findall(r'["\u201c\u201d\u300a\u3010](.{2,24}?)["\u201c\u201d\u300b\u3011]', text):
    push(fragment, 5)

  for fragment in re.findall(r"\b[A-Za-z][A-Za-z0-9.+#/_-]*(?:\s+[A-Za-z0-9.+#/_-]+){0,3}", text):
    if any(char.isupper() for char in fragment) or any(char.isdigit() for char in fragment):
      push(fragment, 4)

  for clause in re.split(r"[,。!?;:]", text):
    normalized = normalize_text(clause)
    if not 4 <= len(normalized) <= 18:
      continue
    score = 0
    if any(hint in normalized for hint in EMPHASIS_HINTS):
      score += 3
    if normalized.startswith(("不是", "真正", "关键", "核心", "最好", "一定", "别", "不要", "先")):
      score += 2
    if any(char.isalpha() for char in normalized) or any(char.isdigit() for char in normalized):
      score += 2
    if score >= 3:
      push(normalized, score)

  ranked = sorted(candidates, key=lambda item: (-item[0], -len(item[1])))
  return [fragment for _, fragment in ranked[:4]]


def stylize_text(text: str, *, max_hits: int = 2) -> str:
  rendered = escape_text(text)
  hits = 0
  for fragment in emphasis_candidates(text):
    if hits >= max_hits:
      break
    escaped = html.escape(fragment)
    if escaped in rendered:
      rendered = rendered.replace(
        escaped,
        f'<strong style="color:{PALETTE["accent"]};font-weight:700;">{escaped}</strong>',
        1,
      )
      hits += 1
  return rendered


def prompt_score(text: str) -> int:
  normalized = normalize_text(text)
  if not normalized:
    return -10
  score = 0
  if any(normalized.startswith(prefix) for prefix in ROLE_PREFIXES):
    score += 6
  if normalized in FIELD_MARKERS or normalized.endswith(":"):
    score += 4
  if re.fullmatch(r"\d+\s*[、..]?\s*\S+", normalized):
    score += 3
  if any(token in normalized for token in ("HTML", "CSS", "JavaScript", "输出", "网页", "页面", "课程", "项目", "视觉", "代码")):
    score += 2
  if len(normalized) <= 18:
    score += 1
  if any(marker in normalized for marker in RESUME_MARKERS):
    score -= 8
  return score


def looks_like_resume_sentence(text: str) -> bool:
  normalized = normalize_text(text)
  return any(marker in normalized for marker in RESUME_MARKERS)


def has_prompt_context(blocks: list[dict], start: int) -> bool:
  total = 0
  hits = 0
  # 扫更多block(提示词段落经常很长,heading穿插其中)
  for block in blocks[start:start + 25]:
    if block["type"] == "image":
      continue
    score = prompt_score(block.get("text", ""))
    total += max(score, 0)
    if score >= 4:
      hits += 1
  return total >= 10 and hits >= 1


def prompt_label(lines: list[str]) -> str:
  joined = " ".join(lines[:10])
  if any(token in joined for token in ("官网", "落地页", "首页", "网页")):
    return "这段网页提示词"
  if any(token in joined for token in ("课程", "训练营", "项目方案", "商业模式")):
    return "这段方案提示词"
  if any(token in joined for token in ("小说", "修仙", "剑宗", "玄清宗")):
    return "这段剧情提示词"
  if any(token in joined for token in ("生图", "插画", "海报", "视觉")):
    return "这段生图提示词"
  return "这段提示词,我单拎出来了"


def collect_prompt_block(blocks: list[dict], start: int) -> tuple[dict | None, int]:
  if start >= len(blocks):
    return None, start
  first = blocks[start]
  if first["type"] != "text":
    return None, start
  _, has_list_marker = strip_list_marker(first.get("text", ""))
  if has_list_marker:
    return None, start
  if prompt_score(first.get("text", "")) < 4 or not has_prompt_context(blocks, start):
    return None, start

  lines: list[str] = []
  index = start
  promptish = 0
  consecutive_low = 0  # 连续低分行数,超过阈值才真正结束
  while index < len(blocks):
    block = blocks[index]
    if block["type"] == "image":
      # 图片直接中断
      break
    text = normalize_text(block.get("text", ""))
    if not text:
      index += 1
      continue
    if looks_like_resume_sentence(text):
      break
    score = prompt_score(text)
    # heading不再立即截断,把它的文字纳入提示词
    if block["type"] == "heading":
      lines.append(text)
      if score >= 3:
        promptish += 1
        consecutive_low = 0
      index += 1
      continue
    # 连续多行低分正文才真正结束(允许少量过渡句)
    if lines and score <= 0 and len(text) > 35 and not text.endswith(":"):
      consecutive_low += 1
      if consecutive_low >= 2:
        break
    else:
      consecutive_low = 0
    lines.append(text)
    if score >= 3:
      promptish += 1
    index += 1

  if len(lines) < 4 or promptish < 2:
    return None, start

  return {
    "type": "prompt",
    "label": prompt_label(lines),
    "text": "\n".join(lines),
  }, index


def is_inline_heading(blocks: list[dict], index: int, text: str) -> bool:
  normalized = normalize_text(text)
  if not 6 <= len(normalized) <= 22:
    return False
  if normalized.endswith(("。", "!", "?", ";", ":", "~")):
    return False
  if normalized in FIELD_MARKERS or any(normalized.startswith(prefix) for prefix in ROLE_PREFIXES):
    return False

  previous = normalize_text(blocks[index - 1].get("text", "")) if index > 0 else ""
  following = normalize_text(blocks[index + 1].get("text", "")) if index + 1 < len(blocks) else ""
  if previous and not re.search(r"[。!?!?::]$", previous):
    return False
  if following.startswith((",", "也", "而", "但", "所以", "因为")):
    return False
  return any(token in normalized for token in ("问题", "麻烦", "门槛", "原因", "重点", "关键", "建议", "体验", "平台", "模型", "朋友", "新手", "普通人"))


def quote_like(text: str) -> bool:
  normalized = normalize_text(text)
  if len(normalized) > 28:
    return False
  return any(token in normalized for token in ("普通人", "很麻烦", "新手友好", "你到底该用哪个", "值不值得"))


LIST_MARKER_RE = re.compile(r"^(?:[-•·●▪◦]\s*|(?:[((]?\d{1,2}[))]?|[1-20]|[一二三四五六七八九十]+)[、..)]\s*)")


def strip_list_marker(text: str) -> tuple[str, bool]:
  normalized = normalize_text(text)
  stripped = LIST_MARKER_RE.sub("", normalized).strip()
  return (stripped or normalized), stripped != normalized


def looks_like_meta_line(text: str) -> bool:
  normalized = normalize_text(text)
  return (
    normalized.endswith("修改")
    or normalized.startswith("最新修改时间")
    or bool(re.fullmatch(r"(昨天|今天|前天)修改", normalized))
    or bool(re.fullmatch(r"\d{1,2}月\d{1,2}日(?:修改)?", normalized))
  )


def looks_like_date_line(text: str) -> bool:
  normalized = normalize_text(text)
  return bool(re.fullmatch(r"\d{4}年\d{1,2}月\d{1,2}日", normalized))


def is_heading_candidate(text: str) -> bool:
  normalized = normalize_text(text)
  if not 2 <= len(normalized) <= 18:
    return False
  if looks_like_meta_line(normalized) or looks_like_date_line(normalized):
    return False
  if normalized.startswith(("--", "-", "-")):
    return False
  if re.search(r"[。!?;,,.!?::、()()...]$", normalized):
    return False
  if any(char.isdigit() for char in normalized):
    return False
  # 口语化带入句("如何/怎么/什么/如果/但是/所以"开头或含有),长度>6不升标题
  # 例:"打工人和学生党如何狠狠压榨它"、"如何判断一个工具值不值得用"
  if len(normalized) > 6 and re.search(r"如何|怎么|什么|如果|但是|所以|因为|只是|只要|就是|真的|其实", normalized):
    return False
  return True


def has_heading_cue(text: str) -> bool:
  normalized = normalize_text(text)
  return (
    normalized in {"现在", "后来", "最后"}
    or normalized.startswith(("关于", "那个", "你让我", "刚", "后来", "直到"))
    or normalized.endswith(("的时候", "那天", "之后"))
  )


def should_keep_separate_text(text: str) -> bool:
  normalized = normalize_text(text)
  if not normalized:
    return False
  _, has_marker = strip_list_marker(normalized)
  if has_marker:
    return True
  if looks_like_meta_line(normalized) or looks_like_date_line(normalized):
    return True
  if normalized.startswith(("--", "-", "-")):
    return True
  return is_heading_candidate(normalized) and (has_heading_cue(normalized) or len(normalized) <= 8)


def build_group_item(text: str, index: int) -> dict:
  normalized = normalize_text(text)
  if ":" in normalized:
    title, body = normalized.split(":", 1)
    if 1 <= len(title.strip()) <= 12 and len(body.strip()) >= 4:
      return {"title": title.strip(), "text": body.strip()}
  return {"title": "", "text": normalized}


def collect_structured_series(blocks: list[dict], start: int) -> tuple[dict | None, int]:
  if start >= len(blocks) or blocks[start]["type"] != "text":
    return None, start

  previous_type = blocks[start - 1]["type"] if start > 0 else ""
  items: list[str] = []
  explicit = False
  index = start

  while index < len(blocks):
    block = blocks[index]
    if block["type"] != "text":
      break
    text = normalize_text(block.get("text", ""))
    if not text or looks_like_meta_line(text) or looks_like_date_line(text):
      break
    stripped, has_marker = strip_list_marker(text)
    if prompt_score(text) >= 4 and not has_marker:
      break
    candidate = stripped if has_marker else text
    if len(candidate) > 42:
      break
    if explicit and not has_marker:
      break
    if not explicit and items and not has_marker and len(candidate) > 28:
      break
    explicit = explicit or has_marker
    items.append(candidate)
    index += 1
    if len(items) >= 4:
      break

  if len(items) < 2:
    return None, start

  max_len = max(len(item) for item in items)
  avg_len = sum(len(item) for item in items) / len(items)
  if explicit:
    if len(items) == 3 and max_len <= 28:
      return {
        "type": "group",
        "layout": "horizontal",
        "items": [build_group_item(item, idx) for idx, item in enumerate(items)],
      }, index
    return {
      "type": "list",
      "style": "ordered",
      "items": items,
    }, index

  if previous_type in {"heading", "subheading", "highlight"} and len(items) in {2, 3} and avg_len <= 22 and max_len <= 30:
    return {
      "type": "group",
      "layout": "horizontal" if len(items) == 3 else "vertical",
      "items": [build_group_item(item, idx) for idx, item in enumerate(items)],
    }, index

  return None, start


def is_highlight_candidate(blocks: list[dict], index: int, text: str) -> bool:
  normalized = normalize_text(text)
  if not 10 <= len(normalized) <= 36:
    return False
  if looks_like_meta_line(normalized) or looks_like_date_line(normalized):
    return False
  if prompt_score(normalized) >= 4:
    return False
  if is_heading_candidate(normalized):
    return False
  if not normalized.endswith(("。", "!", "?", "......")):
    return False
  if normalized.count(",") >= 3:
    return False

  previous = normalize_text(blocks[index - 1].get("text", "")) if index > 0 else ""
  following = normalize_text(blocks[index + 1].get("text", "")) if index + 1 < len(blocks) else ""
  has_context = len(previous) >= 20 or len(following) >= 20 or (index > 0 and blocks[index - 1]["type"] in {"heading", "subheading"})
  if not has_context:
    return False
  cue = (
    normalized.startswith(("不是因为", "因为", "所以", "而是", "但", "后来", "其实", "只是"))
    or "被看见" in normalized
    or "我想" in normalized
    or "我记得" in normalized
    or "很重要" in normalized
    or len(normalized) <= 18
  )
  return cue


def display_width(width: int, height: int) -> str:
  if width > 0 and height > 0:
    ratio = width / height
    if ratio >= 1.4:
      return "92%"
    if ratio <= 0.82:
      return "62%"
    if ratio <= 1.05:
      return "70%"
  return "78%"


def text_contains_recent_fragment(recent_texts: list[str], candidate: str) -> bool:
  stripped = candidate.lstrip("。,""\"")
  for item in recent_texts[-3:]:
    if len(item) >= len(stripped) + 6 and stripped and stripped in item:
      return True
  return False


def should_merge_text(previous: str, current: str) -> bool:
  if not previous or not current:
    return False
  if should_keep_separate_text(previous) or should_keep_separate_text(current):
    return False
  if current.startswith(("。", ",", "、", ";", ":", ")", "”", '"')):
    return True
  if previous.endswith((",", "、", ":", ";", "(", "“", '"', "......", "...")):
    return True
  if not re.search(r"[。!?!?:;]$", previous) and not looks_like_meta_line(current):
    return True
  if len(current) <= 8 and not re.search(r"[。!?!?]$", current):
    return True
  return False


def merge_text(previous: str, current: str) -> str:
  if current.startswith(("。", ",", "、", ";", ":", ")", "”", '"')):
    return f"{previous.rstrip()}{current.lstrip()}"
  return f"{previous.rstrip()}{current.lstrip()}"


def refine_text_blocks(blocks: list[dict]) -> list[dict]:
  refined: list[dict] = []
  recent_texts: list[str] = []
  for block in blocks:
    if block["type"] != "text":
      refined.append(block)
      continue

    text = normalize_text(block.get("text", ""))
    if not text:
      continue
    if text_contains_recent_fragment(recent_texts, text):
      continue

    if refined and refined[-1]["type"] == "text":
      previous_text = refined[-1]["text"]
      if text in previous_text and len(text) < len(previous_text):
        continue
      if previous_text in text and len(previous_text) < len(text) and len(previous_text) <= 14:
        refined[-1]["text"] = text
        recent_texts.append(text)
        continue
      if should_merge_text(previous_text, text):
        refined[-1]["text"] = merge_text(previous_text, text)
        recent_texts.append(refined[-1]["text"])
        continue

    refined.append({"type": "text", "text": text})
    recent_texts.append(text)

  return refined


def promote_heading_blocks(blocks: list[dict]) -> list[dict]:
  promoted: list[dict] = []
  for index, block in enumerate(blocks):
    if block["type"] != "text":
      promoted.append(block)
      continue

    text = normalize_text(block.get("text", ""))
    previous = normalize_text(blocks[index - 1].get("text", "")) if index > 0 else ""
    following = normalize_text(blocks[index + 1].get("text", "")) if index + 1 < len(blocks) else ""

    is_heading = False
    if is_heading_candidate(text):
      previous_closed = bool(previous) and bool(re.search(r"[。!?!?::...]$", previous))
      following_long_enough = len(following) >= 8 and not looks_like_meta_line(following)
      if has_heading_cue(text):
        is_heading = True
      elif previous_closed and following_long_enough:
        is_heading = True
      elif len(text) <= 8 and following_long_enough:
        is_heading = True
      elif previous_closed and len(text) <= 12:
        is_heading = True

    if is_heading:
      # 两个 heading 连在一起时,后一个降级为 subheading(标题之间必有层级关系)
      prev_block_type = promoted[-1]["type"] if promoted else ""
      if prev_block_type == "heading":
        promoted.append({"type": "subheading", "text": text})
      else:
        promoted.append({"type": "heading", "text": text})
    else:
      promoted.append({"type": "text", "text": text})
  return promoted


def group_images_to_gallery(blocks: list[dict]) -> list[dict]:
  """
  把 blocks 里连续的 image block 合并成 gallery block。
  1张 → 保持 image;2张以上 → {"type": "gallery", "images": [...]}
  gallery 的 HTML 渲染规则见 render_gallery_grid。
  """
  result: list[dict] = []
  index = 0
  while index < len(blocks):
    block = blocks[index]
    if block.get("type") != "image":
      result.append(block)
      index += 1
      continue
    # 收集连续 image blocks
    run: list[dict] = []
    while index < len(blocks) and blocks[index].get("type") == "image":
      run.append(blocks[index])
      index += 1
    # 最后一张图片（签名图等）单独一行，不跟前面并排
    is_tail = (index >= len(blocks))  # 这组图片在文章末尾
    if len(run) == 1:
      result.append(run[0])
    elif is_tail:
      # 末尾连续图片：前面的该合并合并，最后一张单独
      front = run[:-1]
      if len(front) == 1:
        result.append(front[0])
      else:
        result.append({"type": "gallery", "images": front})
      result.append(run[-1])  # 签名图单独
    else:
      result.append({"type": "gallery", "images": run})
  return result


def auto_layout_blocks(blocks: list[dict]) -> list[dict]:
  laid_out: list[dict] = []
  index = 0
  while index < len(blocks):
    block = blocks[index]
    if block["type"] != "text":
      laid_out.append(block)
      index += 1
      continue

    prompt_block, prompt_end = collect_prompt_block(blocks, index)
    if prompt_block:
      laid_out.append(prompt_block)
      index = prompt_end
      continue

    series_block, series_end = collect_structured_series(blocks, index)
    if series_block:
      laid_out.append(series_block)
      index = series_end
      continue

    text = normalize_text(block.get("text", ""))
    if is_highlight_candidate(blocks, index, text):
      # 如果下一句也是 highlight 候选且有更强的金句特征,让当前句让步
      next_text = ""
      if index + 1 < len(blocks) and blocks[index + 1]["type"] == "text":
        next_text = normalize_text(blocks[index + 1].get("text", ""))
      if next_text and is_highlight_candidate(blocks, index + 1, next_text):
        # 下一句也是金句候选--把当前句当普通文字,让下一句做金句
        laid_out.append(block)
        index += 1
        continue
      laid_out.append({"type": "highlight", "text": text})
      index += 1
      continue

    laid_out.append(block)
    index += 1

  # 最后一步:把连续 image block 合并成 gallery
  return group_images_to_gallery(laid_out)


def auto_layout_article(article: dict) -> dict:
  blocks = article.get("blocks", [])
  laid_out = auto_layout_blocks(promote_heading_blocks(refine_text_blocks(blocks)))
  return {
    "title": article.get("title", ""),
    "blocks": ensure_intro_card(article.get("title", ""), laid_out),
  }


def normalize_article(title: str, raw_blocks: list[dict], image_data: dict[str, str], footer_data_url: str | None) -> dict:
  start = 0
  normalized_title = normalize_text(title)
  for idx, block in enumerate(raw_blocks):
    if block["type"] == "title" and normalize_text(block.get("text", "")) == normalized_title:
      start = idx
      break

  blocks = raw_blocks[start:]
  article_blocks: list[dict] = []
  if blocks and normalize_text(blocks[0].get("text", "")) == normalized_title:
    blocks = blocks[1:]
  if blocks and blocks[0]["type"] == "meta":
    article_blocks.append({"type": "meta", "text": blocks[0]["text"]})
    blocks = blocks[1:]

  seen_headings: set[str] = set()
  for block in blocks:
    if block["type"] == "image":
      if not is_good_image(block):
        continue
      article_blocks.append(
        {
          "type": "image",
          "src": image_data.get(block["src"], block["src"]),
          "alt": block.get("alt", "文章配图"),
          "width": int(block.get("width", 0) or 0),
          "height": int(block.get("height", 0) or 0),
        }
      )
      continue

    # video 块直接透传,不做文字 normalize(它没有 text 字段)
    if block["type"] == "video":
      article_blocks.append(block)
      continue

    text = normalize_text(block.get("text", ""))
    if should_drop_text(text) or text == normalized_title:
      continue
    if not article_blocks and looks_like_meta_line(text):
      article_blocks.append({"type": "meta", "text": text})
      continue
    if block["type"] == "heading":
      if text in seen_headings:
        continue
      seen_headings.add(text)
      article_blocks.append({"type": "heading", "text": text})
      continue
    # 保留 highlight/prompt 类型,不降级为 text
    # highlight 保留原始换行(callout内容可能有多行),不用 normalize_text
    if block["type"] in {"highlight", "prompt"}:
      raw_text = block.get("text", "")
      # 逐行 normalize 再重新拼回,保留多行结构
      if "\n" in raw_text:
        lines = [normalize_text(line) for line in raw_text.splitlines()]
        lines = [l for l in lines if l]  # 去掉空行
        block_text = "\n".join(lines)
      else:
        block_text = text  # 单行直接用已 normalize 的
      article_blocks.append({"type": block["type"], "text": block_text,
                             "label": block.get("label", "")})
      continue
    article_blocks.append({"type": "text", "text": text})

  article_blocks = refine_text_blocks(article_blocks)
  article_blocks = promote_heading_blocks(article_blocks)
  article_blocks = auto_layout_blocks(article_blocks)
  article_blocks = ensure_intro_card(title, article_blocks)

  # 视频占位框已移到编辑器里手动添加，不再自动插入

  if footer_data_url:
    article_blocks.append({"type": "image", "src": footer_data_url, "alt": "关注引导图", "width": 1280, "height": 640})

  return {
    "title": title,
    "blocks": article_blocks,
  }


def render_meta(text: str) -> str:
  return (
    f'<p style="margin:0 0 18px;color:{PALETTE["muted"]};font-size:12px;line-height:1.6;letter-spacing:0.8px;">'
    f"{escape_text(text)}</p>"
  )


def render_keyword_pills(keywords: list[str]) -> str:
  visible = [normalize_text(keyword) for keyword in keywords if normalize_text(keyword)]
  if not visible:
    return ""
  return "".join(
    f'<span style="display:inline-block;margin:0 8px 8px 0;padding:6px 12px;border-radius:999px;'
    f'background-color:#fff9ef;border:1px solid {WARM_BORDER};color:{PALETTE["accent"]};font-size:12px;'
    f'line-height:1.2;font-weight:700;">#{escape_text(keyword)}</span>'
    for keyword in visible[:5]
  )


def render_intro_visual(block: dict) -> str:
  image_src = normalize_text(block.get("image_src", ""))
  image_alt = normalize_text(block.get("image_alt", "")) or "今日主题视觉"
  if image_src:
    return (
      f'<span style="display:block;padding:8px;border-radius:26px;background-color:#edd5b6;">'
      f'<span style="display:block;padding:8px;border-radius:22px;background-color:#fff5e8;">'
      f'<img src="{escape_text(image_src)}" alt="{escape_text(image_alt)}" '
      'style="display:block;width:100%;max-width:100%;height:auto;border-radius:16px;" />'
      '</span></span>'
    )
  return (
    f'<span style="display:block;padding:8px;border-radius:26px;background-color:#edd5b6;">'
    f'<span style="display:block;min-height:198px;padding:18px 16px;border-radius:22px;background-color:#fff5e8;">'
    f'<span style="display:block;width:76px;height:76px;margin:0 0 12px auto;border-radius:24px;background-color:#ecd0b1;"></span>'
    f'<span style="display:block;width:48px;height:4px;margin:0 0 14px;border-radius:999px;background-color:{WARM_LINE};"></span>'
    f'<span style="display:block;height:54px;border-radius:18px;background-color:#f1dcc3;"></span>'
    '</span></span>'
  )


def render_hero_card(block: dict) -> str:
  title = normalize_text(block.get("title", ""))
  category = normalize_text(block.get("category", ""))
  summary = normalize_text(block.get("summary", ""))
  theme = normalize_text(block.get("theme", ""))
  keywords_markup = render_keyword_pills(block.get("keywords", []))
  title_markup = (
    f'<p style="margin:0 0 12px;font-family:\'Songti SC\',\'STSong\',\'SimSun\',serif;color:{PALETTE["ink"]};'
    f'font-size:30px;line-height:1.36;font-weight:700;">{escape_text(title)}</p>'
    if title
    else ""
  )
  category_markup = (
    f'<span style="display:inline-block;margin:0 0 8px;padding:6px 12px;border-radius:999px;background-color:#fff3e4;'
    f'color:{PALETTE["accent"]};font-size:11px;line-height:1.2;font-weight:700;">{escape_text(category)}</span>'
    if category
    else ""
  )
  theme_markup = (
    f'<p style="margin:0 0 10px;color:{PALETTE["muted"]};font-size:12px;line-height:1.6;letter-spacing:1.2px;'
    f'text-transform:uppercase;">Theme · {escape_text(theme)}</p>'
    if theme
    else ""
  )
  summary_markup = (
    f'<p style="margin:0 0 14px;color:{PALETTE["text"]};font-size:15px;line-height:1.86;">{stylize_text(summary, max_hits=1)}</p>'
    if summary
    else ""
  )
  # 封面图框:用border框包裹,可以直接放图也可以后贴
  hero_image_src = normalize_text(block.get("image_src", ""))
  if hero_image_src:
    cover_placeholder = (
      f'<section style="margin:0 0 16px;border:2px solid {WARM_BORDER};border-radius:16px;overflow:hidden;">'
      f'<img src="{escape_text(hero_image_src)}" alt="封面" '
      f'style="display:block;width:100%;max-width:100%;height:auto;" />'
      f'</section>'
    )
  else:
    cover_placeholder = (
      f'<section style="margin:0 0 16px;border:2px solid {WARM_BORDER};border-radius:16px;overflow:hidden;">'
      f'<p style="margin:0;padding:40px 0;text-align:center;'
      f'color:{PALETTE["muted"]};font-size:13px;line-height:1.6;">'
      f'🖼 删除本段文字,在此处粘贴封面图</p>'
      f'</section>'
    )
  return (
    f'<span style="display:block;margin:0 0 32px;padding:10px;border-radius:32px;background-color:#ecd4b5;">'
    f'<span style="display:block;padding:18px 18px 16px;border-radius:28px;background-color:#fff4e8;">'
    f'{cover_placeholder}'
    f'<p style="margin:0 0 12px;">'
    f'<span style="display:inline-block;margin:0 8px 8px 0;padding:6px 12px;border-radius:999px;background-color:{WARM_PILL};'
    f'color:{PALETTE["accent"]};font-size:11px;line-height:1.2;font-weight:700;letter-spacing:1.5px;">今日导读</span>'
    f'{category_markup}</p>'
    f'{theme_markup}'
    f'{title_markup}'
    f'{summary_markup}'
    f'<span style="display:block;">{keywords_markup}</span>'
    '</span>'
    '</span>'
  )


def render_video_cover(block: dict) -> str:
  cover_src = normalize_text(block.get("cover_src", ""))
  cover_alt = normalize_text(block.get("cover_alt", "")) or "视频封面"
  if cover_src:
    return (
      f'<span style="display:block;padding:8px;border-radius:26px;background-color:#edd5b6;">'
      f'<span style="display:block;padding:8px;border-radius:22px;background-color:#fff5e8;">'
      f'<img src="{escape_text(cover_src)}" alt="{escape_text(cover_alt)}" '
      'style="display:block;width:100%;max-width:100%;height:auto;border-radius:16px;" />'
      '</span></span>'
    )
  return (
    f'<span style="display:block;padding:8px;border-radius:26px;background-color:#edd5b6;">'
    f'<span style="display:block;min-height:184px;padding:18px 16px;border-radius:22px;background-color:#fff5e8;">'
    f'<span style="display:block;width:100%;height:100%;min-height:148px;border-radius:18px;background-color:#f1dcc3;">'
    f'<span style="display:block;width:56px;height:56px;margin:44px auto 0;border-radius:999px;background-color:#fff0df;"></span>'
    '</span>'
    '</span></span>'
  )


def render_video_card(block: dict) -> str:
  title = normalize_text(block.get("title", ""))
  summary = normalize_text(block.get("summary", ""))
  note = normalize_text(block.get("note", ""))
  link = normalize_text(block.get("link", ""))
  title_markup = (
    f'<p style="margin:0 0 10px;color:{PALETTE["ink"]};font-family:\'Songti SC\',\'STSong\',\'SimSun\',serif;'
    f'font-size:24px;line-height:1.45;font-weight:700;">{escape_text(title)}</p>'
    if title
    else ""
  )
  summary_markup = (
    f'<p style="margin:0 0 12px;color:{PALETTE["text"]};font-size:15px;line-height:1.84;">{stylize_text(summary, max_hits=1)}</p>'
    if summary
    else ""
  )
  note_markup = (
    f'<div style="padding:10px 12px;border-radius:16px;background-color:#fff5e9;'
    f'color:{PALETTE["accent"]};font-size:13px;line-height:1.75;font-weight:600;">{escape_text(note)}</div>'
    if note
    else ""
  )
  link_markup = (
    f'<p style="margin:10px 0 0;color:{PALETTE["muted"]};font-size:12px;line-height:1.7;">视频链接:{escape_text(link)}</p>'
    if link
    else ""
  )
  return (
    f'<span style="display:block;margin:20px 0 28px;padding:10px;border-radius:32px;background-color:#ecd4b7;">'
    f'<span style="display:block;padding:16px 16px 14px;border-radius:28px;background-color:#fff4e8;">'
    f'<p style="margin:0 0 12px;"><span style="display:inline-block;margin:0 8px 8px 0;padding:6px 12px;border-radius:999px;'
    f'background-color:{WARM_PILL};color:{PALETTE["accent"]};font-size:11px;line-height:1.2;font-weight:700;letter-spacing:1.6px;">VIDEO</span>'
    f'<span style="display:inline-block;margin:0 0 8px;padding:6px 12px;border-radius:999px;background-color:#fff4e7;'
    f'color:{PALETTE["accent"]};font-size:11px;line-height:1.2;font-weight:700;">报编信息</span></p>'
    '<span style="display:block;font-size:0;white-space:nowrap;">'
    f'<span style="display:inline-block;vertical-align:top;width:42%;padding-right:14px;white-space:normal;">{render_video_cover(block)}</span>'
    '<span style="display:inline-block;vertical-align:top;width:58%;white-space:normal;">'
    f'{title_markup}'
    f'{summary_markup}'
    f'{note_markup}'
    f'{link_markup}'
    '</span>'
    '</span>'
    '</span>'
    '</span>'
  )


def render_heading(text: str, chapter_number: int) -> str:
  label = f"{chapter_number:02d}"
  return (
    f'<div style="margin:0;padding:46px 0 28px;background-color:#fff8f1;">'
    f'<p style="margin:0 0 12px;"><span style="display:inline-block;padding:6px 14px;border-radius:999px;'
    f'background-color:{WARM_PILL};color:{PALETTE["accent"]};font-size:11px;line-height:1.2;font-weight:700;'
    f'letter-spacing:1.8px;text-transform:uppercase;">Chapter {label}</span></p>'
    f'<div style="padding-left:14px;border-left:3px solid {WARM_LINE};">'
    f'<p style="margin:0;font-family:\'Songti SC\',\'STSong\',\'SimSun\',serif;'
    f'color:{PALETTE["ink"]};font-size:29px;line-height:1.42;font-weight:700;letter-spacing:0.1px;">{escape_text(text)}</p>'
    f'<div style="width:92px;height:2px;margin-top:12px;background-color:{WARM_LINE};border-radius:999px;"></div>'
    '</div>'
    "</div>"
  )


def render_subheading(text: str, section_number: int) -> str:
  label = f"{section_number:02d}"
  return (
    f'<div style="margin:0;padding:30px 0 20px;background-color:#fff8f1;">'
    f'<p style="margin:0 0 10px;"><span style="display:inline-block;padding:4px 10px;'
    f'border-radius:999px;background-color:{WARM_PILL};color:{PALETTE["accent"]};font-size:11px;line-height:1.2;'
    f'font-weight:700;letter-spacing:1.5px;text-transform:uppercase;">Section {label}</span></p>'
    f'<div style="padding-left:12px;border-left:2px solid {WARM_BORDER};">'
    f'<p style="margin:0;font-family:\'Songti SC\',\'STSong\',\'SimSun\',serif;'
    f'color:{PALETTE["ink"]};font-size:22px;line-height:1.5;font-weight:700;letter-spacing:0.2px;">'
    f'{escape_text(text)}</p>'
    '</div>'
    '</div>'
  )


def render_paragraph(text: str, *, lead: bool = False) -> str:
  size = 18 if lead else 16
  color = PALETTE["ink"] if lead else PALETTE["text"]
  weight = 600 if lead else 400
  pad = "0 0 18px" if lead else "0 0 17px"
  return (
    f'<p style="margin:0;padding:{pad};color:{color};font-size:{size}px;line-height:1.92;font-weight:{weight};background-color:#fff8f1;">'
    f"{stylize_text(text)}</p>"
  )


def render_quote(text: str) -> str:
  return (
    f'<div style="margin:18px 0 22px;padding:14px 16px 14px 16px;border-left:3px solid {PALETTE["accent"]};'
    f'background-color:{WARM_PANEL_SOFT};border-radius:0 18px 18px 0;'
    f'color:{PALETTE["ink"]};font-size:17px;line-height:1.9;font-weight:600;">{stylize_text(text, max_hits=1)}</div>'
  )


def render_highlight(text: str) -> str:
  # 多行 callout 文字:按 \n 分段,段间加大间距,行间距和字号与正文统一
  paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
  if len(paragraphs) <= 1:
    rendered = stylize_text(text, max_hits=2)
  else:
    # 每段独立block,段间距20px,字号和行间距与全文统一
    parts = []
    for p in paragraphs:
      parts.append(
        f'<span style="display:block;margin:0 0 20px;color:{PALETTE["ink"]};'
        f'font-family:\'Songti SC\',\'STSong\',\'SimSun\',serif;'
        f'font-size:15px;line-height:1.84;font-weight:600;">'
        f'{stylize_text(p, max_hits=2)}</span>'
      )
    rendered = ''.join(parts)
    # 多段时直接返回完整结构(不再包一层统一的span)
    return (
      f'<div style="margin:0;padding:12px 0 16px;background-color:#fff8f1;">'
      f'<span style="display:inline-block;max-width:100%;padding:2px 3px 4px;background-color:#f2dfc9;'
      f'border-radius:16px;">'
      f'<span style="display:inline-block;max-width:100%;padding:10px 14px;background-color:#fbefe0;'
      f'border:1px solid {WARM_BORDER};border-radius:14px;">'
      f'<span style="display:block;width:26px;height:3px;margin:0 0 12px;border-radius:999px;background-color:{WARM_LINE};"></span>'
      f'{rendered}'
      '</span>'
      '</span>'
      '</div>'
    )
  return (
    f'<div style="margin:0;padding:12px 0 16px;background-color:#fff8f1;">'
    f'<span style="display:inline-block;max-width:100%;padding:2px 3px 4px;background-color:#f2dfc9;'
    f'border-radius:16px;">'
    f'<span style="display:inline-block;max-width:100%;padding:10px 14px;background-color:#fbefe0;'
    f'border:1px solid {WARM_BORDER};border-radius:14px;">'
    f'<span style="display:block;width:26px;height:3px;margin:0 0 12px;border-radius:999px;background-color:{WARM_LINE};"></span>'
    f'<span style="display:block;color:{PALETTE["ink"]};font-family:\'Songti SC\',\'STSong\',\'SimSun\',serif;'
    f'font-size:15px;line-height:1.84;font-weight:600;">{rendered}</span>'
    '</span>'
    '</span>'
    '</div>'
  )


def prompt_lines_markup(prompt_text: str) -> str:
  lines = [line for line in prompt_text.splitlines() if line.strip()]
  if not lines:
    lines = [prompt_text]
  rendered: list[str] = []
  for line in lines:
    rendered.append(
      f'<p style="margin:0 0 8px;color:#372f28;font-size:13px;line-height:1.75;'
      f'font-family:\'SFMono-Regular\',\'JetBrains Mono\',\'Menlo\',\'PingFang SC\',monospace;'
      f'white-space:pre-wrap;word-break:break-word;">{escape_text(line)}</p>'
    )
  return "".join(rendered)


def render_prompt_card(label: str, prompt_text: str, *, show_hint: bool = True) -> str:
  line_count = len([line for line in prompt_text.splitlines() if line.strip()])
  scroll_style = "max-height:240px;overflow-y:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;padding-right:6px;"
  hint = "这段提示词已经锁成固定高度,可以直接上下滑动看完整内容。"
  if line_count <= 4 and len(prompt_text) <= 120:
    scroll_style = "max-height:240px;overflow-y:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;"
  hint_markup = (
    f'<p style="margin:10px 0 0;color:{PALETTE["muted"]};font-size:12px;line-height:1.6;">{escape_text(hint)}</p>'
    if show_hint
    else ""
  )
  return (
    f'<div style="margin:20px 0 24px;padding:18px 18px 16px;border-radius:24px;'
    f'background-color:{WARM_PANEL};border:1px solid {WARM_BORDER};">'
    f'<span style="display:inline-block;margin:0 0 8px;padding:5px 12px;border-radius:999px;'
    f'background-color:{WARM_PILL};color:{PALETTE["accent"]};font-size:11px;line-height:1.2;font-weight:700;letter-spacing:1.6px;">PROMPT</span>'
    f'<p style="margin:0 0 12px;color:{PALETTE["ink"]};font-size:18px;line-height:1.6;font-weight:600;">{escape_text(label)}</p>'
    f'<div style="padding:14px 15px;border-radius:18px;background-color:#fffdf9;border:1px solid {WARM_BORDER};{scroll_style}">'
    f'{prompt_lines_markup(prompt_text)}'
    "</div>"
    f"{hint_markup}"
    "</div>"
  )


def image_frame(src: str, alt: str, *, width: str, inline: bool = False, margin_right: str = "0") -> str:
  return (
    f'<span style="display:{"inline-block" if inline else "block"};vertical-align:top;width:{width};max-width:100%;'
    f'margin-right:{margin_right};white-space:normal;">'
    f'<span style="display:block;padding:4px;border-radius:24px;background-color:#fff7ee;border:1px solid {WARM_BORDER};">'
    f'<img src="{escape_text(src)}" alt="{escape_text(alt)}" '
    'style="display:block;width:100%;max-width:100%;height:auto;border-radius:20px;" />'
    "</span></span>"
  )


def render_single_image(block: dict) -> str:
  width = display_width(int(block.get("width", 0) or 0), int(block.get("height", 0) or 0))
  return (
    '<div style="margin:0;padding:18px 0 22px;text-align:center;background-color:#fff8f1;">'
    f'{image_frame(block["src"], block.get("alt", "文章配图"), width=width)}'
    '</div>'
  )


def _gallery_rows(n: int) -> list[int]:
  """
  根据图片数量返回每行的图片数量列表。
  规则:
    1 → [1](保持 single image,不走这里)
    2 → [2]
    3 → [3]
    4 → [2, 2]
    5 → [3, 2]
    6 → [3, 3]
    7 → [3, 2, 2]
    8 → [2, 2, 2, 2]
    通用:每行最多 3 张,按 3/3/3... 排,最后一行剩余居中
  """
  special: dict[int, list[int]] = {
    2: [2],
    3: [3],
    4: [2, 2],
    5: [3, 2],
    6: [3, 3],
    7: [3, 2, 2],
    8: [2, 2, 2, 2],
  }
  if n in special:
    return special[n]
  rows: list[int] = []
  remaining = n
  while remaining > 0:
    rows.append(min(3, remaining))
    remaining -= 3
  return rows


def render_gallery(blocks: list[dict]) -> str:
  """
  渲染多图画廊(网格布局)。
  微信后台兼容:用 table 布局,每行最多 3 张,按 _gallery_rows 规则分组。
  """
  n = len(blocks)
  if n == 0:
    return ""
  if n == 1:
    return render_single_image(blocks[0])

  rows = _gallery_rows(n)
  row_htmls: list[str] = []
  offset = 0
  for row_count in rows:
    chunk = blocks[offset:offset + row_count]
    offset += row_count
    # 每行用 table,宽度 100%
    # 每格等宽,内容是圆角图片
    col_pct = str(round(100 / row_count, 2))
    cells: list[str] = []
    for block in chunk:
      src = escape_text(block.get("src", ""))
      alt = escape_text(block.get("alt", "文章配图"))
      cells.append(
        f'<td style="width:{col_pct}%;padding:3px;vertical-align:top;">'
        f'<span style="display:block;padding:3px;border-radius:14px;'
        f'background-color:#fff7ee;border:1px solid {WARM_BORDER};">'
        f'<img src="{src}" alt="{alt}" '
        f'style="display:block;width:100%;height:auto;border-radius:11px;" />'
        f'</span>'
        f'</td>'
      )
    # 如果最后一行不满行,居中(用空单元格补)
    if len(chunk) < row_count:
      empty_cols = row_count - len(chunk)
      for _ in range(empty_cols):
        cells.insert(0, f'<td style="width:{col_pct}%;padding:3px;"></td>')
    row_htmls.append(
      f'<tr>{"".join(cells)}</tr>'
    )

  return (
    f'<div style="margin:0;padding:14px 0 22px;background-color:#fff8f1;">'
    f'<table style="width:100%;border-collapse:collapse;border-spacing:0;" cellpadding="0" cellspacing="0">'
    f'<tbody>'
    f'{"".join(row_htmls)}'
    f'</tbody>'
    f'</table>'
    f'</div>'
  )


def render_list_block(items: list[str], *, style: str = "unordered") -> str:
  chips: list[str] = []
  for index, item in enumerate(items):
    if not normalize_text(item):
      continue
    bullet = str(index + 1) if style == "ordered" else "•"
    chips.append(
      '<div style="display:flex;align-items:flex-start;gap:12px;margin:0 0 12px;">'
      f'<span style="display:inline-flex;flex:0 0 auto;align-items:center;justify-content:center;min-width:24px;height:24px;'
      f'border-radius:999px;background:rgba(184,98,60,0.12);color:{PALETTE["accent"]};font-size:12px;font-weight:700;">{escape_text(bullet)}</span>'
      f'<p style="margin:0;color:{PALETTE["text"]};font-size:15px;line-height:1.85;">{stylize_text(item, max_hits=1)}</p>'
      '</div>'
    )
  if not chips:
    return ""
  return (
    f'<div style="margin:0;padding:18px 0 24px;background-color:#fff8f1;">'
    f'<div style="padding:16px 16px 6px;border-radius:22px;'
    f'background-color:{WARM_PANEL};border:1px solid {WARM_BORDER};">'
    f'{"".join(chips)}'
    '</div></div>'
  )


def render_group_card(title: str, text: str) -> str:
  title_markup = ""
  if normalize_text(title):
    title_markup = (
      f'<p style="margin:0 0 8px;color:{PALETTE["ink"]};font-size:15px;line-height:1.6;'
      f'font-weight:700;">{escape_text(title)}</p>'
    )
  body_markup = (
    f'<p style="margin:0;color:{PALETTE["text"]};font-size:14px;line-height:1.82;">'
    f'{stylize_text(text, max_hits=1)}</p>'
  )
  return (
    f'<div style="height:100%;padding:16px 14px;border-radius:18px;background-color:{WARM_PANEL_SOFT};'
    f'border:1px solid {WARM_BORDER};">'
    f'<div style="width:28px;height:4px;margin:0 0 10px;border-radius:999px;background-color:{WARM_LINE};"></div>'
    f'{title_markup}{body_markup}'
    '</div>'
  )


def render_group_block(items: list[dict], *, layout: str = "horizontal") -> str:
  normalized_items = [
    {
      "title": normalize_text(item.get("title", "")),
      "text": normalize_text(item.get("text", "")),
    }
    for item in items
    if normalize_text(item.get("title", "")) or normalize_text(item.get("text", ""))
  ]
  if not normalized_items:
    return ""

  if layout == "vertical":
    cards = "".join(
      f'<div style="margin:0 0 10px;">{render_group_card(item["title"], item["text"])}</div>'
      for item in normalized_items
    )
    return f'<div style="margin:18px 0 24px;">{cards}</div>'

  rows: list[str] = []
  for offset in range(0, len(normalized_items), 3):
    chunk = normalized_items[offset:offset + 3]
    cells: list[str] = []
    for index, item in enumerate(chunk):
      width = "31.8%" if len(chunk) == 3 else "48.6%"
      margin_right = "10px" if index < len(chunk) - 1 else "0"
      cells.append(
        f'<span style="display:inline-block;vertical-align:top;width:{width};margin-right:{margin_right};">'
        f'{render_group_card(item["title"], item["text"])}'
        '</span>'
      )
    rows.append(f'<div style="margin:0 0 10px;white-space:nowrap;font-size:0;">{"".join(cells)}</div>')
  return f'<div style="margin:18px 0 24px;">{"".join(rows)}</div>'


def wrap_preview_block(markup: str, start_index: int, end_index: int, *, interactive: bool = False) -> str:
  if not interactive:
    return markup
  return (
    f'<section class="wx-preview-block" data-block-index="{start_index}" data-block-end="{end_index}">'
    f'{markup}'
    '</section>'
  )


def compose_article(article: dict, *, interactive: bool = False, show_prompt_hint: bool = True, wechat: bool = False) -> str:
  blocks = article["blocks"]
  parts: list[str] = []
  lead_budget = 2
  index = 0
  chapter_count = 0
  section_count = 0
  while index < len(blocks):
    block = blocks[index]
    block_type = block["type"]

    if block_type == "hero":
      parts.append(wrap_preview_block(render_hero_card(block), index, index, interactive=interactive))
      lead_budget = 0
      index += 1
      continue

    if block_type == "meta":
      parts.append(wrap_preview_block(render_meta(block["text"]), index, index, interactive=interactive))
      index += 1
      continue

    if block_type == "video":
      parts.append(wrap_preview_block(render_video_card(block), index, index, interactive=interactive))
      lead_budget = 0
      index += 1
      continue

    if block_type == "video_placeholder":
      # 自适应视频框:不限高度,宽度100%,overflow:hidden裁切圆角
      # 微信后台删掉占位文字后,光标在框内插入任意尺寸视频
      placeholder_html = (
        f'<div style="margin:0;padding:24px 0 28px;background-color:#fff8f1;">'
        f'<section style="padding:12px;'
        f'border:2px solid {WARM_BORDER};border-radius:16px;overflow:hidden;">'
        f'<p style="margin:0 0 10px;">'
        f'<span style="display:inline-block;padding:4px 10px;border-radius:999px;'
        f'background-color:{WARM_PILL};color:{PALETTE["accent"]};font-size:11px;'
        f'line-height:1.2;font-weight:700;letter-spacing:1.5px;">VIDEO</span></p>'
        f'<p style="margin:0;padding:50px 0;text-align:center;'
        f'color:{PALETTE["muted"]};font-size:13px;line-height:1.6;">'
        f'▶ 删除本段文字,在此处插入视频</p>'
        f'</section></div>'
      )
      parts.append(wrap_preview_block(placeholder_html, index, index, interactive=interactive))
      index += 1
      continue

    if block_type == "gallery":
      images = block.get("images", [])
      markup = render_single_image(images[0]) if len(images) == 1 else render_gallery(images)
      parts.append(wrap_preview_block(markup, index, index, interactive=interactive))
      lead_budget = 0
      index += 1
      continue

    if block_type == "image":
      start_index = index
      run: list[dict] = []
      while index < len(blocks) and blocks[index]["type"] == "image":
        run.append(blocks[index])
        index += 1
      # 末尾最后一张图（签名图等）单独一行
      is_tail = (index >= len(blocks))
      if len(run) == 1:
        markup = render_single_image(run[0])
        parts.append(wrap_preview_block(markup, start_index, start_index, interactive=interactive))
      elif is_tail and len(run) >= 2:
        front = run[:-1]
        front_markup = render_single_image(front[0]) if len(front) == 1 else render_gallery(front)
        parts.append(wrap_preview_block(front_markup, start_index, index - 2, interactive=interactive))
        last_markup = render_single_image(run[-1])
        parts.append(wrap_preview_block(last_markup, index - 1, index - 1, interactive=interactive))
      else:
        markup = render_gallery(run)
        parts.append(wrap_preview_block(markup, start_index, index - 1, interactive=interactive))
      continue

    if block_type == "prompt":
      markup = render_prompt_card(block.get("label", "这段提示词"), block.get("text", ""), show_hint=show_prompt_hint)
      parts.append(wrap_preview_block(markup, index, index, interactive=interactive))
      lead_budget = 0
      index += 1
      continue

    if block_type == "quote":
      parts.append(wrap_preview_block(render_quote(block.get("text", "")), index, index, interactive=interactive))
      lead_budget = 0
      index += 1
      continue

    if block_type == "highlight":
      parts.append(wrap_preview_block(render_highlight(block.get("text", "")), index, index, interactive=interactive))
      lead_budget = 0
      index += 1
      continue

    if block_type == "list":
      markup = render_list_block(block.get("items", []), style=block.get("style", "unordered"))
      if markup:
        parts.append(wrap_preview_block(markup, index, index, interactive=interactive))
      lead_budget = 0
      index += 1
      continue

    if block_type == "group":
      markup = render_group_block(block.get("items", []), layout=block.get("layout", "horizontal"))
      if markup:
        parts.append(wrap_preview_block(markup, index, index, interactive=interactive))
      lead_budget = 0
      index += 1
      continue

    prompt_block, next_index = collect_prompt_block(blocks, index)
    if prompt_block:
      parts.append(
        wrap_preview_block(
          render_prompt_card(prompt_block["label"], prompt_block["text"], show_hint=show_prompt_hint),
          index,
          next_index - 1,
          interactive=interactive,
        )
      )
      lead_budget = 0
      index = next_index
      continue

    text = block["text"]
    if block_type == "heading":
      chapter_count += 1
      section_count = 0
      parts.append(wrap_preview_block(render_heading(text, chapter_count), index, index, interactive=interactive))
      lead_budget = 0
      index += 1
      continue
    if block_type == "subheading":
      section_count += 1
      parts.append(wrap_preview_block(render_subheading(text, section_count), index, index, interactive=interactive))
      lead_budget = 0
      index += 1
      continue
    if is_inline_heading(blocks, index, text):
      chapter_count += 1
      section_count = 0
      parts.append(wrap_preview_block(render_heading(text, chapter_count), index, index, interactive=interactive))
      lead_budget = 0
      index += 1
      continue
    if quote_like(text):
      parts.append(wrap_preview_block(render_quote(text), index, index, interactive=interactive))
      index += 1
      continue

    parts.append(wrap_preview_block(render_paragraph(text, lead=lead_budget > 0), index, index, interactive=interactive))
    if lead_budget > 0:
      lead_budget -= 1
    index += 1
  article_inner = "".join(parts)
  markup = (
    '<section style="padding:26px 18px 34px;background-color:#fff8f1;'
    'border-radius:28px;">'
    f'{article_inner}'
    '</section>'
  )
  if wechat:
    markup = sanitize_for_wechat(markup)
  return markup


# ---------------------------------------------------------------------------
# 微信HTML净化层 -- 后处理方式,不侵入 render_*() 函数
# ---------------------------------------------------------------------------

_GRADIENT_RE = re.compile(
    r"(background(?:-image)?)\s*:\s*linear-gradient\([^)]+\)",
    re.IGNORECASE,
)
_BORDER_RADIUS_RE = re.compile(
    r"border-radius\s*:\s*[^;\"']+;?",
    re.IGNORECASE,
)
_BOX_SHADOW_RE = re.compile(
    r"box-shadow\s*:\s*[^;\"']+;?",
    re.IGNORECASE,
)
_MAX_HEIGHT_RE = re.compile(
    r"max-height\s*:\s*[^;\"']+;?",
    re.IGNORECASE,
)
_OVERFLOW_RE = re.compile(
    r"overflow(?:-[xy])?\s*:\s*(?:auto|scroll|hidden)[^;]*;?",
    re.IGNORECASE,
)
_WEBKIT_OVERFLOW_RE = re.compile(
    r"-webkit-overflow-scrolling\s*:\s*[^;\"']+;?",
    re.IGNORECASE,
)
_OVERSCROLL_RE = re.compile(
    r"overscroll-behavior\s*:\s*[^;\"']+;?",
    re.IGNORECASE,
)


def _sanitize_flex_to_table(html_str: str) -> str:
    """
    将 display:flex 列表项改用 table 布局。
    匹配 render_list_block 输出的 flex 行:
      <div style="display:flex;align-items:flex-start;gap:12px;...">
        <span ...>bullet</span>
        <p ...>text</p>
      </div>
    → 改成 table-row 方式
    """
    # 替换 flex 容器 div → table 行
    html_str = re.sub(
        r'<div\s+style="display:flex;align-items:flex-start;gap:12px;([^"]*)">\s*'
        r'(<span\s+style="display:inline-flex;flex:0 0 auto;align-items:center;justify-content:center;'
        r'min-width:24px;height:24px;[^"]*">[^<]*</span>)\s*'
        r'(<p\s)',
        lambda m: (
            f'<table style="width:100%;border-collapse:collapse;{m.group(1)}" cellpadding="0" cellspacing="0"><tr>'
            f'<td style="width:28px;vertical-align:top;padding-right:10px;">'
            + re.sub(r'display:inline-flex;flex:0 0 auto;align-items:center;justify-content:center;',
                     'display:inline-block;text-align:center;', m.group(2))
            + '</td>'
            f'<td style="vertical-align:top;">'
            + m.group(3)
        ),
        html_str,
    )
    # 对应的闭合 </p></div> → </p></td></tr></table>
    # 但这很难用正则精确匹配,所以改用更直接的方式:
    # 直接把所有 display:flex 替换,然后用简单的 tag replacement
    return html_str


def sanitize_for_wechat(html_str: str) -> str:
    """
    对最终输出的 HTML 做微信兼容净化。
    策略:纯字符串/正则替换,不依赖 BeautifulSoup。

    规则:
    1. <section> → <span style="display:block;">(保留 inline style)
    2. <div> → <span style="display:block;">(保留 inline style)
    3. <strong> → <span style="font-weight:bold;">(保留其他 inline style)
    4. display:flex → 改成 table 布局
    5. border-radius → 删除
    6. linear-gradient → 改为纯色
    7. box-shadow → 删除
    8. max-height + overflow → 删除(微信不支持滚动)
    9. 保留 <table>/<tr>/<td>/<p>/<span>/<img>/<a>
    """
    out = html_str

    # --- 1. display:flex 列表项 → table 布局 ---
    # render_list_block 的 flex 行
    out = re.sub(
        r'<div style="display:flex;align-items:flex-start;gap:12px;margin:0 0 12px;">',
        '<table style="width:100%;border-collapse:collapse;margin:0 0 12px;" cellpadding="0" cellspacing="0"><tr>',
        out,
    )
    # flex 行里的 bullet span(inline-flex → inline-block)
    out = re.sub(
        r'display:inline-flex;flex:0 0 auto;align-items:center;justify-content:center;',
        'display:inline-block;text-align:center;',
        out,
    )
    # bullet span 后面跟的 <p> 需要被包在 <td> 里
    # 模式:</span><p → </span></td><td style="vertical-align:top;"><p
    # 但只在 flex→table 转换的上下文中
    # 用更精确的替换:bullet span 的闭合后紧跟的 <p>
    out = re.sub(
        r'(font-weight:700;">(?:[^<]*)</span>)\s*(<p\s+style="margin:0;)',
        r'\1</td><td style="vertical-align:top;">\2',
        out,
    )
    # 在 bullet 前面加 <td>
    out = re.sub(
        r'(<table style="width:100%;border-collapse:collapse;margin:0 0 12px;"[^>]*><tr>)\s*(<span\s+style="display:inline-block;text-align:center;)',
        r'\1<td style="width:28px;vertical-align:top;padding-right:10px;">\2',
        out,
    )
    # 闭合:原来 flex div 的 </div> 变成 </td></tr></table>
    # 这比较 tricky - 需要找到 table 行的结尾
    # 简单做法:先把所有 </p></div> 在上下文里改
    # 实际上,flex list item 的 HTML 结构是:
    #   <div style="display:flex...">
    #     <span ...>bullet</span>
    #     <p ...>text</p>
    #   </div>
    # 转换后变成:
    #   <table ...><tr>
    #     <td ...><span ...>bullet</span></td>
    #     <td ...><p ...>text</p>     ← 缺 </td></tr></table>
    #   </div>                         ← 多余的 </div>
    # 所以需要把紧跟 table-row 内容后的 </div> 替换成 </td></tr></table>
    # 策略:后面统一做 div→span 替换时,这个 </div> 会变成 </span>
    # 但为了安全,先用一个标记

    # --- 2. linear-gradient → 纯色 ---
    def _gradient_to_solid(m: re.Match) -> str:
        prop = m.group(1)
        # 从渐变中提取最后一个颜色作为纯色
        colors = re.findall(r'(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\))', m.group(0))
        fallback = colors[-1] if colors else "#f3ebe1"
        return f"{prop}:{fallback}"

    out = _GRADIENT_RE.sub(_gradient_to_solid, out)

    # --- 3. border-radius → 保留(微信渲染层支持)---
    # out = _BORDER_RADIUS_RE.sub("", out)

    # --- 4. box-shadow → 删除 ---
    out = _BOX_SHADOW_RE.sub("", out)

    # --- 5. max-height / overflow / -webkit-overflow-scrolling / overscroll-behavior → 删除 ---
    out = _MAX_HEIGHT_RE.sub("", out)
    out = _OVERFLOW_RE.sub("", out)
    out = _WEBKIT_OVERFLOW_RE.sub("", out)
    out = _OVERSCROLL_RE.sub("", out)

    # --- 6. <section> → <span style="display:block;"> ---
    # 有 style 的 section
    out = re.sub(
        r'<section\s+style="([^"]*)"',
        r'<span style="display:block;\1"',
        out,
    )
    # 无 style 但有其他属性的 section
    out = re.sub(
        r'<section\s+([^>]*?)>',
        r'<span style="display:block;" \1>',
        out,
    )
    # 纯 <section>
    out = out.replace("<section>", '<span style="display:block;">')
    out = out.replace("</section>", "</span>")

    # --- 7. <div> → <span style="display:block;"> ---
    # 有 style 的 div
    out = re.sub(
        r'<div\s+style="([^"]*)"',
        r'<span style="display:block;\1"',
        out,
    )
    # 纯 <div> 或有 class 的 div(不应该出现在文章 markup 里,但以防万一)
    out = re.sub(
        r'<div(?:\s[^>]*)?>',
        '<span style="display:block;">',
        out,
    )
    out = out.replace("</div>", "</span>")

    # --- 8. <strong> → <span style="font-weight:bold;"> ---
    # <strong style="..."> → <span style="font-weight:bold;...">
    out = re.sub(
        r'<strong\s+style="([^"]*)"',
        r'<span style="font-weight:bold;\1"',
        out,
    )
    # 纯 <strong>
    out = out.replace("<strong>", '<span style="font-weight:bold;">')
    out = out.replace("</strong>", "</span>")

    # --- 9. 清理多余分号和空 style ---
    out = re.sub(r'style=";\s*', 'style="', out)
    out = re.sub(r';;+', ';', out)
    out = re.sub(r'style="\s*"', '', out)

    # --- 10. 修复 flex→table 转换后多余的 </span>(原来的 </div>)---
    # table 行结尾应该是 </td></tr></table> 而不是 </span>
    # 匹配模式:</p></span> 紧跟在 table 行内
    # 简单做法:找到每个 <table...margin:0 0 12px 开头的行,
    # 确保其后第一个未配对的 </span> 变成 </td></tr></table>
    # 用标记法更安全
    parts = out.split('<table style="width:100%;border-collapse:collapse;margin:0 0 12px;"')
    if len(parts) > 1:
        rebuilt = [parts[0]]
        for part in parts[1:]:
            # 找这个 table 片段中第一个 </p> 后紧跟的 </span>
            # 这个 </span> 是原来 flex div 的闭合,应该变成 </td></tr></table>
            fixed = re.sub(
                r'(</p>)\s*(</span>)',
                r'\1</td></tr></table>',
                part,
                count=1,
            )
            rebuilt.append(fixed)
        out = '<table style="width:100%;border-collapse:collapse;margin:0 0 12px;"'.join(rebuilt)

    return out


def build_source_html(title: str, article_markup: str) -> str:
  return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escape_text(title)}</title>
</head>
<body style="margin:0;background:#faf5ee;">
  <main style="max-width:460px;margin:0 auto;padding:28px 20px 56px;background:#ffffff;">
    {article_markup}
  </main>
</body>
</html>"""


def build_copy_page(title: str, article_markup: str) -> str:
  copy_script = r"""
(() => {
  const article = document.getElementById("wx-article");
  const statusEl = document.getElementById("status");
  function setStatus(msg) { if (statusEl) statusEl.textContent = msg; }

  document.getElementById("btn-copy").addEventListener("click", async () => {
    try {
      const html = article.innerHTML;
      const plain = article.innerText;
      if (navigator.clipboard && window.ClipboardItem) {
        const item = new ClipboardItem({
          "text/html": new Blob([html], { type: "text/html" }),
          "text/plain": new Blob([plain], { type: "text/plain" }),
        });
        await navigator.clipboard.write([item]);
        setStatus("已复制！去微信后台粘贴吧。");
      } else {
        const range = document.createRange();
        range.selectNodeContents(article);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.execCommand("copy");
        sel.removeAllRanges();
        setStatus("已复制！去微信后台粘贴吧。");
      }
    } catch(e) {
      setStatus("复制失败: " + e.message);
    }
  });

  document.getElementById("btn-select").addEventListener("click", () => {
    const range = document.createRange();
    range.selectNodeContents(article);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    setStatus("正文已选中，直接 Cmd+C 复制。");
  });
})();
  """

  return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escape_text(title)} · 公众号复制页</title>
  <style>
    body {{
      margin: 0;
      background: linear-gradient(180deg, #fbf6ef 0%, #f3ebe1 100%);
      color: {PALETTE["ink"]};
      font-family: "PingFang SC", sans-serif;
    }}
    .app {{ width: min(720px, calc(100vw - 32px)); margin: 0 auto; padding: 28px 0 56px; }}
    .toolbar {{
      display: flex; align-items: center; gap: 10px;
      padding: 12px 18px; margin-bottom: 16px;
      background: rgba(255,255,255,0.8); border-radius: 14px;
      box-shadow: 0 1px 6px rgba(0,0,0,0.06);
    }}
    .toolbar button {{
      padding: 8px 16px; border-radius: 8px; font-size: 13px;
      font-weight: 600; cursor: pointer; border: 1.5px solid #ead8c2;
      background: #fff; color: {PALETTE["accent"]};
    }}
    .toolbar button:hover {{ background: {PALETTE["accent"]}; color: #fff; border-color: {PALETTE["accent"]}; }}
    .toolbar .status {{ flex: 1; font-size: 12px; color: #9c8e7e; text-align: right; }}
    .preview {{ margin-top: 8px; }}
    .note {{ font-size: 12px; color: #9c8e7e; margin-bottom: 8px; }}
  </style>
</head>
<body>
  <div class="app">
    <div class="toolbar">
      <button id="btn-copy">复制到微信</button>
      <button id="btn-select">选中正文</button>
      <div class="status" id="status">准备好了。点复制，去公众号后台粘贴。</div>
    </div>
    <section class="preview">
      <p class="note">下面是排版后的正文内容：</p>
      <main id="wx-article">
        {article_markup}
      </main>
    </section>
  </div>
  <script>{copy_script}</script>
</body>
</html>"""


def build_preview_page(title: str, article_markup: str, *, interactive: bool = False) -> str:
  extra_style = ""
  extra_script = ""
  if interactive:
    extra_style = """
    .wx-preview-block {
      position: relative;
      transition: box-shadow 120ms ease, background 120ms ease, transform 120ms ease;
      cursor: pointer;
    }
    .wx-preview-block[data-block-active="1"] {
      background: rgba(248, 239, 228, 0.88);
      box-shadow: 0 0 0 3px rgba(184, 98, 60, 0.18);
      border-radius: 20px;
      transform: translateY(-1px);
    }
    """
    extra_script = """
  <script>
    (() => {
      const blocks = () => Array.from(document.querySelectorAll(".wx-preview-block"));
      let activeIndex = null;

      const setActive = (index, shouldScroll) => {
        activeIndex = index;
        for (const block of blocks()) {
          block.removeAttribute("data-block-active");
        }
        const current = document.querySelector(`.wx-preview-block[data-block-index="${index}"]`);
        if (!current) return;
        current.setAttribute("data-block-active", "1");
        if (shouldScroll) {
          current.scrollIntoView({ block: "center", behavior: "smooth" });
        }
      };

      window.focusBlock = (index) => {
        setActive(Number(index), true);
      };

      document.addEventListener("click", (event) => {
        const target = event.target.closest(".wx-preview-block");
        if (!target) return;
        const index = Number(target.getAttribute("data-block-index"));
        setActive(index, false);
        window.parent.postMessage({ source: "svg-wechat-preview", blockIndex: index }, "*");
      });

      window.addEventListener("message", (event) => {
        if (event.data?.source !== "svg-wechat-editor") return;
        if (typeof event.data.blockIndex !== "number") return;
        setActive(event.data.blockIndex, true);
      });

      if (activeIndex === null) {
        const first = document.querySelector(".wx-preview-block");
        if (first) {
          first.setAttribute("data-block-active", "1");
          activeIndex = Number(first.getAttribute("data-block-index"));
        }
      }
    })();
  </script>"""
  return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escape_text(title)} · 自研预览</title>
  <style>
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top, rgba(255, 245, 231, 0.78), rgba(255, 245, 231, 0) 38%),
        linear-gradient(180deg, #fbf6ef 0%, #f3ebe1 100%);
      font-family: "Iowan Old Style", "Songti SC", "Noto Serif SC", serif;
    }}
    main {{
      width: min(520px, calc(100vw - 28px));
      margin: 0 auto;
      padding: 30px 0 96px;
    }}
    .card {{
      padding: 32px 20px 60px;
      background: #fff;
    }}
    {extra_style}
  </style>
</head>
<body>
  <main>
    <section class="card">{article_markup}</section>
  </main>
  {extra_script}
</body>
</html>"""


def footer_data_url(path: Path) -> str | None:
  if not path.exists():
    return None
  mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
  return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def default_output_dir(title: str) -> Path:
  return OUTPUT_ROOT / slugify(title)


def build_payload(title: str, article: dict, *, source_url: str = "") -> dict:
  return {
    "title": title,
    "source_url": source_url,
    "article": article,
    "block_count": len(article.get("blocks", [])),
  }


def render_output_bundle(
  title: str,
  article: dict,
  *,
  interactive_preview: bool = False,
  copy_prompt_hint: bool = False,
  preview_prompt_hint: bool = True,
  wechat_post_sanitize: bool = False,
) -> dict[str, str]:
  # preview 模式:保留原样式(border-radius, flex 等),供编辑器预览
  preview_markup_raw = compose_article(article, show_prompt_hint=copy_prompt_hint)
  source_html = build_source_html(title, preview_markup_raw)

  # copy 模式:微信净化后的 HTML,用于粘贴到微信后台
  wechat_markup = compose_article(article, show_prompt_hint=copy_prompt_hint, wechat=True)
  if wechat_post_sanitize:
    wechat_markup = sanitize_copy_for_wechat(wechat_markup)
  copy_html = build_copy_page(title, wechat_markup)

  # 编辑器 interactive 预览
  preview_markup = compose_article(article, interactive=interactive_preview, show_prompt_hint=preview_prompt_hint)
  preview_html = build_preview_page(title, preview_markup, interactive=interactive_preview)

  # 额外:微信预览页(净化后效果预览,不带复制按钮)
  wechat_preview_markup = compose_article(article, show_prompt_hint=preview_prompt_hint, wechat=True)
  if wechat_post_sanitize:
    wechat_preview_markup = sanitize_copy_for_wechat(wechat_preview_markup)
  wechat_preview_html = build_preview_page(title, wechat_preview_markup)

  return {
    "article_markup": preview_markup_raw,
    "source_html": source_html,
    "copy_html": copy_html,
    "preview_html": preview_html,
    "wechat_preview_html": wechat_preview_html,
  }


# ---------------------------------------------------------------------------
# 微信 HTML 净化后处理 -- CLI --wechat 模式专用
# ---------------------------------------------------------------------------
# 在 compose_article / render_* 完成后,对最终 article HTML 做一次统一净化。
# 纯 re 替换,不引入新依赖。

_WX_GRADIENT_RE = re.compile(
    r"linear-gradient\([^)]*\)",
    re.IGNORECASE,
)
_WX_BORDER_RADIUS_RE = re.compile(
    r"border-radius\s*:\s*[^;\"']+;?",
    re.IGNORECASE,
)
_WX_BOX_SHADOW_RE = re.compile(
    r"box-shadow\s*:\s*[^;\"']+;?",
    re.IGNORECASE,
)
_WX_DISPLAY_FLEX_RE = re.compile(
    r"display\s*:\s*flex\b",
    re.IGNORECASE,
)
_WX_DISPLAY_INLINE_FLEX_RE = re.compile(
    r"display\s*:\s*inline-flex\b",
    re.IGNORECASE,
)


def _is_inside_table(html: str, pos: int) -> bool:
    """粗略判断 pos 是否在 <table>...</table> 内部。"""
    before = html[:pos]
    opens = len(re.findall(r"<table[\s>]", before, re.IGNORECASE))
    closes = len(re.findall(r"</table>", before, re.IGNORECASE))
    return opens > closes


def _replace_div_outside_table(html: str) -> str:
    """<div → <p 、</div> → </p>,但 table 内部的保持不动。"""
    # 开标签
    result_parts: list[str] = []
    last_end = 0
    for m in re.finditer(r"<div(\s|>|/>)", html, re.IGNORECASE):
        if _is_inside_table(html, m.start()):
            continue
        result_parts.append(html[last_end:m.start()])
        result_parts.append(f"<p{m.group(1)}")
        last_end = m.end()
    result_parts.append(html[last_end:])
    html = "".join(result_parts)

    # 闭标签
    result_parts = []
    last_end = 0
    for m in re.finditer(r"</div>", html, re.IGNORECASE):
        if _is_inside_table(html, m.start()):
            continue
        result_parts.append(html[last_end:m.start()])
        result_parts.append("</p>")
        last_end = m.end()
    result_parts.append(html[last_end:])
    return "".join(result_parts)


def sanitize_copy_for_wechat(html: str) -> str:
    """
    接收完整排版 article HTML,返回微信兼容的净化 HTML。

    规则:
     1. <section → <p ,</section> → </p>
     2. <div → <p ,</div> → </p>(table 内部不动)
     3. 删除 border-radius
     4. 删除 box-shadow
     5. linear-gradient(...) → background-color:#B8623C
     6. display:flex → display:block
     7. display:inline-flex → display:inline-block
     8. 保留 table/tr/td/th/img/span/p/strong/em/a/br
     9. #8d5b2d → #B8623C
    """
    out = html

    # 1. <section> → <p>
    out = re.sub(r"<section(\s|>)", r"<p\1", out, flags=re.IGNORECASE)
    out = re.sub(r"</section>", "</p>", out, flags=re.IGNORECASE)

    # 2. <div> → <p>(table 内部不动)
    out = _replace_div_outside_table(out)

    # 3. border-radius → 保留(微信渲染层支持,第三方编辑器也保留)
    # out = _WX_BORDER_RADIUS_RE.sub("", out)

    # 4. box-shadow → 删除(微信不稳定)
    out = _WX_BOX_SHADOW_RE.sub("", out)

    # 5. linear-gradient → 品牌纯色
    out = _WX_GRADIENT_RE.sub("#B8623C", out)
    # 修正属性名:background: #hex → background-color: #hex
    out = re.sub(
        r"(background(?:-image)?)\s*:\s*#B8623C",
        r"background-color:#B8623C",
        out,
    )

    # 6. display:flex → display:block
    out = _WX_DISPLAY_FLEX_RE.sub("display:block", out)

    # 7. display:inline-flex → display:inline-block
    out = _WX_DISPLAY_INLINE_FLEX_RE.sub("display:inline-block", out)

    # 8. 保留 table/tr/td/th/img/span/p/strong/em/a/br - 不需要额外操作

    # 9. 高亮色替换
    out = out.replace("#8d5b2d", "#B8623C")
    out = out.replace("#8D5B2D", "#B8623C")

    # 清理多余分号和空 style
    out = re.sub(r";\s*;", ";", out)
    out = re.sub(r'style=";\s*', 'style="', out)
    out = re.sub(r'style="\s*"', "", out)

    return out


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="自研飞书 -> 公众号复制页生成器")
  parser.add_argument("--url", required=True, help="飞书公开文档链接")
  parser.add_argument("--output-dir", default="", help="输出目录,不传则按标题生成")
  parser.add_argument("--footer-image", default=str(DEFAULT_FOOTER), help="文末尾图,不存在则跳过")
  parser.add_argument("--wechat", action="store_true", default=False, help="输出微信净化版(额外后处理)")
  parser.add_argument("--theme", default="赤铜橙", choices=list(THEMES.keys()),
                      help="色系名称，默认赤铜橙")
  return parser.parse_args()


def _inline_local_images(html: str) -> str:
  """把 /api/local-image?path=xxx 替换为 base64 data URL,让 copy.html 脱离 server 也能显示图片。"""
  import base64, mimetypes
  def _replace_match(m):
    local_path = m.group(1)
    p = Path(local_path)
    if p.exists():
      mime = mimetypes.guess_type(str(p))[0] or "image/png"
      b64 = base64.b64encode(p.read_bytes()).decode()
      return f'data:{mime};base64,{b64}'
    return m.group(0)  # 文件不存在则保留原路径
  return re.sub(r'/api/local-image\?path=([^"\'&]+)', _replace_match, html)


def write_outputs(output_dir: Path, payload: dict, *, wechat: bool = False) -> None:
  output_dir.mkdir(parents=True, exist_ok=True)
  bundle = render_output_bundle(payload["title"], payload["article"], wechat_post_sanitize=wechat)
  # 把所有本地图片内联为 base64
  for key in ("source_html", "copy_html", "preview_html", "wechat_preview_html"):
    if key in bundle:
      bundle[key] = _inline_local_images(bundle[key])

  (output_dir / "article.json").write_text(json.dumps(payload["article"], ensure_ascii=False, indent=2), encoding="utf-8")
  (output_dir / "source.html").write_text(bundle["source_html"], encoding="utf-8")
  (output_dir / "preview.html").write_text(bundle["preview_html"], encoding="utf-8")
  (output_dir / "copy.html").write_text(bundle["copy_html"], encoding="utf-8")
  (output_dir / "index.html").write_text(bundle["copy_html"], encoding="utf-8")
  (output_dir / "wechat_preview.html").write_text(bundle["wechat_preview_html"], encoding="utf-8")


def main() -> None:
  global WARM_BORDER, WARM_PANEL, WARM_PANEL_SOFT, WARM_PILL, WARM_LINE
  args = parse_args()

  # ── 应用色系 ──
  theme = THEMES[args.theme]
  PALETTE["ink"] = theme["ink"]
  PALETTE["text"] = theme["text"]
  PALETTE["muted"] = theme["muted"]
  PALETTE["accent"] = theme["accent"]
  PALETTE["accent_soft"] = theme["accent_soft"]
  PALETTE["line"] = theme["line"]
  PALETTE["paper"] = theme["paper"]
  PALETTE["paper_deep"] = theme["paper_deep"]
  WARM_BORDER = theme["warmBorder"]
  WARM_PANEL = theme["warmPanel"]
  WARM_PANEL_SOFT = theme["warmPanelSoft"]
  WARM_PILL = theme["warmPill"]
  WARM_LINE = theme["warmLine"]

  title, raw_blocks, image_data = extract_from_feishu_api(args.url)
  output_dir = Path(args.output_dir).resolve() if args.output_dir else default_output_dir(title)
  article = normalize_article(title, raw_blocks, image_data, footer_data_url(Path(args.footer_image).resolve()))
  payload = build_payload(title, article, source_url=args.url)
  write_outputs(output_dir, payload, wechat=args.wechat)

  print(json.dumps(
    {
      "title": title,
      "output_dir": str(output_dir),
      "article_json": str(output_dir / "article.json"),
      "preview": str(output_dir / "preview.html"),
      "copy": str(output_dir / "copy.html"),
      "block_count": len(article["blocks"]),
    },
    ensure_ascii=False,
    indent=2,
  ))


if __name__ == "__main__":
  main()
