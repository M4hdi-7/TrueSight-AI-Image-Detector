# TrueSight — Graduation-project dissertation drafts

This directory contains section-by-section markdown drafts of the dissertation. Each file maps onto one section of the university's required template. Combine them in numeric order to produce the full document.

## How to use this directory

1. Read each file in order (`01-` through `08-`, then the appendices).
2. Sections 3 and 8 are skeletons — you'll need to fill in the comparative-research notes (literature review) and the actual academic references yourself.
3. Section 7 includes a screenshot subsection — capture the screenshots listed in `appendix-b-screenshots.md` and embed them in your final document.
4. Sections 5 and 6 contain Mermaid diagram code. To get image files for your Word / PDF dissertation:
   - Open https://mermaid.live in your browser.
   - For each Mermaid code block, copy the contents and paste into the left pane.
   - Click **Actions → PNG** (or SVG) and download.
   - Insert the resulting image into your dissertation document at the same position.
5. Combine all files into your university template's format (Word / LaTeX / PDF).

## Section index

| File | Section |
| --- | --- |
| `01-introduction.md` | 1. Introduction |
| `02-project-overview.md` | 2. Project Overview and Objectives |
| `03-literature-review.md` | 3. Literature Review (skeleton — needs user research) |
| `04-requirements.md` | 4. Requirements Phase (functional + non-functional) |
| `05-analysis.md` | 5. Analysis Phase (use cases + activity diagrams) |
| `06-design.md` | 6. Design Phase (context + ER diagram + schema) |
| `07-implementation.md` | 7. Implementation Phase (tools, scenarios, sample reports) |
| `08-references.md` | 8. References (template — needs real entries) |
| `appendix-a-code.md` | Appendix A: Code |
| `appendix-b-screenshots.md` | Appendix B: Screenshots (capture checklist) |
| `appendix-c-cd.md` | Appendix C: CD of the project |

## What still needs your input

- **Literature review (§3)**: visit each suggested comparator system, gather notes, fill in the table.
- **References (§8)**: replace the placeholder citations with real ones from work you have actually read.
- **Screenshots (Appendix B)**: capture seven screenshots listed in the appendix.
- **Convert to final format**: when ready, paste everything into your university's Word template.

## Workflow tip

Once you've filled in §3 and §8 and captured screenshots, concatenate all the markdown files in order:

```powershell
Get-Content 01-introduction.md, 02-project-overview.md, 03-literature-review.md, 04-requirements.md, 05-analysis.md, 06-design.md, 07-implementation.md, 08-references.md, appendix-a-code.md, appendix-b-screenshots.md, appendix-c-cd.md | Out-File -FilePath FULL-DISSERTATION.md -Encoding utf8
```

You can then feed `FULL-DISSERTATION.md` to a fresh Claude / ChatGPT session for a final polish pass — checking for tone consistency, repeated phrasing, and small inaccuracies.
