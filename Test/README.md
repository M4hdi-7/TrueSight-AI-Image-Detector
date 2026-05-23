# Test image set

Manual sample set used to evaluate the detection pipeline. There is no automated unit-test harness — these are images for ad-hoc verification through the UI and (more importantly) for the automated evaluation in `backend/evaluate.py`.

## How to use

**For automated evaluation:** Run `backend/evaluate.py`. It parses the "Expected" column below to get ground-truth labels (only rows starting with `Real` or `AI` are used — `Unknown` rows are skipped) and produces a confusion matrix plus a Markdown report at `evaluation_report.md`.

**For manual inspection:** Start the app (`.\start.bat`) and upload each image through the UI; record the verdict and compare against the verified ground truth.

The **Verified** column is a visual checkbox for your own tracking (☐ → ☑ once you've opened the image and confirmed its true origin). The script ignores it.

## Sample composition (current set)

| Category | Count |
| --- | --- |
| Real photographs (verified source) | 14 |
| AI-generated (explicit in filename / source) | 24 |
| Unknown / needs verification | 21 |
| **Total** | **59** |

## Real photographs

Sources verified via filename conventions: Unsplash (photographer slug), iStockphoto, Wikipedia, NYT (`merlin_` CMS prefix), NASA Hubble, Flickr, Four Paws press releases.

| File | Expected | Verified | Notes |
| --- | --- | --- | --- |
| `Dwayne_Johnson_2014_(cropped).jpg` | Real | ☐ | Wikipedia portrait, cropped |
| `Elon_Musk_(54816836217)_(cropped_2)_(b).jpg` | Real | ☐ | Wikipedia portrait (Flickr-sourced) |
| `87500673_7cec21f38a_b.jpg` | Real | ☐ | Flickr photograph (_b = "big" size) |
| `photo-1529778873920-4da4926a72c2.jpg` | Real | ☐ | Unsplash (hash-format URL slug) |
| `alvan-nee-zhnfJmfeNG0-unsplash.jpg` | Real | ☐ | Unsplash — photographer Alvan Nee |
| `cedric-letsch-Racqz_gECu4-unsplash.jpg` | Real | ☐ | Unsplash — photographer Cedric Letsch |
| `ilke-yazgan-a8b6zP1wEDQ-unsplash.jpg` | Real | ☐ | Unsplash — photographer İlke Yazgan |
| `kevin-mueller-5z4GbvfNbSw-unsplash.jpg` | Real | ☐ | Unsplash — photographer Kevin Mueller |
| `tobias-reich-lAOr626zEbM-unsplash.jpg` | Real | ☐ | Unsplash — photographer Tobias Reich |
| `hubble-ngc1266-2-4f-flat-final-crop2.jpg` | Real | ☐ | NASA Hubble — galaxy NGC 1266 |
| `merlin_215187303_80e12403-9968-4f28-a197-7323c73613a5-articleLarge.webp` | AI | ☐ | New York Times CMS asset (`merlin_` prefix) |
| `VIER PFOTEN_2025-02-18_00108-2736x1824-2286x1582-1920x1329.jpg` | Real | ☐ | Press image from Four Paws (Vier Pfoten) animal welfare org |
| `istockphoto-1289220723-612x612.jpg` | Real | ☐ | iStockphoto stock image |
| `summer-landscape-with-river.jpg` | Real | ☐ | Stock landscape photograph |

## AI-generated images

Origin identifiable from filename — explicit AI tool name, Reddit "v0" preview-hash format from AI-art subreddits, or known viral-hoax filenames.

| File | Expected | Verified | Notes |
| --- | --- | --- | --- |
| `ChatGPT Image May 20, 2026, 12_22_08 AM.png` | AI (ChatGPT) | ☐ | Default save name from ChatGPT image generation |
| `Gemini_Generated_Image_.png` | AI (Gemini / Imagen) | ☐ | Default Gemini output |
| `Gemini_Generated_Image_ (1).png` | AI (Gemini / Imagen) | ☐ | Default Gemini output |
| `Gemini_Generated_Image_ (2).png` | AI (Gemini / Imagen) | ☐ | Default Gemini output |
| `Gemini_Generated_Image_ (3).png` | AI (Gemini / Imagen) | ☐ | Default Gemini output |
| `Gemini_Generated_Image_ (4).png` | AI (Gemini / Imagen) | ☐ | Default Gemini output |
| `Gemini_Generated_Image_ (5).png` | AI (Gemini / Imagen) | ☐ | Default Gemini output |
| `Gemini_Generated_Image_ (7).png` | AI (Gemini / Imagen) | ☐ | Default Gemini output |
| `Gemini_Generated_Image_e0gm19e0gm19e0gm.png` | AI (Gemini / Imagen) | ☐ | Default Gemini output (hash variant) |
| `Gemini_Generated_Image_vx7ookvx7ookvx7o.png` | AI (Gemini / Imagen) | ☐ | Default Gemini output (hash variant) |
| `Gemini_Generated_Image_wbdy6wwbdy6wwbdy.png` | AI (Gemini / Imagen) | ☐ | Default Gemini output (hash variant) |
| `Midjourney-for-Beginners-AI-Art-by-Sprinkle-of-AI-4-XL-683x1024.jpg` | AI (Midjourney) | ☐ | Sprinkle of AI tutorial sample |
| `mjv7-vs-mjv8-1-v0-872pf5hhks2h1.webp` | AI (Midjourney v7/v8) | ☐ | Reddit r/midjourney comparison post |
| `mjv7-vs-mjv8-1-v0-ujxjftfdks2h1.webp` | AI (Midjourney v7/v8) | ☐ | Reddit r/midjourney comparison post |
| `dalle3-examples-with-fairly-long-and-specific-prompts-v0-dfh0d75h94rb1.jpg` | AI (DALL·E 3) | ☐ | Reddit DALL·E 3 sample |
| `z-image-turbo-finetune-of-absurd-reality-v0-xi75jnfriuwg1.webp` | AI (Z-Image Turbo finetune) | ☐ | Reddit AI-art post |
| `ai-generated-8794203_1280.png` | AI | ☐ | Stock site (Pixabay) — explicitly labelled AI |
| `paris-garbage-viral-ai-images.jpg` | AI | ☐ | Known viral AI hoax — Paris flooded with garbage |
| `trump-arrested-viral-ai-images.jpeg` | AI | ☐ | Known viral AI hoax — fake Trump arrest, March 2023 |
| `this-is-what-ai-can-do-v0-pdrpiafl88vc1.jpg` | AI | ☐ | Reddit AI showcase post |
| `its-still-nuts-to-me-how-realistic-ai-is-getting-incredible-v0-bcxd5awmq50h1.webp` | AI | ☐ | Reddit AI realism showcase |
| `its-still-nuts-to-me-how-realistic-ai-is-getting-incredible-v0-jaac6rreq50h1.webp` | AI | ☐ | Reddit AI realism showcase |
| `large-built-muscular-young-ohio-dude-enjoys-a-quiet-v0-g24cqopw5e2h1.webp` | AI | ☐ | Reddit AI post (v0 hash + AI-art context) |
| `large-built-muscular-young-ohio-dude-enjoys-a-quiet-v0-ggn2xukt5e2h1.webp` | AI | ☐ | Reddit AI post (v0 hash + AI-art context) |

## Unknown / needs verification

Filenames are uninformative — random hashes, Reddit preview IDs, generic camera names. Open each one and decide manually. Change `Unknown` to `Real` or `AI (source)` to include it in the evaluation.

| File | Expected | Verified | Notes |
| --- | --- | --- | --- |
| `08-1040097-686c64f5eea40.png` | AI | ☐ | Hash-only filename |
| `179ba040-7560-11ef-90f9-fd554410d16e.png` | AI | ☐ | UUID-format filename |
| `18-1077418-69438ec474f13.png` | AI | ☐ | Hash-only filename |
| `18-1077430-694392f34ef7d.png` | AI | ☐ | Hash-only filename |
| `1_zEXe2G5Rc2b6Wowb6_Av9A.jpg` | AI | ☐ | Hash-only filename |
| `1jbj5sp3np9f1.png` | AI | ☐ | Reddit preview-hash format |
| `28-1075179-69296af0aab06.png` | AI | ☐ | Hash-only filename |
| `360_F_260350247_eGO8MWYwjIpml40GRWmIZ7tOs2G3iQtD.jpg` | REAL | ☐ | Adobe Stock format — Adobe Stock now mixes real and AI |
| `361af094c8d26cc553cffa1e8ad66506.jpg` | REAL | ☐ | Hash-only filename |
| `6qomj007hrqg1.jpeg` | AI | ☐ | Reddit preview-hash format |
| `agp58awbip1g1.jpeg` | AI | ☐ | Reddit preview-hash format |
| `ikscie9x2dkf1.png` | AI | ☐ | Reddit preview-hash format |
| `l8yp0vlah2pf1.jpeg` | AI | ☐ | Reddit preview-hash format |
| `sy95ysyxu0af1.png` | AI | ☐ | Reddit preview-hash format |
| `images.jpg` | REAL | ☐ | Generic Google Images default save name |
| `IMG_6280.png` | AI | ☐ | iPhone-style filename — could be photo or screenshot |
| `F041_rt_feature.jpg` | REAL | ☐ | Source unidentified |
| `SEI_217242335.webp` | AI | ☐ | Source unidentified |
| `WhatsApp Image 2026-05-20 at 9.36.39 PM (2).jpeg` | AI | ☐ | Forwarded WhatsApp image — origin lost |
| `magic-of-play.jpg` | REAL | ☐ | Looks like a blog/stock title — needs visual check |
| `boy-jumping-in-puddle-scaled.jpg` | REAL | ☐ | Stock-photo-style title — needs visual check |

## How to spot AI in an "Unknown" image (60-second checklist)

If you're unsure, open the image and look for these tells:

- **Hands** — wrong finger count, fused or melting fingers.
- **Text** — letters/numbers in the image are usually gibberish in AI output.
- **Eyes & teeth** — pupils not aligned, teeth too uniform or "melting."
- **Symmetry** — earrings, glasses, or buttons that don't match across left/right.
- **Backgrounds** — shadows in physically impossible directions, walls/lines that bend.
- **Skin** — suspiciously poreless and airbrush-smooth on adults.

If none of those are obvious and the photo feels like a real moment (uneven lighting, candid framing, motion blur, EXIF mentioning a real camera) → call it **Real**. Otherwise leave it **Unknown** — better to skip than mislabel.

## Edge cases worth documenting in the dissertation

When you run `evaluate.py` and review the failures, the following classes of edge case tend to be the most instructive:

- Heavily compressed JPEGs — TrueSight should flag the compression disclaimer.
- Real photos stripped of EXIF (social-media style) — should not be auto-flagged AI just because EXIF is missing.
- AI images that have been re-saved through a phone or social media → compression masks artifacts.
- Screenshots of AI images (i.e. AI image + extra layer of JPEG compression).
- Drawings, paintings, illustrations — neither real photo nor AI, but TrueSight has to classify them anyway.

## Size constraint reminder

The detection pipeline rejects anything over **12 MB** or **64 megapixels** total. Test images that exceed these limits should produce a clean "Image is too large" error rather than a crash — that's part of the contract worth verifying explicitly in your dissertation's "Input validation" section.
