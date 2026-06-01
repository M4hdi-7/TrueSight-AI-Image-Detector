# TrueSight — Viva Preparation (One-Document Bundle)

A single self-contained document covering everything needed to defend the TrueSight project in a supervisor / examiner discussion. Two halves:

- **Part 1 — The Project.** What it is, who it's for, what problem it solves, why each major decision was made, how it compares to existing tools, what it measures up to. Answers the "general" questions ("who is it for", "what did you do", "why this and why that").
- **Part 2 — The Codebase.** File-by-file, function-by-function walkthrough so any "why is this line here?" / "what happens if X?" question has an answer.

---

# Part 1 — The Project

## 1. One-paragraph elevator pitch

**TrueSight** is a local-network web application that classifies an uploaded image as **AI-generated**, **deepfake**, or **authentic**, and produces a forensic report explaining the verdict in plain language. It orchestrates two commercial detection APIs — **Sightengine** (primary: AI-generation + deepfake probability) and **Hive AI** (secondary: per-generator attribution, called only when an image is already judged AI). On top of the API verdicts, it layers **on-device forensic signals** (EXIF metadata, JPEG quantization, dimension checks) and persists a local SQLite history. The system runs on a user's PC and is reachable from any device on the same Wi-Fi — typically a phone for image capture and a PC for analysis.

It does **not** train its own classifier. The project's value-add is the *system around* the detection — cascade logic, local signals, validation, persistence, presentation, and evaluation — not the detection itself.

## 2. The problem (why this project exists)

Generative-image models — Midjourney, DALL·E, Stable Diffusion, Flux, Gemini Imagen, GPT-Image — have crossed the threshold beyond which the average viewer can no longer reliably distinguish their output from authentic photographs. Two reference incidents to cite in the viva:

- **March 2023** — an AI-generated image of Pope Francis in a Balenciaga puffer jacket spread across social media as if it were real, deceiving millions.
- **Two months earlier** — fabricated images of a former US president being arrested went viral the same way.

The consequences span sectors: journalism cannot trust photographs without verification; courts cannot trust photographic exhibits without provenance; and an ordinary person scrolling a feed has no easy way to ask the basic question — *is this real?*

A small market of detection tools has emerged in response, but each is constrained in similar ways. They are **cloud-only** (the user must upload their image to a third-party server), **account-gated and rate-limited**, and they return **opaque verdicts** — "87% AI" with no explanation of why, and no surfacing of the auxiliary forensic evidence (metadata, compression history, provenance signatures) that a sceptical user could weigh independently.

TrueSight is a graduation-project response to those three constraints.

## 3. Who it's for (target users / use cases)

Three concrete scenarios from the dissertation:

1. **Journalist verifying a viral image.** A reporter receives a forwarded image of a public figure in an unusual situation. Before publication, she opens TrueSight on the newsroom's local network from her phone, drops the image in, and waits ~10 s. Verdict returns "AI Generated" at 99 % with Midjourney named as the most likely generator. She captures the verdict screen for the editorial trail and declines to publish. **The image never leaves the LAN.**
2. **Social-media moderator triaging user uploads.** A moderator works through a queue of reported images. Each scan completes in under 30 s. AI-positive verdicts route to a dedicated review queue with attribution preserved; "Real Photo" verdicts continue down the normal pipeline. The local SQLite history records every triage decision for later audit.
3. **Researcher labelling a dataset.** A researcher building a dataset of AI-generated images runs `evaluate.py` to label a directory in bulk. Ground-truth labels go into `Test/README.md` where origin is known; the harness produces a confusion matrix plus a Markdown report listing every misclassification — the "interesting failures" become the focus of dataset review.

Common thread: **a single user, on a trusted local network, who wants a transparent forensic verdict — not a single opaque number from a third-party server.**

## 4. What was built (objectives, in plain language)

From the formal objectives list:

1. Classify images as AI-generated / deepfake / authentic with a numeric confidence.
2. Identify the most likely generator engine (Midjourney, DALL·E, Flux, Gemini, GPT-Image, Stable Diffusion, …) when AI is detected.
3. Detect face-swap deepfake patterns.
4. Compute zero-cost on-device forensic signals (EXIF, AI-software tag detection, JPEG compression heuristic).
5. Produce a **plain-language forensic report**, not an opaque score.
6. Operate over LAN, reachable from any phone or laptop, no account needed.
7. Persist local scan history in SQLite (last 50 visible).
8. Provide an **automated evaluation framework** producing a confusion matrix + standard classification metrics against a labelled test set.

**Out of scope** (be ready to defend this list as a deliberate boundary):

- Training a proprietary detection model
- Authentication / multi-user isolation
- HTTPS, rate limiting, production-grade web serving
- Adversarial robustness
- Video analysis
- C2PA / Content Credentials reading (future work — see § 11.3)

## 5. Why each big decision (the "why this, why that" answers)

This is the section to read carefully before viva. Each row pairs a question your supervisor might ask with the defensible answer.

