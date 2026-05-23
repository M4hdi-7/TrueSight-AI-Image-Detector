# 3. Literature Review

This chapter surveys existing systems that attempt to answer "is this image AI-generated?" — both consumer-grade detection tools and the emerging cryptographic-provenance standards. The goal is to position TrueSight in the comparison space and to identify the gap it occupies.

## 3.1 Detection-based tools

### 3.1.1 Hive AI Moderation

Hive Inc. (founded 2017) operates large-scale content-moderation models used by Reddit, OpenAI's ChatGPT moderation pipeline, and several social platforms. Its public AI-image detector at `hivemoderation.com/ai-generated-content-detection` returns a probability that the image was AI-generated together with per-engine classification (which model generated it). Hive's V3 detection API — the one TrueSight uses as its attribution backend — exposes named heads for over a dozen generators including Midjourney, DALL·E, Flux, Stable Diffusion, GPT-Image, Gemini, Kling, Krea, Ideogram, and Grok. Hive's strength is the breadth and currency of its engine catalogue; its weakness is that it is closed-source and cloud-only, and the public demo requires account registration.

### 3.1.2 Sightengine

Sightengine is a French content-moderation API provider that offers, among many models, a `genai` model (AI-generation probability) and a `deepfake` model (face-swap probability). Both can be requested in a single `/check.json` call. The free tier allows 2,000 operations per month with a 500-per-day cap; the documentation publishes the exact per-model operation cost. Sightengine's strength is the bundled deepfake head and a clean REST API; its weakness, observed empirically during this project, is that the `ai_generators` sub-block returning per-engine attribution is not enabled on standard plans and is gated behind a "contact us" enterprise tier. TrueSight uses Sightengine as its primary detector.

### 3.1.3 Optic AI or Not

Available at `aiornot.com`, Optic offers a single-purpose binary classifier — "AI" or "Not AI" — with a confidence score. The tool is free with an account, processes uploaded images one at a time, and does not surface per-engine attribution or auxiliary forensic signals. Optic's strength is its single-page simplicity; its weakness is the lack of reasoning beyond the binary output.

### 3.1.4 Illuminarty

Available at `app.illuminarty.ai`, Illuminarty differentiates itself by producing a probability heat-map highlighting which regions of the image are most likely AI-generated. This is qualitatively different from a single global score and supports localised tampering analysis. The free tier has rate limits. Illuminarty's strength is the regional view; its weakness is that it lacks an explicit deepfake head and offers less generator-attribution detail than Hive.

### 3.1.5 Microsoft "About this image"

Integrated into Bing Search and Copilot since late 2023, "About this image" is *provenance-based* rather than classification-based. When the user invokes it, the system performs a reverse-image search across indexed pages, returns the earliest dates and locations the image has appeared, and surfaces any embedded C2PA content credentials. This is not "is this AI?" but "what is the history of this file?" The strength is that provenance evidence is more durable than classifier confidence — a real photo with documented Reuters provenance is genuinely real. The weakness is that the system fails silently for new images, images that have been re-encoded since their original publication, or images that have never been crawled.

### 3.1.6 OpenAI's discontinued classifier

OpenAI launched a public AI-text classifier in January 2023 and discontinued it on 20 July 2023, citing low accuracy in detecting AI-generated text. The discontinuation is itself a useful citation: the company that trained the leading generators publicly admitted that detection through classification was not reliable enough to deploy. Although OpenAI's image-generation product (DALL·E) embeds content credentials in its outputs, OpenAI does not currently offer a public AI-image classifier.

## 3.2 Provenance-based standards

### 3.2.1 C2PA — Coalition for Content Provenance and Authenticity

