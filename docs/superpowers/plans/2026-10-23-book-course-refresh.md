# Book and Course Refresh Implementation Plan

> **For agentic workers:** Use the executing-plans workflow and independent agents for the separate preview and course surfaces. Keep one final review across the release.

**Goal:** Publish the latest six-chapter textbook, continuous original-layout previews, release timestamps, Reasoning Lab and Star History information, and direct course-to-book navigation.

**Architecture:** Keep the private authoring repository as source. Generate HTML and approved local PDF snapshots, publish only HTML and page images. Preserve unrelated course changes by releasing course integration from a clean worktree and applying matching edits to the existing workspace.

**Tech Stack:** Python, Pandoc, Tectonic, pypdf, Pillow, native HTML/CSS/JavaScript, GitHub Pages.

**Spec:** The user's six requested changes and existing authorization, download and presentation requirements.

## Global Constraints

- No PDF file download or public PDF assets; original-layout preview remains available.
- Use actual latest authoring order and titles. No draft or internal import notices in reader-facing copy.
- Preserve authorization email ehaihong@bupt.edu.cn, AI FOR SCIENCE branding and course button.
- Display first successful launch and latest release timestamps in Asia/Shanghai.
- Do not include unrelated uncommitted course work in this release.

## Review Focus

- All six chapters, figures, tables and source versions agree across HTML and previews.
- Scrolling reaches later pages; paging, jumps, zoom and mobile layout remain usable.
- No PDF files or source materials enter published assets.
- Course cover and navigation work in both languages and at small screen widths.
- Dates and Star History refer to actual project information, and the supplied QR image remains intact.

## Tasks

- [x] Pull authoring repository; regenerate current chapters and local compilation snapshots, then all preview pages.
- [x] Fix preview interaction using continuous scrolling, lazy page loading, page navigation and zoom; reproduce and test the former single-page behavior.
- [x] Add release timestamps, six-chapter book presentation, README Star History and Reasoning Lab QR image.
- [x] Add course homepage cover and direct book navigation; replace old local textbook pages with redirects in an isolated release checkout and the working copy.
- [ ] Validate builds, browsers, QR preservation and cross-site links; obtain final code review, publish both sites and check live behavior.

## Verification

- Latest authoring source: c5c0a804ad2d42de8fdec868157fa530e2504089; full local compilation 195 pages; six chapter previews 257 pages including references.
- 18 Python tests passed; six-chapter browser checks passed, including 16 homepage language/theme/width combinations and continuous scroll, jump, zoom, retry and publication boundaries.
- Course site build, 33 JavaScript tests and 28 responsive language/theme combinations passed; unrelated original workspace files preserved.
- Independent review corrected a duplicated figure wrapper; all six chapters now have unique IDs and 66 figures/12 tables matching the source.
