# Anticipated viva questions and prepared answers

A practice document. The questions are organised by likelihood and severity. Tier 1 must be rehearsed out loud; Tiers 2–3 should be skimmed so the vocabulary is familiar.

---

## Tier 1 — must be prepared

These are the questions a competent examiner is most likely to use to probe whether the project has substance.

### Q1. "Isn't this just a wrapper around someone else's API?"

The single most dangerous question. Answer it confidently and specifically.

> *"The AI classification itself is provided by Sightengine and Hive — I'm not claiming I trained a detector. My contribution is the system around that classification. Specifically: (1) a cost-aware **cascade architecture** that calls Hive only when Sightengine flags AI, saving roughly half the attribution-call quota; (2) **local forensic signals** — EXIF metadata inspection and JPEG quantization analysis — computed with zero API cost; (3) a **five-layer input validation stack** including magic-byte verification, dimension caps, and UUID rename; (4) an **evaluation harness** with resume-capable runs that produces confusion matrices, precision/recall/F1, and auto-generated failure analysis; (5) full-stack integration — LAN-accessible web UI, persistent SQLite history, accessibility-first design with ARIA and focus management. The detector is bought; the system is built."*

---

### Q2. "Your detector got 100% precision. Is that real?"

This is a probe of whether you understand the calibration of your own results.

> *"You're right that Sightengine's output is bimodal — most images come back at the extreme ends of the 0–100 range. In our 59-image evaluation, 38 of 40 AI images scored exactly 99.0% and 18 of 19 real images scored 0.1%. This means the binary classification result is largely insensitive to where I place the 50% threshold. The 100% precision figure reflects Sightengine's calibration on this test set, not a property I can claim to have engineered. The single misclassification was a Reddit image specifically curated for its photorealism, which I take as an upper-bound signal on what automated detection can achieve. Real-world deployment, with illustrations, paintings, and screenshots, would almost certainly produce more false positives."*

---

### Q3. "Why didn't you train your own model?"

Standard attack on API-driven projects. Have a confident, principled answer.

> *"Training a competitive AI-detection model requires labelled examples spanning current generators — Midjourney v8, Gemini 3, Flux, GPT-Image — which evolve faster than any retraining cycle a student could maintain. A self-trained model would lag behind the threat model by months. Using external detection APIs lets the system stay current with the generator landscape without retraining. The trade-off — vendor dependency — is acknowledged in the limitations section, and the architecture is provider-agnostic: `model.py` orchestrates, and both API clients are swappable. Earlier versions of this project did use local models, as documented in `CHANGELOG.md` — v1.0 ran a 5-model PyTorch jury that was rejected for being too slow and quickly outdated. The shift to APIs was an informed engineering decision."*

---

### Q4. "What's your false-positive rate in real-world deployment?"

Probing whether you understand the gap between evaluation and deployment.

> *"On the test set: zero in nineteen real images. With Wilson's 95% confidence interval that translates to a true false-positive rate somewhere between 0% and 18%. In real-world deployment I would expect false positives on illustrations, paintings, AI-style retouched real photos, screenshots, heavily compressed photos, and adversarial inputs designed to fool detectors. The 0% headline is best-case; a more robust evaluation would require a larger and more diverse real-image set, which was constrained here by Sightengine's free-tier daily quota of 500 operations."*

---

## Tier 2 — likely traps

These are the small, specific technical questions designed to test whether you've actually read your own code.

### Q5. "Why these specific thresholds?"

Trick question — there are **two different thresholds**. Clarify first.

> *"Which thresholds — the binary classification cutoff at 50%, or the five-bucket UI verdict labels at 85/60/45/20?"*

That single move shows you understand the architecture and buys five seconds.

**For the binary 50% threshold:**
> *"50% is the natural cutoff for a probability score and matches Sightengine's documented convention for treating scores above 0.5 as positive. It also drives the cascade decision — only images at or above 50% trigger the Hive attribution call."*

**For the verbose labels (85/60/45/20):**
> *"These are heuristic UI thresholds giving the user five gradations of verdict confidence — AI Generated, Likely AI Generated, Suspicious / Inconclusive, Likely Real, Real Photo. They're chosen empirically against the bimodal score distribution observed in evaluation, but I did not perform a rigorous sensitivity analysis. They could be tuned with more data."*

