# TrueSight — Graduation-project dissertation drafts

This directory contains the dissertation as a set of section-by-section Markdown files matching the university's template. Concatenate them in order to produce the full document.

## Section index

| File | Section |
| --- | --- |
| `01-introduction.md` | 1. Introduction |
| `02-project-overview.md` | 2. Project Overview and Objectives |
| `03-literature-review.md` | 3. Literature Review |
| `04-requirements.md` | 4. Requirements Phase |
| `05-analysis.md` | 5. Analysis Phase (use cases + activity diagrams) |
| `06-design.md` | 6. Design Phase (context + ER diagram + schema) |
| `07-implementation.md` | 7. Implementation Phase |
| `08-references.md` | 8. References |
| `appendix-a-code.md` | Appendix A: Code |
| `appendix-b-screenshots.md` | Appendix B: Screenshots |
| `appendix-c-cd.md` | Appendix C: CD of the project |

## What you still need to do

Two things, both straightforward:

1. **Export the five Mermaid diagrams to PNG.** Open https://mermaid.live, paste each fenced ```mermaid``` block from `05-analysis.md` (three diagrams) and `06-design.md` (two diagrams) into the left pane, click **Actions → PNG**, and download. Insert each PNG into your Word/PDF document at the position the section refers to it.
2. **Capture the seven screenshots.** Appendix B lists them with suggested filenames. Start the application (`.\start.bat`), reach each state, capture, save under `docs/dissertation/screenshots/`, and replace the `[INSERT SCREENSHOT: ...]` placeholders.

## How to combine the files

```powershell
cd docs\dissertation
Get-Content 01-introduction.md, 02-project-overview.md, 03-literature-review.md, 04-requirements.md, 05-analysis.md, 06-design.md, 07-implementation.md, 08-references.md, appendix-a-code.md, appendix-b-screenshots.md, appendix-c-cd.md | Out-File -FilePath FULL-DISSERTATION.md -Encoding utf8
```

Feed `FULL-DISSERTATION.md` to a Word-conversion AI if you want a `.docx` file produced automatically. Insert the diagram PNGs and screenshots in their referenced positions.
