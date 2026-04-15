---
name: wechat-layout-editor
description: >
  飞书文档一键转公众号排版编辑器，6种色系可选。接收飞书文档链接，自动抓取内容、生成排版 HTML，
  并打开可视化编辑器进行块级编辑（移动、删除、合并、变色、拆分、类型切换）后复制到微信后台。
  支持6种色系切换：赤铜橙、青石蓝、松绿、玫瑰红、琥珀黄、石墨灰。
  Use when 用户说"排版""公众号排版""微信排版""layout""帮我排版""飞书转公众号"
  "帮我把飞书文档排版""用绿色系排版""换个色系""排版编辑器"，
  或提供飞书文档链接并希望转为公众号可粘贴的排版成品。
author: 赛博小熊猫Loki
---

# 公众号排版编辑器

将飞书文档一键转为公众号排版，支持可视化块编辑和多色系切换。

## 安装

```bash
git clone https://github.com/<your-repo>/wechat-layout-editor.git
cd wechat-layout-editor
```

## 本地依赖

此 Skill 依赖本地安装的以下工具：

- **Python 3.10+**
- **lark-cli**（已配置飞书认证，用于读取飞书文档内容和下载图片）

依赖检查：
```bash
python3 --version    # 需要 3.10+
lark-cli --version   # 需要已安装并完成 auth login
```

## 色系

6种可选色系，用户可通过名称或颜色描述指定，默认为「赤铜橙」。

| 色系名 | accent | warmBg | warmPill | warmBorder | warmLine | warmPanel | 适用场景 |
|--------|--------|--------|----------|------------|----------|-----------|---------|
| 赤铜橙 | #B8623C | #fff8f1 | #f5e0c5 | #ead8c2 | #d6ab81 | #fff5e9 | 默认，温暖人文 |
| 青石蓝 | #4A7B9D | #f0f5f8 | #d4e6f0 | #b8d4e3 | #7ab0cc | #e8f0f5 | 冷静理性、科技 |
| 松绿   | #3D8B6E | #f0f8f4 | #d0ebde | #b2d8c5 | #6db898 | #e5f3ec | 自然清新、环保 |
| 玫瑰红 | #B85A6C | #fdf2f4 | #f5d4da | #eac2c8 | #d68a98 | #fae8eb | 情感温柔、女性 |
| 琥珀黄 | #B8923C | #fdf8f0 | #f5e8c5 | #eadcc2 | #d6c081 | #f8f0e2 | 明亮活力、教育 |
| 石墨灰 | #6B7280 | #f5f5f6 | #e0e2e5 | #d1d5db | #9ca3af | #ebedf0 | 简约商务、中性 |

色系配置文件：`themes/themes.json`

## 执行流程

### 1. 首次使用检查依赖

```bash
python3 --version
lark-cli --version
```

如果 `lark-cli` 未安装或未登录，提示用户先完成配置。

### 2. 解析用户输入

从用户消息中提取：

- **飞书链接**：包含 `feishu.cn/docx/`、`feishu.cn/wiki/`、`feishu.cn/doc/` 的 URL
- **色系名**（可选）：匹配色系名称或颜色描述

色系快速匹配规则：

| 用户说的话 | 色系 |
|-----------|------|
| "用橙色""默认色""赤铜" | 赤铜橙 |
| "用蓝色""冷色""科技感" | 青石蓝 |
| "用绿色""清新""自然" | 松绿 |
| "用红色""粉色""温柔" | 玫瑰红 |
| "用黄色""明亮""活力" | 琥珀黄 |
| "用灰色""简约""商务" | 石墨灰 |
| "换个色系""换个颜色" | 列出6种色系让用户选 |

没指定色系时默认「赤铜橙」。

### 3. 调用排版引擎

排版引擎位于 `engine/feishu_to_copy_page.py`（相对于仓库根目录）。

```bash
# 在仓库根目录下运行
python3 engine/feishu_to_copy_page.py \
  --url "<飞书链接>" \
  --wechat \
  --output-dir "<输出目录>"
```

脚本执行成功后会输出 JSON，包含：
- `title`：文章标题
- `output_dir`：输出目录路径
- `copy`：copy.html 路径
- `block_count`：排版块数

### 4. 应用色系（非默认色系时）

如果用户指定了非默认色系，对生成的 HTML 文件做颜色替换：

```python
# 默认赤铜橙 → 目标色系 的颜色映射
replacements = {
    "#B8623C": target["accent"],
    "#fff8f1": target["warmBg"],
    "#f5e0c5": target["warmPill"],
    "#ead8c2": target["warmBorder"],
    "#d6ab81": target["warmLine"],
    "#fff5e9": target["warmPanel"],
}
```

对 `copy.html`、`source.html`、`preview.html`、`editor.html` 都做相同替换。

### 5. 打开编辑器

复制编辑器到输出目录并打开：

```bash
cp engine/editor.html "<输出目录>/editor.html"
open "<输出目录>/editor.html"
```

或启动一站式服务：

```bash
python3 server/layout_server.py
# 浏览器打开 http://localhost:8790
```

### 6. 向用户汇报

告诉用户：
- 文章标题
- 排版块数
- 使用的色系
- 编辑器地址
- 如何复制到微信（点击"复制到微信"按钮，去公众号后台粘贴）

## 注意事项

- 排版引擎需要 lark-cli 已登录且有文档读取权限
- 飞书链接必须是当前用户有权限访问的文档
- 图片会自动下载并内联为 base64，copy.html 脱离服务器也能显示
- 编辑器依赖同目录下的 copy.html 加载排版内容
- `--wechat` 参数会做微信兼容净化（section→span, div→span, 去 box-shadow 等）
