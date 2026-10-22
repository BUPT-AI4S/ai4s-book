# 参与与反馈

欢迎参与《科学智能原理与实践》的内容、网站与文档改进。

## 教材纠错

通过 Issues 提供：章节与小节、网页锚点、问题描述、修改建议以及可核对的来源。区分原文表述错误、引用错误和对研究结论的不同理解；涉及数值与论断时请尽量链接原论文或官方资料。

维护团队会审阅反馈并更新教材。`data/textbook/` 下的文件由工具生成，正文修改请通过 Issues 提交。

## 网站与文档

可通过 Pull Request 改进 HTML、CSS、JavaScript、README 或工具。请说明使用场景、修改后的行为和验证方式，保持项目路径兼容、键盘可用和手机阅读体验，并遵守所用材料的许可要求。

## 本地检查

```sh
python tools/build_textbook.py --check
python -m unittest discover -s tests -p 'test_*.py'
python tools/stage_site.py
python tools/preview.py --port 8084
```

更新教材正文的维护流程见 [docs/maintenance.md](docs/maintenance.md)。

贡献者署名按实际贡献和本人意愿记录。
