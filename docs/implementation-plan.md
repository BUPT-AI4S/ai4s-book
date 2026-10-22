# Public book implementation plan

Goal: publish the agreed three-chapter book as a public GitHub project, bilingual project README and standalone Pages website, while keeping the LaTeX manuscript private.

Spec: `docs/design.md`. Stack: Python, Pandoc, Tectonic, pypdf, native HTML/CSS/JS, local PDF.js, GitHub Pages.

1. Adapt the existing renderer for three ungrouped chapters, custom figure tips, actual tables, cross-references, and a full-book PDF. Tests must verify real chapter order, 32 images, 2 tables, linked references, PDF checksums, and publication boundaries. Compile the original complete book once and split at verified chapter bookmarks.
2. Build an editorial book homepage, three-chapter library and reader with HTML/PDF modes, downloads, theme/language controls, project star links and course links. Keep all navigation compatible with a project subpath.
3. Write Chinese and English READMEs, honest badges, chapter/resource navigation, contribution/feedback instructions, rights statement, citation metadata, changelog and maintainer build instructions. Do not disclose the private manuscript.
4. Validate outputs, unit tests and browser behavior, render PDF samples, stage only public artifacts. Review the final files and privacy boundary.
5. Check/create the authorized BUPT-AI4S/ai4s-book repository, push only reviewed files, configure GitHub Pages and verify its deployment. If account permissions block the remote steps, retain a complete validated local project and report the exact permission limitation.