Founded in 2021 by Adobe, Microsoft, BBC, Intel, Truepic, and others, C2PA is the industry standard for cryptographically signing image provenance at creation time. A camera or generative model that supports C2PA writes a signed manifest into the image's metadata describing how the image was produced, what was done to it, and by whom. The signature can be verified anywhere the public-key infrastructure is reachable. As of 2025 the standard is implemented natively by Adobe Firefly, OpenAI DALL·E 3, and several Sony and Leica camera bodies. Its strength is that it makes provenance verifiable without classification at all; its limitation is that an image stripped of metadata loses every C2PA assertion, so the standard protects authenticated images but does not classify unauthenticated ones.

### 3.2.2 Adobe Content Credentials

Content Credentials is Adobe's user-facing implementation of C2PA. The "CR" pin icon appears on supported images on supporting platforms (currently Behance, LinkedIn, and Adobe's own products), letting a viewer click through to inspect the provenance chain. Content Credentials is the most visible deployment of C2PA outside the specification itself.

## 3.3 Academic foundations

Three lines of academic work inform the broader field. The first is **classification of synthetic images by CNN artefacts** — Wang, Wang, Owens and Efros's 2020 CVPR paper "CNN-generated images are surprisingly easy to spot... for now" demonstrated that early GAN outputs had distinctive frequency-domain artefacts that classifiers could exploit; subsequent diffusion models are harder to detect with the same techniques. The second is **deepfake detection surveys** — Mirsky and Lee's 2021 ACM Computing Surveys article "The Creation and Detection of Deepfakes" is the standard reference for the face-swap detection problem. The third is **the calibration and generalisation gap** — multiple recent papers have shown that detectors trained on one generator's outputs do not generalise to the next generation of generators, which is the underlying reason behind both Sightengine's near-binary score distribution observed in this project's evaluation and Hive's need to continually expand its engine catalogue.

## 3.4 Comparative summary

| System | Method | Deepfake | Engine attribution | Deployment | Privacy | Reasoning shown | Account needed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Hive AI Moderation | CNN classifier (multi-head) | Yes | Yes (12+ engines) | Cloud | Image uploaded to Hive servers | Single score per head | Yes |
| Sightengine | Classifier API | Yes (separate `deepfake` model) | Plan-gated (enterprise tier only) | Cloud | Image uploaded to Sightengine | Single score per model | Yes (API key) |
| Optic AI or Not | Classifier | No | No | Cloud | Image uploaded | Binary verdict | Yes |
| Illuminarty | Region-localised classifier | Indirect via region map | Limited | Cloud | Image uploaded | Heat-map | Yes |
| Microsoft "About this image" | Reverse search + C2PA | No (provenance-based) | Indirect via origin | Cloud (Bing) | Image fingerprinted, not stored | Provenance trail | No (Bing account optional) |
| OpenAI Image Classifier | (discontinued July 2023) | — | — | — | — | — | — |
| C2PA / Content Credentials | Cryptographic signing at source | N/A | N/A | Embedded in file | Local (no upload required) | Provenance manifest | No |
| **TrueSight (this work)** | **API cascade + local forensic signals** | **Yes (Sightengine)** | **Yes (Hive cascade)** | **Local (LAN)** | **High — image only leaves device for the API call** | **Bullet-point reasons list** | **No (LAN-only)** |

## 3.5 Where TrueSight differs

The comparison shows that no existing tool combines all of the following: local deployment, on-device forensic signals (EXIF, JPEG quantization), multi-provider cascade for cost-aware attribution, persistent local history, and a transparent reasoning list rather than an opaque score. Each cloud competitor sacrifices privacy by requiring upload to a third-party server, sacrifices transparency by returning a single number, or sacrifices currency by relying on a single classifier head whose engine catalogue lags the generator landscape. Each provenance-based tool sacrifices coverage by failing to classify images that lack C2PA credentials, which is almost everything in the wild.

TrueSight occupies the unfilled niche: a *local, multi-provider, forensic-reasoning* detector. It does not claim a novel classification algorithm — the classifiers are Sightengine's and Hive's — but it integrates two third-party detectors with on-device signals in a configuration that no comparator offers.