Honest beats fake-calibrated.

---

### Q6. "What's your train/test split?"

Trick question — there is no training.

> *"TrueSight does no model training. It orchestrates external detection APIs and computes local forensic signals. The `Test/` directory is purely an evaluation set, not training data. There's no risk of train-test contamination because no training occurs."*

---

### Q7. "Why is the deepfake score sometimes 96% on a clearly-AI image rather than a face-swap?"

Eagle-eyed examiner who actually read the evaluation report.

> *"Good observation. Sightengine's deepfake head appears to treat synthetically-generated faces as deepfake-adjacent, not just real-faces-swapped-onto-real-images. In our evaluation, AI-generated portraits with prominent faces — `sy95ysyxu0af1.png`, `this-is-what-ai-can-do-...` — triggered both the genai head (99%) and the deepfake head (96%). My interpretation is that 'deepfake' for Sightengine includes 'face was synthetically constructed', not strictly 'face was swapped'. I noted this observation in the evaluation report."*

---

### Q8. "Why no authentication?"

Documented in the limitations section but they'll still ask.

> *"TrueSight is designed for LAN-only deployment. Anyone on the same Wi-Fi can call any endpoint, including `/clear_history`. This is intentional for a local forensics tool and explicitly out of scope for the project. Production deployment would require authentication, HTTPS, rate-limiting, restricted CORS, and a real WSGI host replacing Flask's dev server — these are listed in the future-work section."*

---

### Q9. "What about adversarial images?"

> *"Out of scope for this project, acknowledged in future work. The single misclassification in our evaluation — the Reddit 'this AI looks incredibly real' image — is an honest example of what happens when generative AI is specifically optimised to fool perception. A more robust system would need adversarial-aware training, which both Sightengine and Hive presumably perform, but is opaque to me as a consumer of their API."*

---

### Q10. "What's the latency per scan?"

If you didn't measure this, admit it. They'll respect honesty more than waffle.

> *"I did not formally measure end-to-end latency, but observationally each Sightengine call takes 5–10 seconds, and the Hive cascade adds another 5–10 seconds on AI-flagged images. The 60-second timeout in the clients is a safety ceiling, not the operating norm. A more thorough evaluation would log per-image latency — this is a real gap and could be added trivially."*

---

## Tier 3 — lower-probability technical questions

### Q11. "What happens if Sightengine returns malformed JSON?"

> *"The clients `try/except` around the `.json()` call and propagate the exception. `predict_image` catches all exceptions and returns a synthetic 'Error' verdict with a user-readable reason. The frontend displays this without crashing. No malformed-response path leaves the user staring at a 500 page."*

### Q12. "How are you preventing path traversal attacks on uploads?"

> *"Three layers. First, `werkzeug.utils.secure_filename` strips path separators and normalises the name. Second, the saved filename is replaced with a UUID, so even a benign uploaded name cannot be referenced by a subsequent request. Third, `send_from_directory` enforces that requested paths stay inside the uploads folder."*

### Q13. "Why JPEG quantization analysis specifically?"

> *"It's a near-zero-cost local signal that identifies heavily-compressed images. Heavy compression destroys the pixel-level artifacts that AI detectors rely on, so the verdict on a heavily-compressed image deserves a 'less reliable' disclaimer. The check reads PIL's `img.quantization` table, averages the 64 luma values, and flags anything above 25 — which corresponds roughly to JPEG quality 50 or worse. It does not change the verdict; it adds a caveat to the report."*

### Q14. "What does `secure_filename` actually do?"

Be ready to demonstrate you know the library you depend on.

> *"It removes path separators, replaces spaces with underscores, removes non-ASCII characters, and ensures the result is a safe filename on POSIX and Windows filesystems. For our defence in depth I also UUID-rename the file after `secure_filename` has run, so the original name is never persisted to disk."*

### Q15. "Why CORS open?"

> *"`CORS(app)` with no arguments allows any origin. This is correct for LAN-only deployment where the frontend on port 8000 talks to the backend on port 5000 from any device on the network. For production it should be restricted to known origins — listed in the limitations section."*

