# 3. Literature Review

> **NOTE TO THE STUDENT**: This chapter requires real comparative research that I (the AI) cannot fabricate. What follows is a structured skeleton with a recommended set of comparator systems, the dimensions on which to compare them, and a guided template for what to write under each. Visit each system's public page or read each paper, jot one or two paragraphs of notes per item, then fill in the table and the per-system subsections below.

This chapter surveys existing systems and academic work that address the problem of identifying AI-generated images. The review covers consumer-grade detection tools (cloud services and websites that anyone can use), industrial detection APIs (used by TrueSight itself), content-provenance initiatives (technical standards for cryptographically signing image origin), and recent academic work on detector robustness.

## 3.1 Consumer-grade detection tools

Six widely-cited consumer tools form the comparison baseline. Each takes an image upload (or URL) and returns a probability or verdict.

### 3.1.1 Hive AI Detector — `https://hivemoderation.com/ai-generated-content-detection`

Suggested write-up points:
- Provider background: Hive Inc. operates content-moderation models for major platforms.
- What you observe on the public demo page: paste their description here.
- Supported generators / engines they claim to detect.
- Account requirement, free-tier limits.
- TrueSight uses Hive's V3 API as its attribution backend — note this dual role.

### 3.1.2 Sightengine — `https://sightengine.com/detect-ai-generated-images`

Suggested write-up points:
- Provider background: Sightengine offers image moderation and authenticity services.
- Their `genai` and `deepfake` models, and how they appear in their playground.
- Free-tier quota (2,000 operations / 500 per day) and pricing tiers.
- TrueSight uses Sightengine as its primary detector — note this is the system being built on.

### 3.1.3 Optic AI or Not — `https://www.aiornot.com`

Suggested write-up points:
- Single-purpose tool for distinguishing AI-generated from real images.
- Verdict format: binary (AI / Not AI).
- Account requirement.
- Whether they explain reasoning or simply present a verdict.

### 3.1.4 Illuminarty — `https://app.illuminarty.ai`

Suggested write-up points:
- Provider background.
- Distinguishing claim: probability heat-maps showing which regions of the image are most likely AI-generated.
- Free tier and rate limits.

### 3.1.5 Microsoft's "About this image" feature in Bing / Copilot

Suggested write-up points:
- Integrated into Microsoft's search products rather than a standalone tool.
- Approach: provenance-based — looks up where the image has been seen before on the web, including any C2PA signatures present.
- Different philosophy: not "is this AI?" but "what is the history of this file?"

### 3.1.6 OpenAI's classifier — discontinued July 2023

Suggested write-up points:
- Worth citing as a cautionary point.
- OpenAI shut down their own AI-image classifier in mid-2023 citing low accuracy.
- The cited reason is itself useful: even the company training the generators admitted detection was hard.

## 3.2 Content-provenance standards

Detection by classification is one approach. Detection by cryptographic provenance — where the generator or camera signs the image at creation — is the alternative being pursued by major industry actors.

### 3.2.1 C2PA (Coalition for Content Provenance and Authenticity)

Suggested write-up points:
- Joint initiative of Adobe, Microsoft, BBC, Intel, Truepic, and others.
- Standard for embedding cryptographically-signed provenance metadata in images.
- Already implemented by Adobe Firefly, OpenAI DALL·E 3, and some Sony / Leica cameras.
- TrueSight does not yet read C2PA — flagged as future work in this dissertation.

### 3.2.2 Adobe Content Credentials

Suggested write-up points:
- Adobe's user-facing implementation of C2PA.
- How it presents provenance to a viewer (the "CR" pin icon).

## 3.3 Academic work on AI-image detection

Suggested write-up points:
- Search Google Scholar for one or two recent (2023–2025) papers on AI-generated image detection.
- Recommended starting queries: "synthetic image detection", "deepfake detection", "diffusion model attribution", "watermarking generative images".
- For each paper you read, note: approach (CNN classifier / frequency-domain features / watermark detection), reported accuracy, dataset, generalisation claims.

## 3.4 Comparative summary

Fill in the following table after gathering notes on each system. Each cell should be a short phrase, not a paragraph.

| System | Detection method | Deepfake support | Generator attribution | Deployment | Privacy posture | Forensic reasoning shown to user | Cost / account required |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Hive Detector | | | | Cloud | | | |
| Sightengine | | | | Cloud | | | |
| Optic AI or Not | | | | Cloud | | | |
| Illuminarty | | | | Cloud | | | |
| Microsoft "About this image" | Provenance lookup | N/A | N/A | Cloud (Bing) | | | |
| OpenAI Classifier (discontinued) | CNN classifier | No | No | Cloud (was) | | None | Free (was) |
| **TrueSight (this project)** | API cascade + local forensic signals | Yes (via Sightengine) | Yes (via Hive cascade) | **Local (LAN)** | **High** — image only leaves device for API calls | **Yes — explicit reasons list** | None (LAN-only) |

## 3.5 How TrueSight differs

After completing the table, write 200–300 words on what TrueSight does that the comparators do not. Suggested framing:

1. **Deployment model.** TrueSight is the only system in the comparison that runs on the user's own machine. Every cloud-based competitor requires uploading the image to a third-party server, often behind an account login. TrueSight uses third-party APIs internally but the user's device, history, and verdicts never leave the local network.

2. **Forensic transparency.** Most cloud tools return an opaque score. TrueSight produces a bullet-point reasoning list that includes the API verdict, the deepfake signal, generator attribution, EXIF metadata flags, JPEG compression disclaimer, and the final verdict label — letting the user weigh the evidence rather than trust a single number.

3. **Multi-provider cascade.** No competitor in the table combines two detection providers. TrueSight uses Sightengine as the primary detector and Hive as a cost-aware secondary lookup for generator attribution — saving quota on real photos where attribution is meaningless.

4. **On-device forensic signals.** Beyond the API verdicts, TrueSight inspects EXIF and JPEG quantization tables on the user's machine, producing signals that cost nothing and are computed even when the API is unreachable.

5. **Persistent local history.** No cloud tool offers a local scan history that survives across sessions without an account.

The literature review concludes that TrueSight occupies an unfilled niche in the comparison space — a *local, multi-provider, forensic-reasoning* detector — rather than competing head-on with any single existing system.

---

> **Reminder**: replace the bracketed write-up suggestions above with your own notes after visiting each system. The references for the systems you cite should be added to chapter 8.
