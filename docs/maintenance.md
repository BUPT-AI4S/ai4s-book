# 维护与发布

网站内容位于 `index.html`、`read.html`、`pdf.html`、`static/` 和 `data/textbook/`。公开网站使用 GitHub Pages 项目路径 `/ai4s-book/`，没有购买或绑定独立域名。

## 查看与修改网站

只查看公开内容无需访问私有书稿，也不需要 LaTeX 编译器：

```sh
python tools/build_textbook.py --check
python -m unittest discover -s tests -p 'test_*.py'
python tools/stage_site.py
python tools/preview.py --port 8084
```

打开 `http://127.0.0.1:8084/ai4s-book/`。预览仅提供暂存后的公共文件，私有快照、工具和内部资料不会随网页提供。

## 更新教材（编写团队）

先把已确认的 Overleaf 修改同步到私有 Git 仓库并更新本地书稿。随后安装生成工具，显式导入编译所需的书稿：

```sh
python -m pip install -r tools/textbook-requirements.txt
python tools/build_textbook.py --sync-from /path/to/private-manuscript --pdf-engine /path/to/tectonic
```

也可使用已安装的 `latexmk` 和 XeLaTeX。Tectonic 首次使用需要联网获取字体和宏包。`.textbook-source/` 是忽略提交的本地快照，不要将其上传；不要复制私有仓库的 `.git`、`sources/`、历史示例和协作说明到公开项目。

生成器从当前 `main.tex` 确定章节与顺序，支持嵌套 input、学习目标、图解小贴士、图表、脚注、数学公式及章节/图/表交叉引用。无法转换的原始 TeX 会使构建停止，避免无声丢文；遇到新宏时先补充网页映射再重新生成。

完整书稿按 LaTeX 原版编译，分章 PDF 由书签确定边界并附全书共享参考文献。PDF 的页码与文献编号保留书稿值；网页文献按章独立编号。

仅重建网页可用 `--html-only`，只复用同一份源码、且通过校验的现有 PDF；正式发布前必须通过 `--check`，确保完整和分章 PDF 全部存在。源码摘要、内容/PDF 校验和记录在 `data/textbook/catalog.json`。请勿直接修改生成文件。

## 提交前检查

- 正文与原稿结构对应，32 幅图和两张表格的数量及单元格完整；新章节更新时同步修改测试的预期数量。
- 交叉引用、图解提示、脚注和文献可跳转；PDF 中的命名目标有效。
- 测试手机、桌面、深浅主题、中英导航、网页/PDF切换及下载。
- 更新 README、English README、CHANGELOG 和引用信息；不填虚构排名、推荐语、出版或授权信息。
- `git status` 和待提交文件中没有 `.textbook-source/`、内部原稿、凭据或日志。

GitHub Actions 只校验已生成的公开内容并暂存发布，不拉取私有仓库；教材更新需要编写团队主动同步、生成和提交。Pages 发布来源设为 GitHub Actions。
