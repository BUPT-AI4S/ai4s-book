# Lecture Poster and Book Refresh Implementation Plan

> **For agentic workers:** Use executing-plans for the book and the independent course poster task; review both before publication.

**Goal:** Show the supplied lecture poster prominently on the course homepage and publish the latest six-chapter textbook to the public book repository and website.

**Architecture:** Course adds a themed announcement with an original-image dialog. The private authoring checkout remains the source; the public generator keeps the established reader URLs while accepting renamed chapter source files. Render PDF figure assets as web images and regenerate verified local manuscript PDFs and linked page previews.

**Tech Stack:** Static HTML/CSS/JavaScript; Python, Pandoc, Tectonic, Poppler, Pillow, pypdf; GitHub Pages.

**Spec:** User request of 2026-10-24, supplied Liu Guangyi poster, existing book preview and publication requirements.

## Constraints
- Keep supplied poster intact; show topic, speaker, 2026-10-27 16:35–18:10 Beijing time and location 3-239.
- Preserve existing homepage news and book links, themes, languages and mobile navigation.
- Publish six approved chapters only. Keep LaTeX source, local PDFs and imported authoring materials private.
- Preserve PDF-layout previews, citation jumps, return links and existing chapter URLs; no PDF downloads.
- Keep source snapshot immutable and source hash consistent across HTML and previews.
- Retain remote reading statistics and Star History updates.

## Tasks
- [x] Fetch repositories; fast-forward clean private and public checkouts and inspect source changes.
- [x] Add the course poster card and accessible original-image dialog; verify responsive and keyboard behavior.
- [x] Test and support renamed chapter files without changing public IDs, local font assets and PDF figure conversion.
- [x] Generate six current HTML chapters, fresh manuscript compilation, split PDFs and all preview pages with links.
- [x] Update contributor/presentation metadata, counts, bilingual README, changelog and actual release timestamp.
- [x] Check generated source/version/asset boundaries, all tests, representative page images, continuous preview and citations.
- [ ] Independent review, publish both repositories, verify deployment and live content.

## Validation

- Source commit: 0c5b628ce3b3f0d72fc7f3f24a4a3a49ce6abe73; six chapters, 64 figures, 13 tables; 261 original-layout preview pages.
- Book: 29 Python tests; six-chapter browser suite, 16 homepage language/theme/width cases, citation jumps and returns; all private PDF chapter text checked without unresolved references; no PDFs in public assets.
- Course: 39 Node and 77 Python tests; 20 poster responsive/language/theme cases plus original bytes, native dialog, keyboard and focus checks.
- Independent review checked stable chapter URLs, references, media boundaries and poster behavior. Added legacy figure/section anchor compatibility and documented the PDF-figure renderer dependency after review. Final supplementary checks confirmed alias scrolling, 5.1–5.3 evaluation tables, contributor list and vector figure loading.