### Q16. "Why SQLite and not Postgres?"

> *"SQLite is the right tool for a single-machine, single-user-at-a-time application. There are no concurrent-writer concerns, no replication needs, and no operational overhead. The schema is one table. Postgres would be over-engineering and would introduce a dependency the project explicitly avoids. If multi-user deployment ever became a requirement, the schema is portable."*

### Q17. "Why are uploads cacheable but API responses not?"

> *"Uploads have immutable UUID filenames, so the browser can cache them indefinitely. API responses (like `/history` or `/predict`) reflect mutable application state — forcing `no-store` prevents the UI from showing stale data after a re-scan or clear. The split is enforced in the `add_header` hook."*

### Q18. "What's the total dependency footprint?"

> *"Five Python packages: Flask, flask-cors, Pillow, requests, python-dotenv. All pinned in `requirements.txt`. No machine-learning libraries (no torch, no transformers, no ONNX). That's deliberate — the v1.1 migration explicitly dropped ML deps."*

---

## Vocabulary cheat-sheet

If the examiner uses a term and you blank, use this list to anchor what they mean.

| Term | One-line meaning |
| --- | --- |
| Precision | When my detector says AI, how often is it right? |
| Recall | What fraction of all AI images does my detector catch? |
| F1 | Harmonic mean of precision and recall — single number that's robust to class imbalance |
| Confusion matrix | 2×2 table: predicted vs actual, with cells TP, TN, FP, FN |
| Class imbalance | When one class is much more common in the test set than the other |
| False positive (FP) | Said AI, was actually real |
| False negative (FN) | Said real, was actually AI |
| Cascade | One model gates the call to a second model — used here for cost optimisation |
| Bayesian fusion | Naive Bayes combination of two independent probabilities — the formula in the alternative `hive-sighteng` branch |
| Magic-byte check | Reading the first bytes of a file to verify the actual format matches the claimed extension |
| EXIF | Exchangeable Image File Format — metadata embedded in image files by cameras |
| C2PA | Coalition for Content Provenance and Authenticity — emerging standard for content credentials |
| Bimodal | A distribution with two peaks — Sightengine's scores cluster at the 0% and 99% extremes |
| CORS | Cross-Origin Resource Sharing — controls which origins can call an API |

---

## Things to mention proactively if the conversation drifts

Use these to recover the narrative if the examiner is dwelling on weaknesses.

- **"The Sightengine sales team is currently reviewing my request for per-generator attribution access."** Shows you're not just consuming an API — you've engaged with the vendor and identified a real gap.
- **"The earlier version of this project ran five local ML models — I moved away from that intentionally."** Shows iteration, not lack of ML capability.
- **"There's an alternative architecture branch — `hive-sighteng` — that explores Bayesian fusion of the two providers' verdicts."** Shows you considered alternatives.
- **"`evaluate.py` resumes from cached results, so each evaluation run only re-scans images that previously errored."** Shows engineering polish on the evaluation infrastructure itself.
- **"The system surfaces 12 distinct generator engines through Hive — including current state-of-the-art like GPT-Image v2, Gemini 3, Z-Image, and Flux."** Shows the project is current.

---

## Honest weaknesses (acknowledge before being attacked)

Pre-empting these in your dissertation methodology section disarms most of the criticism.

1. **Sample size of 59 is small.** State 95% confidence intervals on your metrics.
2. **Class imbalance (68/32) inflates accuracy.** That's why F1, not accuracy, is the headline number.
3. **No latency measurements.** State the qualitative observation and flag as future work.
4. **No baseline comparison.** "What if I used Sightengine alone? Hive alone?" — would strengthen the cascade argument but wasn't measured.
5. **No adversarial-image testing.** Listed in future work.
6. **Heavy dependency on external services.** Mitigation: provider-agnostic architecture.
7. **Test set is convenience-sampled, not random.** Sourced from places where the ground-truth labels could be verified (Unsplash photographers, Reddit AI subreddits) — not a representative sample of "all images on the internet."

Saying these *first* takes them off the examiner's question list.
