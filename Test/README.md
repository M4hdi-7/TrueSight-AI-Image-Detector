# Test image set

Manual sample set used to exercise the detection pipeline end-to-end. There is no automated test harness — these are images for ad-hoc verification through the UI or via `backend/verify_sightengine.py`.

## Ground truth

Fill in the **Verified** column once you've confirmed each image's true origin. The "Expected" column reflects what the filename or visual context suggests, but examiners should not trust filenames as ground truth.

| File | Expected | Verified | Notes |
| --- | --- | --- | --- |
| `Dwayne_Johnson_2014_(cropped).jpg` | Real | ☐ | Wikipedia portrait, cropped |
| `87500673_7cec21f38a_b.jpg` | Real | ☐ | Flickr photograph |
| `photo-1529778873920-4da4926a72c2.jpg` | Real | ☐ | Unsplash stock photo |
| `summer-landscape-with-river.jpg` | Real | ☐ | Stock landscape |
| `istockphoto-1289220723-612x612.jpg` | Real | ☐ | iStockphoto |
| `merlin_215187303_80e12403-9968-4f28-a197-7323c73613a5-articleLarge.webp` | Real | ☐ | News photo |
| `VIER PFOTEN_2025-02-18_00108-2736x1824-2286x1582-1920x1329.jpg` | Real | ☐ | Press / charity image |
| `images.jpg` | Unknown | ☐ | Small/unlabeled — useful for boundary case |
| `Midjourney-for-Beginners-AI-Art-by-Sprinkle-of-AI-4-XL-683x1024.jpg` | AI (Midjourney) | ☐ | Tutorial sample |
| `dalle3-examples-with-fairly-long-and-specific-prompts-v0-dfh0d75h94rb1.jpg` | AI (DALL·E 3) | ☐ | Reddit DALL·E 3 sample |
| `Gemini_Generated_Image_.png` | AI (Imagen / Gemini) | ☐ | Default filename from Gemini |
| `ai-generated-8794203_1280.png` | AI | ☐ | Pixabay AI sample |
| `paris-garbage-viral-ai-images.jpg` | AI | ☐ | Viral AI hoax image |
| `trump-arrested-viral-ai-images.jpeg` | AI | ☐ | Viral AI hoax image |
| `this-is-what-ai-can-do-v0-pdrpiafl88vc1.jpg` | AI | ☐ | Reddit AI sample |
| `1_zEXe2G5Rc2b6Wowb6_Av9A.jpg` | Unknown | ☐ | Filename uninformative |
| `08-1040097-686c64f5eea40.png` | Unknown | ☐ | Filename uninformative |
| `179ba040-7560-11ef-90f9-fd554410d16e.png` | Unknown | ☐ | Filename uninformative |
| `18-1077418-69438ec474f13.png` | Unknown | ☐ | Filename uninformative |
| `18-1077430-694392f34ef7d.png` | Unknown | ☐ | Filename uninformative |
| `28-1075179-69296af0aab06.png` | Unknown | ☐ | Filename uninformative |

## How to use

**For automated evaluation:** Run `backend/evaluate.py`. It parses this file's "Expected" column to get ground-truth labels (only rows starting with `Real` or `AI` are used — `Unknown` rows are skipped) and produces a confusion matrix plus a Markdown report at `evaluation_report.md`.

**For manual inspection:**

1. Start the app (`.\start.bat`) and upload each image through the UI.
2. Record TrueSight's verdict (label + score) and compare against the verified ground truth.
3. Edge cases worth documenting in the report:
   - Heavy JPEG compression (TrueSight should flag this in the reasons list).
   - EXIF software tag containing a known AI tool name (should be flagged in metadata reasons).
   - Real photos with no EXIF (should not be auto-flagged as AI just because EXIF is absent).
   - AI images where Sightengine and Hive disagree about the source engine.

## Size constraint

The detection pipeline rejects anything over 12 MB or 64 megapixels. Test images that exceed these limits should produce a clean "Image is too large" error rather than a crash — that's part of the contract worth verifying.
