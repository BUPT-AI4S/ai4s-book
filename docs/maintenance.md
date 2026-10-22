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

`.textbook-source/` 是忽略提交的本地快照，保留所选版本以便重建。生成网页不需要 LaTeX 编译器。

生成器从快照中的 `main.tex` 确定章节与顺序，支持嵌套 input、学习目标、小贴士、图表、脚注、数学公式及交叉引用。遇到新宏时先补充网页映射再重新生成。阅读版省略工程说明，保留科研内容及其适用条件。

网站只发布网页正文，参考文献按章编号。PDF 发布开关保持关闭，目录和章节数据不提供 PDF 地址；暂存过程也排除 PDF 文件。旧 PDF 阅读链接跳转至章节网页。

发布前必须通过 `--check`，验证章节、配图、校验和及网页发布范围。来源摘要、内容校验和记录在 `data/textbook/catalog.json`。请勿直接修改生成文件。

## 提交前检查

- 正文结构、32 幅图和两张表格的数量及单元格完整；新章节发布时同步修改测试的预期数量。
- 交叉引用、图解提示、脚注和文献可跳转。
- 测试手机、桌面、深浅主题、中英导航、课程链接与授权邮箱，确认发布目录中没有 PDF。
- 同步 README、English README、CHANGELOG 和引用信息。
- 检查待提交文件与发布目录。

教材更新按“同步、生成、校验、提交”执行。GitHub Actions 校验已生成的内容并发布到 Pages。
