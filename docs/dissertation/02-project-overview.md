# 2. Project Overview and Objectives

## 2.1 Project statement

**TrueSight** is a self-hosted, local-network web application for the forensic analysis of digital images. Given an uploaded image, it determines whether the image is AI-generated, identifies the most probable generator engine when applicable, detects face-swap deepfake patterns, surfaces local metadata signals, and presents a forensic report alongside a persistent scan history. The implementation pairs two commercial detection APIs (Sightengine and Hive AI) in a cost-aware cascade with on-device forensic checks, wrapped in a Flask backend and a vanilla-JavaScript single-page frontend reachable from any device on the user's Wi-Fi network.

## 2.2 Objectives

1. Classify uploaded images as AI-generated, deepfake, or authentic with a numeric confidence score.
2. Identify the most likely generator engine (Midjourney, DALL·E, Flux, Gemini, GPT-Image, Stable Diffusion, and others) when an image is judged AI.
3. Detect face-swap deepfake patterns in images containing faces.
4. Compute zero-cost on-device forensic signals — EXIF metadata, AI-software tag detection, JPEG compression heuristic.
5. Produce a plain-language forensic report rather than an opaque score.
6. Operate over LAN, accessible from any phone or laptop on the same network without requiring an account.
7. Persist scan history locally in SQLite, with the most recent fifty scans presented in a dedicated view.
8. Provide an automated evaluation framework that produces a confusion matrix and standard classification metrics against a labelled test set.

## 2.3 Out of scope

The following are explicitly **not** project objectives: training a proprietary detection model; authentication or multi-user isolation; HTTPS, rate limiting, or production-grade web serving; adversarial robustness; video analysis; cryptographic provenance (C2PA / Content Credentials) reading.

## 2.4 Project evolution

| Version | What changed | Why |
| --- | --- | --- |
| **1.0** | Five locally-installed PyTorch image classifiers running as an ensemble jury. | Initial proof of concept; heavy dependencies, slow on consumer hardware, outdated as new generators appeared. |
| **1.1** | Replaced the ensemble with Hive AI's V3 Detection API. | Lightweight and fast; gained per-engine attribution; Hive remained sole detection provider. |
| **1.2** | Sightengine becomes primary detector (AI-generation + deepfake in one call); Hive repositioned as a cost-aware secondary lookup invoked only when an image is judged AI. Threshold logic centralised, `logging` adopted, evaluation framework introduced. | Sightengine offers better current-generator coverage and an explicit deepfake head; the cascade saves an estimated 50 percent of Hive quota; centralised thresholds and structured logging are graduation-grade engineering polish. |

Version 1.2 is the system described in this dissertation. The progression illustrates a deliberate trade-off: rather than chase ever-larger local models, the project pivoted to a system-level value-add — orchestration, forensic layering, presentation — built on top of cloud detection that stays current without retraining cycles.
