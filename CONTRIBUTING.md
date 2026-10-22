# 参与与反馈

感谢你帮助完善《科学智能原理与实践》。当前公开三章协作编写稿，LaTeX 编写源码保持私有。

## 书稿纠错

通过 Issues 提供：章节与小节、网页锚点或PDF版本/页码、问题描述、修改建议以及可核对的来源。区分原文表述错误、引用错误和对研究结论的不同理解；涉及数值与论断时请尽量链接原论文或官方资料。

编写团队会审阅反馈，并在书稿源工程中处理，再生成后续公开版本。请不要直接修改 `data/textbook/` 下的生成文件，以免下次同步时覆盖。

## 网站与文档

可通过 Pull Request 改进 HTML、CSS、JavaScript、README 或公开工具。说明触发场景、修改后的行为和验证方式；保持项目路径兼容、键盘可用和手机阅读体验。未经授权，不加入完整 LaTeX 书稿、内部资料、凭据或第三方受限材料。

## 本地检查

```sh
python tools/build_textbook.py --check
python -m unittest discover -s tests -p 'test_*.py'
python tools/stage_site.py
python tools/preview.py --port 8084
```

只查看和改进网站不需要私有书稿或 LaTeX 编译器。更新教材正文的维护流程见 [docs/maintenance.md](docs/maintenance.md)。

贡献者署名按实际贡献和本人意愿记录，不自动将所有反馈者列为书籍作者。
