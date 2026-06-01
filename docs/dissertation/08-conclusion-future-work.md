# 8. Conclusion and Future Work

## 8.1 Conclusion

TrueSight set out to address three constraints common to existing AI-image detection tools: cloud-only deployment that compromises user privacy, account-gated access that obstructs ad-hoc use, and opaque verdicts that leave the user without forensic reasoning. The system delivered against all three. Detection runs over a user's own local-area network; no account is required to use the interface; and every verdict is accompanied by a bullet-point reasons list, per-signal scores, generator attribution where applicable, and on-device forensic signals (EXIF, JPEG compression) that the user can weigh independently.

Quantitatively, the evaluation against a 59-image test set spanning twelve named AI generators yielded an F1 score of 98.7 percent, with 100 percent precision and 97.5 percent recall. The single misclassification occurred on an image that was explicitly curated for exceptional photorealism — an honest upper bound on what automated detection can achieve when generators are optimised to defeat it. The system also satisfies all twenty functional and non-functional requirements documented in Chapter 4, runs on five Python packages with no machine-learning dependencies, and is reachable from any phone or laptop on the same Wi-Fi network without configuration.

The project's value-add is the system around the API calls — the cascade architecture, the local forensic signals, the five-layer input validation stack, the persistent history, the evaluation harness, and the accessibility-first user interface — rather than the classification itself. The version history (v1.0 to v1.1 to v1.2) shows a deliberate engineering progression from local PyTorch models that became outdated within months to a provider-agnostic orchestration layer that can adopt new detection backends as the generator landscape evolves.

## 8.2 Limitations

The following limitations are acknowledged throughout the dissertation and are restated here for completeness:

- **Vendor dependency.** Detection capability is bound to the availability and accuracy of Sightengine and Hive. If either provider degrades or shutters its API, TrueSight degrades with it.
- **No authentication or HTTPS.** The system operates under a LAN-only single-user assumption and is not safe to expose outside the local network.
- **Small test set with class imbalance.** Fifty-nine images is sufficient for a graduation evaluation but produces wide confidence intervals on the false-positive rate.
- **No adversarial-image testing.** The single misclassification hints at an upper bound, but the system has not been deliberately stress-tested against generations engineered to defeat detectors.
- **Sightengine's bimodal score distribution.** The threshold logic is largely insensitive to where the binary cutoff sits because Sightengine clips most outputs to the extremes; finer calibration would require either a different upstream provider or a self-trained model.

## 8.3 Future Work

Concrete next steps, grouped by category and ordered by expected impact within each group.

### Scope expansion — broader content verification

TrueSight currently exposes only two of the many detection models that Sightengine and Hive provide — `genai` and `deepfake`. Both providers offer a much wider catalogue that can be enabled through the same orchestration layer with minimal code change. Surfacing additional models would extend TrueSight from a single-purpose AI-image detector into a general forensic content-verification platform suitable for newsrooms, content moderation teams, and online-safety contexts.

1. **Scam and malicious-content detection.** Sightengine's QR-code model flags codes that resolve to known phishing or scam destinations; combined with text-in-image analysis it can catch fraudulent screenshots circulated on social media. Adding both would let TrueSight verify not only "is this image real?" but "is this image trying to defraud the user?"
2. **Text-in-image (OCR) extraction.** Sightengine's `text-content` model and Hive's text-recognition heads extract printed and handwritten text from an image, surfacing emails, phone numbers, and URLs embedded in the picture. Useful for fact-checking screenshots, identifying watermarks, and detecting overlay text that AI generators frequently render as gibberish.
3. **Watermark detection.** A dedicated model that identifies post-processing watermarks added by stock-photo agencies, AI-tool branding, or social-media overlays. A confirmed watermark from a reputable agency is a strong real-photo signal; a confirmed AI-tool watermark is dispositive in the opposite direction.
4. **Safety and moderation models.** Both providers expose nudity, violence, gore, weapons, drugs, hate-symbol, and self-harm classifiers. Surfacing these alongside the current AI/deepfake signals would make TrueSight usable as a triage tool for user-generated-content platforms, not only as an authenticity checker.
5. **Image quality and type classification.** Sightengine's `quality` model scores technical and aesthetic quality, and its `type` model distinguishes photographs from illustrations. Both signals qualify the AI-detection verdict — a low-quality screenshot of an illustration is a different forensic case from a high-resolution photograph, and the report should reflect that.
6. **Face analysis.** Sightengine and Hive both detect faces, count them, estimate ages, and flag the presence of minors. Counting faces is useful for journalism (verifying the number of subjects in a contested image); minor-detection is a hard-floor moderation signal.

Each item above follows the same architectural pattern already established in `model.py`: enable one additional Sightengine model name in the `/check.json` call, add a parser for its response field, surface the result as a new signal in the verdict dictionary, and add a reason-text bullet driven by a configurable threshold. The cost is one additional Sightengine operation per scan per model enabled — a manageable trade-off against an enterprise plan or a switched-on pay-per-scan tier.

### Functional extensions

7. **C2PA / Content Credentials reading.** Major AI tools (Adobe Firefly, DALL·E 3) and cameras (Sony α1, Leica) now embed cryptographically-signed provenance manifests in image metadata. Reading these locally would let TrueSight surface authenticated provenance without any API call — a higher-confidence signal than any classifier.
8. **Per-generator attribution from Sightengine directly.** Sales engagement has been initiated to enable the `ai_generators` sub-block on the project's Sightengine plan. Once available, the Hive cascade becomes optional, simplifying the architecture and reducing per-scan operational cost.
9. **Adversarial-aware evaluation.** Curate a targeted set of images deliberately optimised to fool detectors and report performance separately. This would set an honest lower bound on real-world reliability.

### Engineering polish

10. **SHA-256 deduplication cache.** Hash every upload before calling the APIs and return cached verdicts on repeated scans. Eliminates wasted API quota on duplicate inputs during development and frequent re-checks.
11. **Latency measurement.** Add per-image timing to the evaluation harness and report mean and 95th-percentile latency alongside accuracy metrics.
12. **Wilson confidence intervals on reported metrics.** With fifty-nine samples the 95 percent confidence interval on a zero-false-positive rate spans roughly zero to eighteen percent. Reporting this explicitly would strengthen the evaluation's honesty without changing the underlying numbers.

### Alternative architectures

13. **Bayesian fusion of providers.** An experimental branch (`hive-sighteng`) implements parallel calls to both detection providers with a Naive Bayes combination of the scores and an explicit disagreement gate. A comparative evaluation of fusion versus the current cascade design would clarify when each architecture is preferred.
14. **Provider portfolio expansion.** Adding Optic, Illuminarty, or a future open-source detector behind the same client-module interface would reduce vendor risk and enable consensus voting on contested verdicts.

### Deployment

15. **Authentication, HTTPS, and rate limiting** for any non-LAN deployment, behind a production WSGI host (Gunicorn) and a reverse proxy (nginx).
16. **Mobile native packaging.** The current web interface is already responsive and usable on mobile (see Section 7.4.8), but a thin native shell — Progressive Web App installation, or a React Native wrapper — would improve discoverability and integration with the phone's share menu, enabling one-tap analysis of images received in messaging applications.
