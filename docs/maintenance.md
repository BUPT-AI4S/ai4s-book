# 维护与发布

网站内容位于 `index.html`、`read.html`、`pdf.html`、`static/` 和 `data/textbook/`。公开网站使用 GitHub Pages 项目路径 `/ai4s-book/`，没有购买或绑定独立域名。

## 查看与修改网站

网站检查与预览：

```sh
python tools/build_textbook.py --check
python -m unittest discover -s tests -p 'test_*.py'
python tools/stage_site.py
python tools/preview.py --port 8084
```

打开 `http://127.0.0.1:8084/ai4s-book/`，预览服务提供 `_site/` 中的网站文件。

## 更新教材

先确定本次发布的章节与版本，再安装生成工具并导入相应的教材工程：

```sh
python -m pip install -r tools/textbook-requirements.txt
python tools/build_textbook.py --sync-from /path/to/authoring-checkout
```

`.textbook-source/` 是忽略提交的本地快照，保留所选版本以便重建。生成网页不需要 LaTeX 编译器；含 PDF 原始配图时需要可在 PATH 中调用的 Poppler `pdftoppm`。这些配图在生成时转成 WebP，源 PDF 不进入公开目录。

生成器从快照中的 `main.tex` 确定章节与顺序，支持嵌套 input、学习目标、小贴士、图表、脚注、数学公式及交叉引用。遇到新宏时先补充网页映射再重新生成。阅读版省略工程说明，保留科研内容及其适用条件。

网站提供网页正文和 PDF 原版页面预览，网页参考文献按章编号，原版预览保留 LaTeX 的全书文献编号。预览使用 1600 像素宽的无损 WebP 页面图片，连续滚动并按需加载页面，支持翻页、跳页与缩放。PDF 文件发布开关保持关闭，暂存过程排除 PDF 文件。

更新原版预览时，使用与网页同版本的本地章节 PDF 和编译清单：

```sh
python tools/build_previews.py --pdf-dir /path/to/chapter-pdfs --source-catalog /path/to/compiled-catalog.json --renderer /path/to/pdftoppm
```

编译清单包含 `sourceHash` 和每章 PDF 的 `pdfSha256`。生成器核对版本与文件校验和，再转换全部页面；相同页面去重保存。网页正文重建时保留同版本的预览资源，来源变化后必须重新生成预览。

发布前必须通过 `--check`，验证章节、配图、校验和及网页发布范围。来源摘要、内容校验和记录在 `data/textbook/catalog.json`。请勿直接修改生成文件。

## 提交前检查

- 正文结构、64 幅图和 13 张表格的数量及单元格完整；新章节发布时同步修改测试的预期数量。
- 交叉引用、图解提示、脚注和文献可跳转。
- 测试手机、桌面、深浅主题、中英导航、预览翻页与缩放、课程链接与授权邮箱，确认发布目录中没有 PDF。
- 同步 README、English README、CHANGELOG 和引用信息。
- 检查待提交文件与发布目录。

教材更新按“同步、生成、校验、提交”执行。GitHub Actions 校验已生成的内容并发布到 Pages。

当前同步源为私有仓库 `0c5b628`。源文件已按实际章次重命名，生成器保留最初的六个公开章节 ID，同时保留旧小节、图表锚点别名。按章统一遗留标签前缀，单列嵌套排版表格转为单元格内换行，避免重复表号。排印用的本地 OTF/TTF 字体进入被忽略的源码快照，公开网站不包含字体、源文件或 PDF。完整编译使用 Tectonic 或 XeLaTeX，并需要缓存或下载 `fontawesome5` 等原工程依赖。
