# Public book implementation plan

Goal: provide a three-chapter online textbook, bilingual project README, companion course links and teaching authorization contact through a standalone GitHub Pages website.

Spec: `docs/design.md`. Stack: Python, Pandoc, native HTML/CSS/JS and GitHub Pages.

1. Generate three chapters with HTML/MathML, figure tips, tables and cross-references. Verify chapter order, 32 images, two tables and reference links.
2. Provide chapter navigation, theme/language controls, GitHub Star and course links. Keep navigation compatible with the project subpath.
3. Maintain Chinese and English READMEs, citation metadata, rights information and teaching authorization contact at ehaihong@bupt.edu.cn.
4. Provide original-layout previews through page images, page navigation and zoom. Validate image checksums and source versions, exclude PDF files and download links, and redirect legacy reader URLs to preview mode.
5. Push reviewed files and verify GitHub Pages deployment.
