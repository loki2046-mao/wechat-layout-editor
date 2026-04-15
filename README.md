# 公众号排版编辑器 — 飞书文档一键转微信排版

将飞书文档一键转为公众号排版成品。支持可视化块级编辑、6种色系切换，生成的 HTML 可直接粘贴到微信公众号后台。

> 作者：赛博小熊猫Loki

## ✨ 功能

- **飞书文档直读**：通过飞书 API 直接读取文档结构，无需浏览器渲染
- **智能排版引擎**：自动识别标题、正文、高亮块、提示词、列表、图片等内容类型
- **可视化编辑器**：块级拖拽排序、删除、合并、拆分、类型切换
- **6种色系**：一键切换整体配色，适配不同内容调性
- **微信兼容**：输出经过微信后台净化处理，粘贴即用
- **图片内联**：所有图片自动下载并转为 base64，HTML 文件完全自包含
- **线上版**：纯前端版本，可直接部署到任意静态托管

<!-- 截图占位：编辑器界面 -->
<!-- ![编辑器截图](screenshots/editor.png) -->

## 📦 安装

### 本地版

```bash
git clone https://github.com/<your-repo>/wechat-layout-editor.git
cd wechat-layout-editor
```

#### 依赖

- **Python 3.10+**
- **lark-cli**：飞书命令行工具（用于读取文档内容和下载图片）

```bash
# 检查 Python 版本
python3 --version

# 安装 lark-cli（如果还没有）
# 参考 lark-cli 文档完成安装和认证
lark-cli auth login
```

### Cola Skill 版

如果你使用 [Cola](https://cola.so)，可以直接作为 Skill 安装：

```bash
git clone https://github.com/<your-repo>/wechat-layout-editor.git ~/.cola/skills/wechat-layout-editor
```

安装后对 Cola 说「帮我排版」或「飞书转公众号」即可触发。

## 🚀 使用方法

### 方式一：一站式服务（推荐）

```bash
python3 server/layout_server.py
```

浏览器打开 `http://localhost:8790`，粘贴飞书链接，一键生成排版并进入编辑器。

### 方式二：命令行直接调用

```bash
python3 engine/feishu_to_copy_page.py \
  --url "https://xxx.feishu.cn/docx/xxxxx" \
  --wechat \
  --output-dir "./output"
```

生成的文件：
- `copy.html` — 复制页（点击按钮复制到微信后台）
- `editor.html` — 可视化编辑器
- `preview.html` — 预览页
- `article.json` — 结构化文章数据

### 方式三：线上版（纯前端）

打开 `online/index.html`，在文本框中粘贴文章内容，选择色系后即可在线排版。

线上版不依赖后端服务，可直接部署到 GitHub Pages、Vercel、Netlify 等静态托管平台。

## 🎨 色系展示

支持 6 种精心调配的色系，覆盖不同内容场景：

| 色系 | 强调色 accent | 背景色 warmBg | 药丸色 warmPill | 边框色 warmBorder | 装饰线 warmLine | 面板色 warmPanel | 适用场景 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|------|
| 🟠 赤铜橙 | `#B8623C` | `#fff8f1` | `#f5e0c5` | `#ead8c2` | `#d6ab81` | `#fff5e9` | 默认，温暖人文 |
| 🔵 青石蓝 | `#4A7B9D` | `#f0f5f8` | `#d4e6f0` | `#b8d4e3` | `#7ab0cc` | `#e8f0f5` | 冷静理性、科技 |
| 🟢 松绿   | `#3D8B6E` | `#f0f8f4` | `#d0ebde` | `#b2d8c5` | `#6db898` | `#e5f3ec` | 自然清新、环保 |
| 🔴 玫瑰红 | `#B85A6C` | `#fdf2f4` | `#f5d4da` | `#eac2c8` | `#d68a98` | `#fae8eb` | 情感温柔、女性 |
| 🟡 琥珀黄 | `#B8923C` | `#fdf8f0` | `#f5e8c5` | `#eadcc2` | `#d6c081` | `#f8f0e2` | 明亮活力、教育 |
| ⚫ 石墨灰 | `#6B7280` | `#f5f5f6` | `#e0e2e5` | `#d1d5db` | `#9ca3af` | `#ebedf0` | 简约商务、中性 |

色系配置存储在 `themes/themes.json`，可自行扩展。

## 📁 项目结构

```
wechat-layout-editor/
├── README.md                   # 本文件
├── LICENSE                     # MIT License
├── SKILL.md                    # Cola Skill 定义
├── engine/
│   ├── feishu_to_copy_page.py  # 排版引擎核心（飞书API读取 + HTML生成）
│   └── editor.html             # 可视化块编辑器
├── server/
│   └── layout_server.py        # 一站式 HTTP 服务（端口 8790）
├── online/
│   └── index.html              # 线上纯前端版（可直接部署）
└── themes/
    └── themes.json             # 6种色系配置
```

## 🔧 工作原理

1. **文档读取**：通过 `lark-cli` 调用飞书 API，获取文档的完整 block 结构
2. **内容解析**：智能识别标题、段落、高亮块（callout）、提示词、列表、图片、视频等
3. **自动排版**：根据内容类型匹配排版组件（导读卡、章节标题、金句高亮、提示词卡片等）
4. **HTML 生成**：输出微信兼容的内联样式 HTML，所有图片转 base64 自包含
5. **可视化编辑**：在编辑器中进行块级调整，实时预览效果
6. **一键复制**：点击复制按钮，直接粘贴到微信公众号后台

## 📝 线上版说明

`online/index.html` 是一个完全独立的纯前端版本：

- 不需要 Python、不需要 lark-cli、不需要后端服务
- 在文本框中直接粘贴文章内容（支持 Markdown 格式的标题标记）
- 支持所有 6 种色系切换
- 包含完整的可视化编辑器功能
- 可直接部署到任意静态托管平台

适合不使用飞书、或只需要快速排版纯文本内容的场景。

## 📄 许可

[MIT License](LICENSE) — Copyright (c) 2025 赛博小熊猫Loki