| Question | Answer |
|---|---|
| **Why didn't you train your own model?** | Training a competitive detector requires labelled samples spanning *current* generators, which evolve faster than any retraining cycle a student could maintain. The earlier v1.0 prototype tried a 5-model PyTorch ensemble and was outdated within months. The pivot to API-driven detection trades novelty for currency — Sightengine and Hive stay updated; my system gets that updating for free. |
| **Why two cloud APIs instead of one?** | Sightengine gives the best primary signal — AI-generation + deepfake in a single call. But Sightengine's per-generator attribution is locked behind an enterprise tier. Hive's V3 API exposes named heads for 12+ specific engines (`midjourney`, `gpt-4o`, `flux`, …) — exactly the missing piece. Pairing them gives both *what* the verdict is (Sightengine) and *which model* produced it (Hive). |
| **Why a cascade (Hive only on AI-positives) rather than always calling both?** | Cost-awareness. Hive's per-call cost + 5–30 s latency is wasted on real photos — there's no generator to attribute. The cascade saves an estimated **50 % of Hive quota** on a real-world traffic mix and removes the latency overhead from the common case. The threshold is `ai_score >= 50 %`, set once in [model.py:26](../backend/ai_model/model.py#L26). |
| **Why Flask and not FastAPI / Django?** | Smallest viable Python web framework. No learning curve for the supervisor / external reviewer, no build step. The whole backend fits in one file you can read in five minutes. FastAPI's async benefits don't help — the bottleneck is the synchronous external API, not the framework. |
| **Why vanilla JS, no React/Vue?** | Same reasoning. The frontend is < 700 lines of script; React would add a 100 KB runtime + a build step + a learning surface in exchange for code organisation we don't yet need. |
| **Why SQLite, not Postgres / Mongo?** | Zero-config, file-based, no separate process to manage. The data set is bounded at ~50 visible rows. Postgres would be deployment overhead with zero functional benefit. |
| **Why no authentication?** | Out of scope for a LAN-only graduation prototype (objective 6: "no account required"). Adding auth without HTTPS would be cargo-cult security. The "Production Readiness" section in `CLAUDE.md` lists every layer that *would* be added before any non-LAN deployment. |
| **Why two label functions (server-side + client-side) with different cut-offs?** | The backend label is *durable* (stored in `history.db`, used by `evaluate.py`); the frontend label is *transient* (just for colour + icon in the current view). Decoupling them means I can re-tune the user-facing colour bands without shifting the evaluation metrics. |
| **Why emoji prefixes (✅ ⚠️ ❌ 🤖) in the reasons text?** | They double as a machine-readable tag (`classifySignal()` reads the prefix to pick a colour class) **and** a human-readable cue. Two birds, one byte. |
| **Why one SQLite table instead of normalised schema?** | No shared verdicts, no shared reasons (each scan produces a bespoke list). No concurrent writers — the standard motivation for normalisation doesn't apply. The single read pattern is "list last 50" or "fetch one row's full record". A single table is the simplest model that satisfies every requirement and exposes the smallest surface area for bugs. |
| **Why store EXIF and JPEG quantization locally instead of using the API for that?** | They're zero-cost local signals. The APIs charge per call; EXIF reading via Pillow is free, instant, and offline. And some signals are *dispositive* without any classifier (e.g. an EXIF `Software` tag literally reading "Midjourney" is conclusive). |
| **Why an evaluation harness with a caching layer?** | Sightengine + Hive cost real money. Caching successful results across runs lets me iterate on the report format, reasons logic, and ground-truth labels in `Test/README.md` without re-spending budget. Failed runs are intentionally *not* cached so transient outages get retried. |
| **Why are the thresholds all in one block at the top of `model.py`?** | Auditability. The five-tier label thresholds, the cascade gate, the deepfake bands, the JPEG compression cutoff, the AI-software substring list — all decisions about *where the line sits* are in one place. Calibration changes don't require chasing the codebase. |
| **Why is the cascade gate `>= 50 %` specifically?** | Sightengine's score distribution is strongly bimodal (see § 8). Almost every output is either 99.0 % or 0.1 %; only one image in 59 fell in the middle. So the threshold's exact value doesn't materially affect outcomes — 50 % is chosen as the natural symmetric cut-off, and it leaves room for finer calibration if the distribution ever flattens. |
| **Why store images on disk instead of inside SQLite as BLOBs?** | Bloats the database; serving file bytes through a SQL layer is slower than `send_from_directory`; backup and inspection get harder. The implicit one-to-one mapping between a `history` row and `uploads/<filename>` is enforced by application logic — written together, deleted together. |
| **Why UUID filenames instead of keeping the user's filename?** | Three reasons: (1) prevents path traversal (`secure_filename()` + UUID rename means no user bytes end up in a path); (2) prevents collisions when two users upload `IMG_1234.jpg`; (3) decouples on-disk identity from anything the user controls, so log lines and DB rows can't be confused with user-supplied data. |
| **Why a single 12 MB upload cap?** | Matches Sightengine's hard upload limit exactly. Failing locally for anything bigger saves a round-trip and a wasted API call. |
| **Why the 64 MP / 8 px dimension gates?** | Same reasoning — mirrors Sightengine's published limits. The wide gap between min and max accommodates everything from a phone thumbnail to a high-res DSLR file. |
| **Why no automated tests?** | Deliberate scope decision. This is a graduation prototype, not a production service. The evaluation harness (`evaluate.py`) is the closest thing to a test suite — it runs the whole pipeline against ground truth and reports metrics. Unit tests on `model.py`'s reason-building would be cheap to add but were not required for the dissertation contribution. |

## 6. How TrueSight compares to existing tools

The literature review compared against eight alternatives. Summary table (positive class = "image-is-AI"):

| System | Method | Deepfake | Engine attribution | Deployment | Privacy | Reasoning shown | Account needed |
|---|---|---|---|---|---|---|---|
| **Hive AI Moderation** | CNN classifier (multi-head) | Yes | Yes (12+ engines) | Cloud | Uploaded to Hive | Single score per head | Yes |
| **Sightengine** | Classifier API | Yes (separate `deepfake` model) | Plan-gated (enterprise) | Cloud | Uploaded to Sightengine | Single score per model | Yes |
| **Optic AI or Not** | Classifier | No | No | Cloud | Uploaded | Binary | Yes |
| **Illuminarty** | Region-localised classifier | Indirect via region map | Limited | Cloud | Uploaded | Heat-map | Yes |
| **Microsoft "About this image"** | Reverse search + C2PA | No (provenance-based) | Indirect via origin | Cloud (Bing) | Fingerprinted, not stored | Provenance trail | Optional |
| **OpenAI Image Classifier** | (discontinued July 2023) | — | — | — | — | — | — |
| **C2PA / Content Credentials** | Cryptographic signing at source | N/A | N/A | Embedded in file | Local | Provenance manifest | No |
| **TrueSight (this work)** | **API cascade + local forensic signals** | **Yes (Sightengine)** | **Yes (Hive cascade)** | **Local (LAN)** | **High — image only leaves device for the API call** | **Bullet-point reasons list** | **No (LAN-only)** |

The position you defend: **no existing tool combines all of (a) local deployment, (b) on-device forensic signals, (c) multi-provider cascade for cost-aware attribution, (d) persistent local history, (e) transparent reasoning rather than a single number.** Every cloud competitor sacrifices privacy by requiring upload; every provenance-only tool fails on images that lack C2PA credentials (which is almost everything in the wild). TrueSight occupies the unfilled niche: a *local, multi-provider, forensic-reasoning* detector.

It does **not** claim a novel classification algorithm — the classifiers are Sightengine's and Hive's — but it integrates them in a configuration that no comparator offers.

One sentence to memorise: **"I didn't build a better classifier. I built a better system around the existing best classifiers, with privacy and transparency the existing tools don't give you."**

## 7. Requirements — what we promised and what we delivered

10 functional + 10 non-functional, all satisfied. The ones worth quoting verbatim if asked:

**Functional highlights**

- **FR-2 — five-layer validation stack** before any external call: extension whitelist → `secure_filename()` → UUID rename → PIL magic-byte check → dimension cap. Reject early, reject locally, never spend API quota on invalid input.
- **FR-4 — the cascade** is enshrined as a formal requirement: "When the AI-generation probability is at least 50 percent, the system shall additionally call Hive AI to extract per-engine generator attribution. When the probability is below this threshold the system shall not contact Hive."
- **FR-10 — automated evaluation harness** with ground-truth from `Test/README.md`, resumable across partial runs.

**Non-functional highlights**

- **NFR-4 — graceful degradation**: Hive failure → verdict still returned without attribution; Sightengine failure → user-readable Error verdict (no crash).
- **NFR-5 — full keyboard accessibility**: ARIA roles, focus traps, `prefers-reduced-motion`, `:focus-visible` styling, all modal dialogs operable from the keyboard alone.
- **NFR-7 — threshold centralisation**: all five cut-offs live in one named-constant block at the top of `model.py`.
- **NFR-9 — no ML libraries**: backend depends on 5 pinned packages; no `torch`, `transformers`, `onnxruntime`, `numpy`, or `scikit-learn`. Image handling is Pillow-only.

## 8. Evaluation — the numbers (have these memorised)

The system was evaluated against a **manually-curated 59-image test set**:

- **40 ground-truth AI-generated** samples spanning 12 named engines: Midjourney, Flux, DALL·E, GPT-Image v1.5 and v2, Gemini 3, Stable Diffusion, SDXL, Z-Image, Kling, Krea, Ideogram, Grok — plus several viral-hoax AI images.
- **19 ground-truth real photographs** drawn from Unsplash, the New York Times CMS, NASA Hubble's public archive, Wikipedia portrait files, Flickr, and iStockphoto.

**Confusion matrix (AI = positive class):**

|                 | Predicted Real | Predicted AI |
|----------------|---------------|--------------|
| **True Real**  | 19 (TN)       | 0  (FP)      |
| **True AI**    | 1  (FN)       | 39 (TP)      |

**Metrics:**

| Metric    | Value     | What it means |
|-----------|-----------|---------------|
| Accuracy  | **98.3 %** | Overall correct fraction. |
| Precision | **100 %**  | When TrueSight says AI, it's right every time on this set. (Zero false positives.) |
| Recall    | **97.5 %** | TrueSight catches 39 of the 40 AI images. |
| F1        | **98.7 %** | The headline metric — harmonic mean of precision and recall, robust to the moderate class imbalance (68 % AI / 32 % real). |

**Why F1 and not just accuracy?** A naive detector that always says "AI" would score **68 % accuracy** on this set just by guessing. F1 exposes that failure mode by penalising both classes asymmetrically.

**The single failure** — an honest data point:

- File: `its-still-nuts-to-me-how-realistic-ai-is-getting-incredible-v0-bcxd5awmq50h1.webp`
- Sourced from a Reddit post whose **title explicitly described the image as a generation chosen for exceptional photorealism.**
- Sightengine returned an AI score of **2.0 %** — confidently wrong.
- The case is not just one bad data point. It demonstrates the **upper bound on what automated detection can achieve** when generative models are specifically optimised to defeat detectors. It's a textbook argument for **layered defences** (provenance signatures, EXIF analysis, source verification) rather than reliance on a single classifier head. This is why TrueSight layers EXIF and JPEG signals on top of the API verdict — the API is not the last word.

**A secondary observation worth raising unprompted:** Sightengine's scores are **strongly bimodal** — every one of the 39 correctly-identified AI images received exactly **99.0 %**; 18 of 19 real photos received exactly **0.1 %**, the 19th received 1.0 %. Only one image in the entire set produced an intermediate score (48 %). This bimodality means the exact location of the binary cut-off matters little — 50 % is symmetric and defensible. It also implies the 5-tier verdict-label brackets (85, 60, 45, 20) primarily affect a small minority of edge cases.

## 9. Architecture in one diagram

```
                                  ┌──────────────────────────────┐
                                  │ Browser (any device on LAN)  │
                                  │ HTML + CSS + vanilla JS      │
                                  └─────────────┬────────────────┘
                                                │  HTTP
                                                │
                  ┌─────────────────────────────┴───────────────────────────┐
                  │  Host machine                                           │
                  │                                                         │
                  │   Static frontend (:8000)        Flask backend (:5000)  │
                  │       └ index.html, script.js,   ├ /predict             │
                  │         style.css, manifest      ├ /history             │
                  │                                  ├ /clear_history       │
                  │                                  └ /uploads/<uuid>      │
                  │                                                         │
                  │       ┌──────────────────────────┴────────────┐         │
                  │       │  Detection orchestrator (model.py)    │         │
                  │       │  - thresholds                         │         │
                  │       │  - EXIF + JPEG signals (Pillow)       │         │
                  │       │  - cascade decision                   │         │
                  │       │  - reason-building                    │         │
                  │       └────────┬────────────────────┬─────────┘         │
                  │                │                    │                   │
                  │       sightengine_client.py    hive_client.py           │
                  │                │                    │                   │
                  │       SQLite (history.db)     uploads/<uuid>.ext        │
                  └────────────────┼────────────────────┼───────────────────┘
                                   │ HTTPS              │ HTTPS (only on AI-positives)
                                   ▼                    ▼
                          Sightengine API          Hive AI V3
                          /check.json              detection endpoint
                          (genai + deepfake)       (attribution)
```

Two architectural lines to defend out loud:

1. **Each external provider has its own client module.** Adding or replacing a provider involves writing one file and changing one import. No detection logic leaks into HTTP code.
2. **The arrow from orchestrator to Hive_Client is labelled "cascade only".** This captures the project's central design decision and distinguishes the architecture from a naive parallel-provider implementation.

## 10. Version evolution — defending the trajectory

| Version | What | Why it changed |
|---|---|---|
| **v1.0** | Five PyTorch / transformers / ONNX classifiers running locally as a jury. | Initial proof-of-concept; heavy dependencies, slow on consumer hardware, outdated within months as new generators appeared. **Demonstrated the cost of self-hosted ML — which justified the pivot.** |
| **v1.1** | Removed the entire ML stack. Switched to Hive V3 as the sole detector. Added dark mode, drag-and-drop, PWA manifest, accessibility pass, SQLite history. | Hive's API has broader and more current engine coverage than any local model I could train. Single-provider dependency was the trade-off. |
| **v1.2 (current)** | Sightengine becomes primary (genai + deepfake in one call); Hive demoted to attribution-only fallback called on AI-positives. Input limits aligned to Sightengine's. Thresholds centralised. `print()` replaced with `logging`. Dependencies pinned. Evaluation framework introduced. | Sightengine has a dedicated deepfake head Hive doesn't expose; the cascade roughly halves Hive quota use; centralisation makes calibration auditable. |

The trajectory you can defend: **each version reduced infrastructure complexity and improved cost-awareness, while increasing reliability by combining better-suited providers.** v1.0 → v1.2 is the story of a deliberate engineering inversion — from "more ML, more local" to "less ML, smarter orchestration".

## 11. Known limitations + future work (be upfront)

### 11.1 Limitations (acknowledge before being asked)

- **Vendor dependency.** Detection capability is bound to Sightengine and Hive. If either provider degrades or shutters its API, TrueSight degrades with it. Mitigation: each provider lives behind a thin client module, so swapping providers is a one-file change.
- **No authentication, no HTTPS, no rate limiting.** LAN-only single-user assumption. Not safe to expose outside the local network.
- **Small test set with class imbalance.** 59 images is sufficient for a graduation evaluation but produces wide confidence intervals on the false-positive rate. A 95 % Wilson confidence interval on the observed zero-false-positive rate spans roughly 0 % to 18 %.
- **No adversarial-image testing.** The single misclassification hints at an upper bound, but the system has not been deliberately stress-tested against generations engineered to defeat detectors.
- **Sightengine's bimodal scores.** The threshold logic is largely insensitive to where the binary cut-off sits because Sightengine clips most outputs to the extremes; finer calibration would require either a different provider or a self-trained model.
- **PIL memory.** A 12 MB JPEG can decode to 500 MB+ resident in RAM. Multiple concurrent uploads on the Flask dev server could OOM the machine.
- **`/history` swallows DB read errors** and returns `[]`. So an empty grid might mean empty DB or might mean a DB read failed.
- **No automated unit tests** on `model.py`. The evaluation harness is the black-box test surface.
- **`start.bat` is Windows-only** and depends on parsing `route print` output.

### 11.2 Future work — scope expansion (most impactful)

TrueSight currently exposes only two of the many models Sightengine and Hive provide. Both expose much wider catalogues that plug into the same orchestration with minimal change. Highest-value additions:

1. **Scam and malicious-content detection.** Sightengine's QR-code model + text-in-image analysis would let TrueSight verify not only "is this real?" but "is this image trying to defraud the user?".
2. **Text-in-image (OCR) extraction.** Surface text in screenshots, watermarks, and image overlays — useful for fact-checking and for catching AI's tell-tale gibberish text rendering.
3. **Watermark detection.** A confirmed stock-photo watermark is a strong real-photo signal; a confirmed AI-tool watermark is dispositive in the other direction.
4. **Safety/moderation models.** Nudity, violence, weapons, hate-symbol, and self-harm classifiers would make TrueSight a triage tool for UGC platforms, not just an authenticity checker.
5. **Image quality + type classification.** Photograph vs illustration; technical quality. Both *qualify* the AI verdict.
6. **Face analysis.** Count faces, estimate ages, flag minors — useful for journalism and a hard-floor moderation signal.

Each follows the same pattern as the current code: enable a model name in the API call, parse the response field, surface as a new signal, drive a reason line from a threshold.

### 11.3 Future work — functional extensions

7. **C2PA / Content Credentials reading.** Adobe Firefly, DALL·E 3, and several Sony/Leica cameras now embed cryptographically-signed provenance manifests. Reading these *locally* would give a higher-confidence signal than any classifier — with zero API cost.
8. **Sightengine's `ai_generators` sub-block.** Once enabled on the project's plan, Hive becomes optional and the cascade simplifies into a single-provider architecture with both verdict and attribution from one call.
9. **Adversarial-aware evaluation.** Curate a targeted set of deliberately-engineered hard cases and report performance separately — an honest lower bound.

### 11.4 Future work — engineering polish

10. **SHA-256 deduplication cache.** Hash every upload before calling the APIs; return cached verdicts on repeats. Eliminates wasted quota on duplicate inputs.
11. **Latency measurement** in the evaluation harness — mean and p95 alongside accuracy.
12. **Wilson confidence intervals** on reported metrics — honest evaluation, no numbers change.

### 11.5 Future work — architectural alternatives

13. **Bayesian fusion of providers** — call both APIs in parallel, combine with explicit disagreement gating. The experimental branch `hive-sighteng` already prototypes this.
14. **Provider portfolio expansion** — add Optic, Illuminarty, or a future open-source detector behind the same client interface. Reduces vendor risk; enables consensus voting on contested verdicts.

### 11.6 Future work — deployment

15. **Authentication + HTTPS + rate limiting** behind Gunicorn + nginx for any non-LAN deployment.
16. **Mobile-native packaging.** The current web UI is already responsive and usable on mobile, but PWA installation or a React Native wrapper would enable one-tap analysis from the phone's share menu — receive an image on WhatsApp, hit Share → TrueSight, get a verdict.

---

# Part 2 — The Codebase

A deep, file-by-file, function-by-function explanation. The goal here is to leave no implementation detail unexplained, so any "why is this here?" or "what happens if X?" question has an answer.

## 12. Bird's-eye view (one paragraph)

TrueSight is a Flask + vanilla-JS web app. The browser uploads an image to a Flask endpoint. Flask validates and renames the file, then hands the path to `predict_image()`. That function reads local forensic signals (size, EXIF, JPEG quantization), calls **Sightengine's** `genai + deepfake` model as the primary detector, and — **only if the image is flagged as AI** — calls **Hive AI** as a secondary lookup to identify *which* generator likely produced the image. The function returns a verdict label, a 0–100 score, a list of human-readable reasons, a signals dictionary, and an EXIF metadata summary. Flask inserts the result into a SQLite history table and returns JSON to the browser. The browser renders the verdict, a confidence bar, an attribution row (if any), an EXIF panel, and updates the history grid.

## 13. Repository layout (annotated)

```
TrueSight_v1.0_copy/
├── backend/
│   ├── app.py                      Flask app — routes, DB, file I/O, validation
│   ├── ai_model/
│   │   ├── __init__.py             Empty — marks ai_model as a package
│   │   ├── model.py                Orchestrator: thresholds, cascade, reason-building
│   │   ├── sightengine_client.py   HTTP wrapper for Sightengine /check.json
│   │   └── hive_client.py          HTTP wrapper for Hive's V3 detection API
│   ├── verify_sightengine.py       Manual smoke test (NOT a pytest suite)
│   ├── evaluate.py                 Ground-truth evaluation harness → confusion matrix + report
│   ├── requirements.txt            5 pinned packages, zero ML deps
│   ├── history.db                  SQLite DB (created at first run)
│   ├── uploads/                    UUID-named saved images
│   └── .env                        HIVE_API_KEY, SIGHTENGINE_API_USER/SECRET (gitignored)
├── frontend/
│   ├── index.html                  Single-page shell, two tabs + two modals + lightbox
│   ├── script.js                   ~650 lines, flat, no framework
│   ├── style.css                   ~1400 lines, CSS-variable theming (light + dark)
│   ├── manifest.json               PWA manifest
│   └── assets/                     Logos, favicons, PWA icons
├── Test/                           Sample images + Test/README.md ground-truth table
├── start.bat                       Windows launcher (auto-detects LAN IP)
├── evaluation_report.md            Output of `evaluate.py` — confusion matrix + per-image table
├── evaluation_results.json         Machine-readable evaluation cache
├── README.md                       User-facing docs
├── CHANGELOG.md                    v1.0 → v1.1 → v1.2 evolution
└── docs/                           Dissertation chapters, architecture, viva prep
```

## 14. The end-to-end request flow (numbered, with file:line anchors)

The user uploads one image and gets one verdict. Here is every step in order.

1. **Browser file pick.** [frontend/script.js:258-278](../frontend/script.js#L258-L278) listens to the `<input type="file">` `change` event. It checks the file is ≤ 12 MB (matching the backend cap exactly), reads the file as a base64 data URL via `FileReader`, displays the preview, hides the drop-zone, and enables the "Analyze Image" button.
2. **Click "Analyze".** [frontend/script.js:304-404](../frontend/script.js#L304-L404) builds a `FormData` with field name `image` and `fetch`es `POST /predict`.
3. **Flask receives the request.** [backend/app.py:72-131](../backend/app.py#L72-L131) is the `/predict` handler:
   - Rejects empty filename or wrong extension (whitelist: jpg/jpeg/png/webp/bmp/tif/tiff/jp2).
   - `secure_filename()` sanitises any user-supplied name (defence-in-depth).
   - Renames the file to `<uuid4-hex>.<ext>` → prevents collisions and path-disclosure.
   - Saves to `backend/uploads/`.
   - Opens with PIL once to verify the magic bytes. If they don't match a whitelisted format, the file is deleted and a 400 returned. This is the "renamed `.exe` to `.jpg`" defence.
4. **Hand off to detection layer.** [backend/app.py:105](../backend/app.py#L105) calls `predict_image(image_path)` from `ai_model.model`.
5. **`predict_image()` reads local signals.** [backend/ai_model/model.py:62-85](../backend/ai_model/model.py#L62-L85) opens the image **once** with PIL and pulls `(width, height, metadata{has_exif, camera, software}, quant_avg)`. Single open is intentional — opening multiple times would double memory pressure on large JPEGs.
6. **Dimension checks.** [model.py:135-158](../backend/ai_model/model.py#L135-L158) rejects images > 64 MP total or < 8 px per side. Mirrors Sightengine's published limits — fail locally instead of round-tripping for an HTTP 400.
7. **Sightengine call.** [model.py:160-186](../backend/ai_model/model.py#L160-L186) calls `sightengine_client.classify_image(path)`. On network exception or non-success status, returns `"Error"` with a user-facing reason — the UI keeps working.
8. **Score parsing.** [model.py:188-191](../backend/ai_model/model.py#L188-L191) reads `response["type"]["ai_generated"]` and `response["type"]["deepfake"]` (both 0.0–1.0) and multiplies by 100.
9. **Cascade decision.** [model.py:193-196](../backend/ai_model/model.py#L193-L196): if `ai_score >= 50%` (the `AI_THRESHOLD` constant), call `_hive_attributions(path)`. Otherwise skip Hive entirely — saves quota and 5–30 s of latency on real photos.
10. **Hive attribution parsing.** [model.py:88-110](../backend/ai_model/model.py#L88-L110) iterates `response["output"][0]["classes"]` and keeps only items whose class name is **not** one of the 9 "base" classes (`ai_generated`, `deepfake`, `inconclusive`, etc.). Everything left is a candidate engine attribution (`midjourney`, `gpt-4o`, `flux`, …). Probabilities < 1 % are dropped as noise.
11. **Signals dictionary built.** [model.py:202-210](../backend/ai_model/model.py#L202-L210) populates `signals` with Sightengine's two scores plus one `Attribution (<engine>)` entry per Hive-returned engine.
12. **Reasons list built.** [model.py:212-248](../backend/ai_model/model.py#L212-L248) appends 4–6 human-readable bullet strings with emoji prefixes (✅ ⚠️ ❌ 🤖):
    - Sightengine AI verdict tier (strong / partial / none).
    - Top Hive engine (only if AI-flagged).
    - Deepfake tier (only if score is present and ≥ 50 %).
    - EXIF presence and camera model.
    - AI-software EXIF flag (matches against `AI_SOFTWARE_NAMES`).
    - JPEG quantization warning if `quant_avg > 25`.
13. **Verdict label selection.** [model.py:251-255](../backend/ai_model/model.py#L251-L255) walks `LABEL_THRESHOLDS` (descending list of cut-offs) and picks the first label whose cut-off the score crosses. Defaults to `"Real Photo"`.
14. **Return tuple.** `(label, ai_score, reasons, signals, metadata)` flows back to Flask.
15. **DB insert + JSON response.** [app.py:108-127](../backend/app.py#L108-L127) writes one row to `history` and returns `{verdict, score, reasons, metadata, filename, signals}`. `score` is divided by 100 here so the frontend gets a fraction; the frontend multiplies by 100 back to a percentage (deliberate mirror of the wire format).
16. **Frontend render.** [script.js:328-394](../frontend/script.js#L328-L394) maps the score onto its own 5-tier label/colour (independent of the backend's label), updates the headline, progress bar, signals list, attribution row, and stores `currentAnalysis` for the details modal.
17. **History refresh.** [script.js:394](../frontend/script.js#L394) fires `fetchHistory()` so the History tab's grid is up-to-date.

End-to-end: 1 multipart upload, 1 disk write, 1 PIL open, 1 Sightengine API call, 0 or 1 Hive API call, 1 SQLite insert, 1 JSON response, ~6 DOM updates.

## 15. `backend/app.py` — Flask layer

### 15.1 Imports and config (lines 1-33)

- `from dotenv import load_dotenv; load_dotenv()` runs **before** any `os.environ` read. If this came after, the API credentials would be missing.
- `logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper(), ...)` configures the root logger; v1.2 retired the old `print()` calls in favour of this.
- `BASE_DIR = os.path.dirname(os.path.abspath(__file__))` makes all paths absolute and relative-to-this-file — app behaves identically regardless of `cwd`.
- `ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff", "jp2"}` matches the `<input accept="">` and the PIL magic-byte check.
- `MAX_FILE_SIZE = 12 * 1024 * 1024` matches Sightengine's hard upload limit. Setting `app.config["MAX_CONTENT_LENGTH"]` means Flask returns HTTP 413 for oversize requests automatically.
- `CORS(app)` is unrestricted — LAN-only assumption. Any tightening happens with deployment, not in code.

### 15.2 `init_db()` (lines 39-56)

```sql
CREATE TABLE IF NOT EXISTS history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT NOT NULL,        -- the on-disk UUID name, not original
    result      TEXT NOT NULL,        -- verdict label string
    confidence  REAL,                 -- ai_score 0–100
    reasons     TEXT,                 -- JSON-serialised list[str]
    timestamp   TEXT                  -- "YYYY-MM-DD HH:MM" local time
)
```

- `IF NOT EXISTS` makes startup idempotent.
- `reasons` is a JSON string — SQLite has no array type, and v1.x did not justify adding a normalised `reasons` table.
- `timestamp` is text not numeric epoch — easier to read in DB browsers, slightly less precise. We never sort on it (we sort on `id DESC`), so the lossy format is fine.
- No indexes. Justified: only read query is `ORDER BY id DESC LIMIT 50`, which uses the implicit `rowid` index.

To migrate the schema there's no Alembic/Flask-Migrate — you either ship `ALTER TABLE` in `init_db()` or ask the user to delete `history.db`.

### 15.3 `allowed_file()` (lines 58-60)

Two-line extension whitelist. `rsplit(".", 1)` — files named `evil.png.exe` see `"exe"` here and are rejected.

### 15.4 `serve_image()` (lines 66-68)

Thin wrapper over Flask's `send_from_directory`, which is **safe against path traversal** by design — refuses any filename containing `..` or absolute paths.

### 15.5 `predict()` — the main endpoint (lines 72-131)

Validation order is deliberate:

1. **Presence check** — returns 400 immediately if no file. No disk write.
2. **Empty filename** — covers the case where the form was submitted with no selection.
3. **Extension whitelist** — rejected before any disk write.
4. **`secure_filename()` + UUID rename** — sanitises and decouples the on-disk name from anything the user provided. Original filename is discarded entirely.
5. **File saved.** ✱ At this point, an attacker has succeeded in writing arbitrary bytes to `uploads/<uuid>.<our-chosen-ext>`. The next check is what stops them from doing anything useful with that.
6. **PIL magic-byte check.** `Image.open()` throws on any file that isn't a real image. If `img.format` is unexpected, file is explicitly removed from disk before returning 400. This is the layer that defeats the renamed-`.exe` attack.

Three more details:

- **Whole function wrapped in `try/except`** returning a generic `"Internal server error"` 500 with the real exception logged at `logger.exception` level. Never leak stack traces to the client.
- DB `INSERT` uses `sqlite3.connect(...)` with `with` — auto-commits on success, auto-closes on exception. Never hold a connection between requests.
- Response body is hand-shaped, not auto-serialised. The frontend depends on exact field names (`verdict`, `score`, `reasons`, `metadata`, `filename`, `signals`). Any rename here is a breaking API change.

### 15.6 `get_history()` (lines 135-159)

- `conn.row_factory = sqlite3.Row` lets us index columns by name.
- 50-row cap hardcoded — no pagination. The UI is one scrolling grid.
- `json.loads(row["reasons"])` deserialises bullets. Malformed JSON would raise and trigger the outer `except`, which returns `[]`. **Known gotcha**: History tab will look empty if reads start failing for any reason.

### 15.7 `clear_history()` (lines 163-180)

Deletes everything in `uploads/` then runs `DELETE FROM history`. Two consequences:

- **Race condition**: a new scan in-flight while `clear_history` runs could have its image deleted before its DB row is written. Acceptable on a single-user LAN app.
- **No auth**. Anyone on the LAN can wipe history with `curl -X DELETE`. The frontend gates this behind a confirm modal, but that's UX, not security.

### 15.8 `add_header()` — cache headers (lines 184-191)

- API responses get `Cache-Control: no-store, no-cache, must-revalidate`. Avoids stale History tab after a new scan or clear.
- `/uploads/*` is exempt — UUID-named blobs are immutable, let them cache. Critical for the History grid (50 thumbnails would re-download every tab switch otherwise).

### 15.9 `app.run()` (lines 193-195)

`host='0.0.0.0'` is what makes the backend reachable from other LAN devices. `127.0.0.1` would bind to loopback only. `FLASK_DEBUG=true` enables the dev autoreloader + interactive tracebacks — **never** for production (RCE risk via the Werkzeug debugger).

## 16. `backend/ai_model/model.py` — the orchestrator

The single most important file in the project. Everything that distinguishes TrueSight from "a thin wrapper around the Sightengine API" lives here.

### 16.1 Module-level constants (lines 14-49)

All knobs at the top so calibration doesn't require chasing the code:

| Constant | Value | Meaning |
|---|---|---|
| `MAX_IMAGE_MEGAPIXELS` | 64 | Sightengine's own upper bound. |
| `MIN_IMAGE_DIMENSION` | 8 px | Sightengine refuses tiny images. |
| `AI_THRESHOLD` | 50.0 | At/above this, call Hive for attribution; mark as AI in the evaluation harness. |
| `LABEL_THRESHOLDS` | list of `(cutoff, label)` | Headline verdict string. 5 tiers. |
| `DEFAULT_LABEL` | `"Real Photo"` | Returned when score falls below the lowest threshold. |
| `SE_STRONG` / `SE_PARTIAL` | 90 / 60 | Cut-offs for the "Sightengine Detector" reason line wording. |
| `DEEPFAKE_HIGH` / `DEEPFAKE_SUSPICIOUS` | 90 / 50 | Cut-offs for the "Deepfake Check" reason line. |
| `JPEG_HEAVY_COMPRESSION` | 25 | Average luma quantization above which we add a "result less reliable" disclaimer. |
| `AI_SOFTWARE_NAMES` | 13 entries | Substring match against EXIF `Software` tag. |
| `_HIVE_BASE_CLASSES` | 9 entries | Hive class names that are verdict-level, not engine-level. Anything outside this set is a candidate engine. |

**Why two threshold layers?** `AI_THRESHOLD` is the binary cut-off used by the cascade and the evaluation harness. `LABEL_THRESHOLDS` is a finer-grained 5-tier mapping used only for the headline verdict shown to the user. Keeping them separate means UI tuning never shifts the evaluation metrics.

**Why a substring match on `AI_SOFTWARE_NAMES`?** EXIF `Software` strings in the wild look like `"Adobe Firefly 2.0"`, `"Stable Diffusion XL"`, `"ComfyUI custom workflow"` — exact matching would miss almost everything. Substring is permissive on purpose. The list includes both `"dall-e"` and `"dall·e"` because the middle character can be ASCII hyphen or Unicode middle-dot.

### 16.2 `_read_image_signals(image_path)` (lines 62-85)

Opens the image **once** with PIL, in a `with` block, and pulls four things:

- `width, height` — for the megapixel check.
- `img_format` — gates the quantization check (only JPEGs have quant tables).
- `exif_data = img.getexif()` — PIL's modern EXIF API. Mapped to tag names via `TAGS` from `PIL.ExifTags`.
- `quant_avg` — average value of the luma (channel 0) quantization table. Computed only for JPEGs.

**Why average the luma table?** JPEG stores per-frequency quantization steps in an 8×8 matrix. Higher values mean coarser quantization (more compression, more information loss). The mean is a crude but stable scalar proxy for "how heavily was this re-encoded". Not in the UI; drives only the "may be less reliable" reason line.

**EXIF defensiveness.** Some EXIF values come back as non-strings (`PIL.TiffImagePlugin.IFDRational`, bytes, etc.). We always `str(...)` them before storing, so the JSON serialiser can't crash on something exotic.

Returns `(width, height, metadata, quant_avg)` where `metadata` is always a dict with keys `has_exif`, `camera`, `software` — never `None`, never missing keys. Matters because the frontend reads `item.metadata?.camera || "N/A"`; if backend returned `None`, the frontend would render `"None"`.

### 16.3 `_hive_attributions(image_path)` (lines 88-110)

Calls `hive_classify(path)` inside `try/except` and returns `{}` on any failure. Hive is positioned as a **best-effort enrichment**, not a hard dependency — if Hive is down, the user still gets a Sightengine-based verdict, just without the engine attribution row.

After the call, it walks `response["output"][0]["classes"]` and keeps:

- Items whose class name is **not** in `_HIVE_BASE_CLASSES` (skips Hive's own verdict classes like `ai_generated`, `deepfake`, `inconclusive`).
- Items whose probability is **> 0.01** (drops noise).

Returns `dict[engine_name, percentage]`, e.g. `{"midjourney": 87.4, "flux": 6.1}`.

### 16.4 `predict_image()` — the main function (lines 113-257)

Control flow:

1. **Read signals.** On exception (PIL can't open) — return `"Error"` with "Could not read image file". Defensive; `app.py` already did a PIL open, but this function is reachable independently from `evaluate.py` and `verify_sightengine.py`.
2. **Dimension gates.** Return `"Error"` if MP > 64 or any side < 8 px.
3. **Sightengine call.** Three failure modes handled independently:
   - Network/HTTP exception → `"Detection service unavailable..."`
   - HTTP 200 but `status != "success"` → bubble Sightengine's error message.
   - Missing `type.ai_generated` field → `"Invalid response format"`.
4. **Score extraction.** `ai_score = float(ai_generated_raw) * 100`. `deepfake_score` is `None` if absent — we never assume it's there.
5. **Cascade gate.** `image_is_ai = ai_score >= AI_THRESHOLD`. Only when `True` do we call `_hive_attributions(path)`. The top engine is `max()` over the dict.
6. **Build `signals` dict.** Keys: `"Sightengine AI Classifier"`, `"Sightengine Deepfake"` (if present), and one `"Attribution (<engine>)"` per Hive engine. **The exact key prefix `"Attribution ("` matters** — the frontend uses a regex to split signals into "stats" and "attribution" rows.
7. **Build `reasons` list.** Six independent reason-emitting blocks, each guarded by a threshold. Each reason is a short emoji-prefixed string. The emoji prefix is what the frontend uses in `classifySignal()` to pick a badge colour, so the emoji is part of the API contract.
8. **Headline label.** Loop over `LABEL_THRESHOLDS` (already descending). First match wins.
9. **Return.** `(label, round(ai_score, 2), reasons, signals, metadata)`.

**Why is the verdict label produced server-side when the frontend also has its own label function?** Two reasons:

- The headline label is stored in `history.db` for the user's records, independent of frontend versions.
- The frontend `getForensicLabel()` uses **different cut-offs** (20 / 45 / 60 / 85) and **different labels** (`Real Photo`, `Likely Real`, `Hard to Tell`, `Suspicious`, `AI Generated`) than the backend. This is *deliberate* — the backend label is for storage and reporting; the frontend label is for instant colour/icon. They're allowed to diverge.

## 17. `backend/ai_model/sightengine_client.py` — Sightengine HTTP wrapper

Twenty-six lines. Single responsibility: send the image to `https://api.sightengine.com/1.0/check.json` with `models=genai,deepfake`, return parsed JSON.

- **Credentials come from `os.environ`**, not module-level globals — `.env` reloads on restart.
- A missing key raises `RuntimeError` — caught in `model.py`, converted to a verdict-level error reason.
- `requests.post(..., files={"media": f}, timeout=60)`. The `files` parameter forces multipart/form-data. 60-second timeout is the **synchronous latency ceiling**.
- `response.raise_for_status()` converts HTTP 4xx/5xx into `requests.HTTPError`.

**Quota cost.** Each scan invokes both models, billed as **10 operations** (5 per model). Free tier 2,000 ops/month → ~200 scans/month ceiling.

## 18. `backend/ai_model/hive_client.py` — Hive HTTP wrapper

Even smaller — 35 lines. Posts to `https://api.thehive.ai/api/v3/hive/ai-generated-and-deepfake-content-detection` with `Authorization: Bearer <HIVE_API_KEY>` and multipart `media` field. Same 60 s timeout, same `raise_for_status()`.

**Hive V3 response shape** (relevant portion):

```json
{
  "output": [
    {
      "classes": [
        {"class": "ai_generated", "value": 0.98},
        {"class": "midjourney",   "value": 0.87},
        {"class": "flux",         "value": 0.06},
        {"class": "deepfake",     "value": 0.01}
      ]
    }
  ]
}
```

`model.py`'s job is to (a) ignore verdict classes, (b) keep engine classes, (c) convert `value` to a percentage, (d) drop noise below 1 %.

**Why Hive at all, given Sightengine is primary?** Sightengine's `genai` model returns *whether* an image is AI, not *which* model produced it. Hive's V3 returns per-engine probabilities. Combining costs more, so the cascade only pays the Hive cost when there's a positive Sightengine score to attribute.

## 19. `backend/verify_sightengine.py` — manual smoke test

Not a pytest suite. A 73-line script that:

1. **Test 1.** Pops the Sightengine env vars and runs `predict_image()` on a sample — confirms it returns `"Error"` gracefully rather than crashing.
2. **Test 2.** Restores env vars, runs on a known-AI sample, prints the result.

`_safe_print(reasons)` strips non-ASCII (emoji prefixes) so Windows `cmd` doesn't choke on encoding.

Run manually — there is no CI, no automated test gate, no coverage report. Deliberate scope decision: this is a graduation prototype, the value is in the orchestration design and the dissertation, not in test infrastructure.

## 20. `backend/evaluate.py` — evaluation harness

The file that produces the dissertation's numbers.

### 20.1 Ground-truth source

`Test/README.md` contains a markdown table. Relevant rows look like:

```
| `IMG_8923.jpg`               | Real    | ... |
| `midjourney-portrait-v6.jpg` | AI      | ... |
| `someimage.jpg`              | Unknown | ... |
```

`parse_ground_truth()` walks the file with a regex, keeps rows whose **Expected** column starts with `"Real"` or `"AI"` (case-insensitive), skips `"Unknown"` / blank. Result: `{filename: "real"|"ai"}`.

**You control which images are in the metrics by editing one markdown table.** No file moves, no renames, no code edits.

### 20.2 Single-image evaluation

For each labelled file:

1. Verify the file exists on disk (markdown can drift from filesystem).
2. Call `predict_image(path)`.
3. Convert `ai_score` to binary `predicted_label` using the **same** `AI_THRESHOLD = 50` constant imported from `model.py`. Single source of truth — bump the threshold to 60 and both runtime and evaluation pick it up.
4. Walk `signals` dict for the highest-scoring `Attribution (<engine>)` entry → `top_engine`.
5. Wrap in a `Result` dataclass with a `correct` boolean.

### 20.3 Caching to avoid re-spending budget

`load_cached_results()` reads `evaluation_results.json` from the previous run. Any **successful** result whose ground-truth label still matches `Test/README.md` is reused — no second API call. **Errored results are not cached** so transient outages get retried automatically.

### 20.4 Outputs

- **stdout**: sorted per-image table + matrix + four metrics. Sort key: `(true_label != "ai", -ai_score)` — AI images first, descending by score, so most confident calls at the top.
- **`evaluation_results.json`**: machine-readable with `summary` block and `results` list. Also the cache for the next run.
- **`evaluation_report.md`**: dissertation-ready Markdown with methodology, sample composition, matrix, metrics, per-image breakdown, **failure analysis** (each wrong call as its own subsection with the model's reasons), and errors. **This is the artefact cited verbatim in chapter 7.**

## 21. `frontend/index.html` — DOM shell

Two views (tabs) + three overlays + a toast container, all in a 233-line file.

### 21.1 `<head>` highlights

- Three `Cache-Control` `<meta>` tags + `Pragma` + `Expires` to defeat browser caching of `index.html` itself.
- `style.css?v=7` / `script.js?v=7` query-string cache busts — bump `v=` to force reload during development.
- Three favicons + Apple-touch-icon for installability.
- PWA `manifest.json` linked.
- `apple-mobile-web-app-*` metas for iOS "Add to Home Screen" native-app feel.
- `theme-color: #003057` (TrueSight navy) drives the Android address-bar tint.
- **Inline theme bootstrap** runs before stylesheet parsing:

  ```js
  const t = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', t);
  ```

  Avoids flash-of-unstyled-content where the page renders in light mode for one frame before JS sets dark.

### 21.2 Structure

- `<header>` holds two logo images (light + dark variants), CSS hides the wrong one.
- `<nav class="tab-bar">` — two `<button role="tab">`s + a theme toggle pill. Full ARIA: `aria-selected`, `aria-controls`, `tabindex` swaps between `0` and `-1`.
- `#home-view` — two-column layout (intro card left, upload card right). CSS collapses to single column on narrow screens.
- `#dropZone` — a `role="button" tabindex="0"` div (keyboard-focusable). Hidden `<input type="file">` lives inside it, `.click()`-ed programmatically.
- `#previewContainer`, `#result` — hidden by default, unhidden by JS.
- `#detailsModal`, `#confirmModal`, `#imageLightbox` — three sibling overlays at end of `<body>`. All `role="dialog" aria-modal="true"`, focus traps when open.
- `#toastContainer` — live region (`role="status" aria-live="polite"`) for transient messages.

**Why `role="button"` on a div** instead of a `<label for="">`? Because we wanted the dropzone to be both clickable and droppable, and look like a card. A `<label>` can't be a drop target. The div + `role=button` + `keydown` handler for Enter/Space matches WAI-ARIA's button pattern.

## 22. `frontend/script.js` — all the behaviour

Flat file, ~650 lines, grouped by section. No module system, no bundler, no transpilation.

### 22.1 Theme toggle (lines 1-9)

`toggleTheme()` flips `data-theme`, persists to `localStorage`. The matching CSS variable block does the rest.

### 22.2 Network setup (lines 11-18)

```js
const currentIP = window.location.hostname;
const BASE_URL  = `http://${currentIP}:5000`;
```

This is the line that **makes the phone-from-LAN flow work**. If we hardcoded `localhost`, only the PC running both servers could use the app. By taking hostname from `window.location`, a phone at `http://192.168.1.7:8000/index.html` derives `BASE_URL = http://192.168.1.7:5000`.

### 22.3 `getForensicLabel(score)` (lines 29-41)

Five tiers: `Real Photo` / `Likely Real` / `Hard to Tell` / `Suspicious` / `AI Generated`. Cut-offs **20 / 45 / 60 / 85**, different from the backend's `LABEL_THRESHOLDS` — see § 16.4 for why. Colours are hardcoded hex (matches the `--success`/`--danger` palette but inlined into `style="color:..."`).

### 22.4 Toast + confirm helpers (lines 55-131)

- `showToast(message, type, duration)` builds a DOM node, appends to `#toastContainer`, schedules CSS-animated removal at `duration` ms (default 3.5 s). Click-to-dismiss.
- `showConfirm({...})` returns a **Promise**. Three things on open: (1) `document.activeElement` saved, (2) modal shown with focus on **Cancel** (safer default), (3) `keydown` intercepted — Escape cancels, Tab triggers `trapFocus()`. On close: listeners removed, focus restored. Full WCAG modal behaviour.

### 22.5 `trapFocus(e, container)` (lines 133-147)

Standard pattern: collects focusable children, wraps Tab from last→first and Shift+Tab from first→last.

### 22.6 `escapeHTML(s)` (lines 149-156)

Replaces `& < > " '`. Used everywhere Hive engine names or EXIF software strings get injected into `innerHTML`. **This is the only XSS defence on the frontend** — anything reading user/API-controlled text into `innerHTML` must go through this helper.

Where we use `innerHTML` deliberately: signals breakdown, history grid items. Where we use `textContent`: reason bullets in the modal. Mixing styles is intentional — `textContent` is the safer default; `innerHTML` is used only where we want emoji prefixes / icons / structured layout.

### 22.7 `switchTab(tabName)` (lines 161-180)

Updates `aria-selected`, `tabindex`, `.active` class, toggles `display`. Side effect: switching to History fires `fetchHistory()`.

### 22.8 DOMContentLoaded handler (lines 185-405)

The single big handler that wires up the home view:

- **Click → file picker.** `dropZone.click()` → `fileInput.click()`.
- **Keyboard.** Enter/Space on dropzone triggers picker.
- **Drag and drop.** Four listeners (`dragenter`, `dragover`, `dragleave`, `drop`) maintain a `dragCounter` to handle child-element bounce. `dragenter` fires multiple times when dragging over nested elements — increment/decrement, only remove highlight when counter hits 0. On drop, file hand-transferred into `fileInput.files` via `DataTransfer` so the existing `change` handler runs.
- **Global drag prevention.** Window-level listeners prevent the browser from navigating to the dropped file if user misses the dropzone.
- **File change.** Size check (12 MB hard cap, matches backend), `FileReader.readAsDataURL` for preview, hide dropzone, show preview, enable Analyse.
- **`resetForNewAnalysis()`.** Single function returning UI to initial state. Used by Remove button + Analyse-Another button. Includes `scrollIntoView` and `focus` so user lands cleanly on the dropzone.
- **Upload button click.** Builds `FormData`, fetches `/predict`. On success: maps score → forensic label, writes title with icon and colour, writes "X% AI Likelihood", sets progress bar width and colour, hides loader, builds signals breakdown (split by `"Attribution ("` prefix), saves `currentAnalysis`, refreshes history. On HTTP error: pulls `data.error` for the toast. On network exception: generic "Server error" toast.

### 22.9 `fetchHistory()` (lines 410-455)

- **Change detection.** `lastHistoryJson` stores the last JSON string. If identical, **don't re-render** — saves flicker and 50 DOM rebuilds on refresh spam.
- **Empty state** / **error state** explicit.
- **Rendering.** Per item: thumbnail (`/uploads/<filename>`), forensic label headline, confidence line. Click opens details modal pre-filled.

### 22.10 `clearHistory()` (lines 457-474)

Promise-await confirm dialog, `DELETE /clear_history`, refresh. Success toast.

### 22.11 Modal + lightbox (lines 479-647)

- `openDetailsModal(data)` accepts an explicit item (from history) or falls back to `currentAnalysis`. Populates image, EXIF labels, reasons list, signals list (signals appended as more reasons in the same `<ul>`, with colour class by score: red ≥ 60, amber ≥ 30, green < 30).
- `classifySignal(text)` is a string-match dispatcher — looks at emoji prefix (`✅` / `❌` / `⚠️`) and assigns a CSS class. This is why the backend's emoji prefixes are part of the API contract.
- **Lightbox** is a second overlay layered on top of details modal. The trick handled in `closeLightbox()`: closing the lightbox should **not** release the body's `modal-open` class if details modal is still open underneath. It checks both other modals' display state first.

## 23. `frontend/style.css` — theming and layout

1,393 lines. Big design decisions:

### 23.1 CSS-variable theme tokens

All colours, radii, shadows live in `:root` and `[data-theme="dark"]`. Every rule that uses colour does so via `var(--name)`. Adding a new component does **not** require new colour decisions — reach for an existing token.

### 23.2 Light + dark in one stylesheet

Dark variant is `[data-theme="dark"]` overrides at the top, plus a few `[data-theme="dark"] .something` rules for components where the override isn't a colour swap (e.g. logo PNGs toggled with `display: none/block`).

### 23.3 Accessibility-load-bearing features

- `:focus-visible` styling everywhere — keyboard users see focus rings, mouse users don't.
- Theme pill has explicit `focus-visible` style so its keyboard focus state is visible.
- `@media (prefers-reduced-motion: reduce)` flattens transitions for motion-sensitive users.
- `body.modal-open { overflow: hidden }` prevents background scroll behind dialogs.

### 23.4 Layout strategy

- `body` is flex, centres a `.app-container { max-width: 460px }`. The whole app looks like a mobile column even on a 4K monitor — intentional, primary device is a phone.
- Home view uses `.home-grid` (CSS grid) — intro panel beside upload card on wide screens, stacked on narrow.
- History view is a CSS grid of cards.

## 24. `frontend/manifest.json` — PWA

Five keys: `name`, `short_name`, `description`, `start_url`, `scope`, `display: standalone`, plus 192 px and 512 px maskable icons. Makes "Add to Home Screen" produce an icon that opens the app full-screen (no browser chrome). Orientation locked to portrait — phone-first.

## 25. `start.bat` — Windows launcher

32 lines:

1. Parses `route print` output to extract LAN IPv4.
2. Opens new `cmd` for backend (`venv\Scripts\python.exe app.py`).
3. Opens second `cmd` for static file server (`python -m http.server 8000`).
4. Prints `http://<IP>:8000` for the user to type into their phone.

**Caveats**: Windows-only, depends on `route print` output format, no graceful shutdown — closing windows kills processes hard. No `start.sh` equivalent.

## 26. Security model — every check, in order

When asked about defending against malicious uploads, here's the full ordered list:

1. **Browser-side `accept` filter** ([index.html:105](../frontend/index.html#L105)) — `accept="image/jpeg,image/png,..."`. UX only; bypassable.
2. **Browser-side size check** ([script.js:262](../frontend/script.js#L262)) — `file.size > 12 MB → reject`. Bypassable.
3. **Flask `MAX_CONTENT_LENGTH`** ([app.py:33](../backend/app.py#L33)) — HTTP 413 returned by Flask before our handler runs. **Cannot** be bypassed.
4. **Extension whitelist** ([app.py:83](../backend/app.py#L83)) — only 8 whitelisted extensions accepted.
5. **`secure_filename()`** ([app.py:88](../backend/app.py#L88)) — strips path separators, control chars, leading dots. Defence-in-depth.
6. **UUID rename** ([app.py:90](../backend/app.py#L90)) — original filename discarded entirely. No user bytes in any path.
7. **PIL magic-byte check** ([app.py:97-102](../backend/app.py#L97-L102)) — `Image.open()` parses actual bytes; format mismatch → file deleted + 400. This is the layer that closes the renamed-`.exe` attack.
8. **Dimension cap** ([model.py:135-158](../backend/ai_model/model.py#L135-L158)) — > 64 MP rejected, bounds memory.
9. **Parameterised SQL** ([app.py:113-116](../backend/app.py#L113-L116)) — `?` placeholders. SQL injection not possible.
10. **HTML escaping on frontend** — `escapeHTML()` on every Hive/EXIF/Sightengine string in `innerHTML`.
11. **Cache-Control on API responses** — prevents stale verdicts in proxies/browsers.

**Deliberately not defended against** (be ready to defend each as a scope boundary):

- **CSRF** — no auth → nothing to forge.
- **Auth bypass** — no auth in the first place.
- **Network-level attacks** — no HTTPS, LAN-only.
- **Rate limiting / DoS** — single user, not a concern at design scale.

## 27. Data flow types (the wire contract)

The `/predict` response — frontend and backend agree on these exact keys:

```ts
{
  verdict:  string                  // "AI Generated" | "Likely AI Generated" | ... | "Real Photo" | "Error"
  score:    number                  // 0.0–1.0 (fraction; frontend multiplies by 100)
  reasons:  string[]                // each starts with ✅ / ⚠️ / ❌ / 🤖 (used as a tag by the frontend)
  metadata: {
    has_exif: boolean,
    camera:   string,               // "Unknown" if absent
    software: string,               // "Unknown" if absent
  },
  filename: string,                 // the UUID name, used to fetch /uploads/<filename>
  signals:  {
    "Sightengine AI Classifier":   number,           // %
    "Sightengine Deepfake"?:       number,           // % (absent if Sightengine returned nothing)
    "Attribution (<engine>)"?:     number            // % (zero or more)
  }
}
```

`/history` response:

```ts
Array<{
  id:         number,
  filename:   string,
  result:     string,
  confidence: number,        // 0–100
  reasons:    string[],
  timestamp:  string         // "YYYY-MM-DD HH:MM"
}>
```

Both sent with `Cache-Control: no-store`.

## 28. Performance characteristics

Where time goes on a single scan:

| Phase | Typical time | Notes |
|---|---|---|
| Browser → Flask upload | < 100 ms on LAN | Wi-Fi throughput-bound. |
| File save + PIL magic check | 50–200 ms | Disk write + PIL header parse. |
| `_read_image_signals` | 100–500 ms | EXIF read dominates. |
| **Sightengine call** | **1–5 s** | **The dominant cost.** |
| Hive call (when AI-flagged) | 5–30 s | Only on positives. Hive V3 is slower than Sightengine. |
| DB insert | < 10 ms | One row, parameterised statement. |
| Response + DOM update | < 100 ms | Tiny JSON payload. |

**Total**: 1.5–6 s for a real photo (no Hive), 6–35 s for an AI photo (cascade). Frontend spinner gives no progress % because both providers give no streaming hint — only a final response.

**Memory** dominated by PIL decoding the JPEG: 12 MB JPEG → > 500 MB RAM. Multiple concurrent uploads on Flask dev server could OOM the machine. Production-readiness item.

## 29. Likely viva questions → where the answer lives

| Question | Where in this doc |
|---|---|
| Who is this for? Why does it exist? | § 2, § 3 |
| What did you build? | § 4, § 9 |
| Why two cloud APIs? | § 5 (table row), § 18 last paragraph |
| Why the cascade? | § 5, § 14 step 9, § 16.4 |
| How accurate is it? | § 8 |
| What's the one failure case? Why? | § 8 (the Reddit photorealism case) |
| Why no own model? | § 5 (table row), § 10 |
| How does it compare to Hive/Sightengine alone, or to Optic, or to C2PA? | § 6 |
| Walk me through what happens when I click "Analyze". | § 14 |
| How do you stop someone uploading an `.exe` renamed to `.jpg`? | § 26, step 7 |
| Where would you put auth if you had to ship publicly? | § 11.6 |
| How do you measure accuracy? | § 20 (and `evaluation_report.md`) |
| Why two label functions (server + client)? | § 5 (table row), § 16.4 last paragraph |
| What happens if Hive is down? | § 16.3 ("best-effort enrichment") |
| Biggest single bottleneck? | § 28 — the Sightengine call. |
| How would you scale to 1,000 users? | § 11.6 — gunicorn + reverse proxy, Postgres, S3 uploads, auth, background workers. Each is a feature, not a refactor. |
| Why no tests? | § 19 last paragraph (scope decision). |
| SQLite schema and why? | § 15.2 |
| How does the phone reach the PC's backend? | § 22.2 (`window.location.hostname`) + § 25 (LAN IP). |
| Is the system accessible? | § 22.4, § 22.5, § 23.3 — full ARIA + focus-visible + reduced-motion + keyboard parity. |
| How big is the dependency footprint? | 5 packages, no ML libs. `backend/requirements.txt`. |
| If Sightengine changed their schema, where would you fix it? | `backend/ai_model/model.py`, lines 177-191. One place. |
| What's next for this project? | § 11.2–11.6 |

---

End of document. To read code in execution order, follow § 14 with file tabs open. To read by responsibility, the order is `app.py` → `model.py` → `sightengine_client.py` → `hive_client.py` → `script.js` → `index.html` → `style.css`.
