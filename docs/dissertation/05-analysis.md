# 5. Analysis Phase

## 5.1 Actors

Three actors participate in TrueSight's operations: the **User** (a person uploading an image from any device on the LAN), the **Sightengine API** (invoked once per scan for AI-generation and deepfake probabilities), and the **Hive AI API** (invoked only when Sightengine judges an image AI, purely for generator attribution).

## 5.2 Use Case Diagram

```mermaid
flowchart LR
    User((User))
    SE((Sightengine API))
    HV((Hive AI API))

    subgraph TrueSight
        UC1[Upload Image]
        UC2[View Verdict and Reasons]
        UC3[View Scan History]
        UC4[Clear All History]
        UC5[Detect AI Generation]
        UC6[Detect Deepfake]
        UC7[Identify Generator Engine]
    end

    User --- UC1
    User --- UC2
    User --- UC3
    User --- UC4

    UC1 -.includes.-> UC5
    UC1 -.includes.-> UC6
    UC1 -.extends.-> UC7

    UC5 --- SE
    UC6 --- SE
    UC7 --- HV
```

The user has direct access to four use cases. The remaining three — Detect AI Generation, Detect Deepfake, Identify Generator Engine — are internal to the Upload-Image workflow. The "include" relationships fire on every upload; the "extend" relationship (Identify Generator Engine) fires only when Sightengine has already judged the image AI.

## 5.3 Use Case Specifications

### 5.3.1 UC-1 Upload Image

| Field | Content |
| --- | --- |
| **Actor** | User |
| **Goal** | Submit an image and receive a verdict with supporting forensic evidence. |
| **Preconditions** | Backend running; image file no larger than 12 MB and within 64 megapixels. |
| **Main flow** | (1) User selects image. (2) Frontend validates type and size. (3) User clicks Analyze. (4) Backend validates extension, renames to UUID, checks magic bytes and dimensions. (5) Backend calls Sightengine. (6) If AI score ≥ 50%, backend calls Hive for attribution. (7) Backend composes verdict and persists to history. (8) Frontend renders verdict card with reasons and signals. |
| **Alternate flows** | A. File rejected client-side — toast error. B. File rejected by backend validation — inline error. C. Sightengine unreachable — Error verdict. D. Hive unreachable but Sightengine succeeded — verdict returns with a "no attribution" note. |
| **Postconditions** | History row inserted; image stored under UUID filename. |

### 5.3.2 UC-2 View Verdict and Reasons

| Field | Content |
| --- | --- |
| **Actor** | User |
| **Goal** | Understand the system's reasoning. |
| **Preconditions** | A scan has just completed. |
| **Main flow** | (1) User reads verdict label and confidence. (2) User opens the Detection Details modal. (3) Modal shows bullet-point reasons, per-signal scores, attribution rows, and EXIF metadata summary. (4) User closes the modal. |
| **Postconditions** | None (read-only). |

### 5.3.3 UC-3 View Scan History

| Field | Content |
| --- | --- |
| **Actor** | User |
| **Goal** | Review previously-analysed images. |
| **Preconditions** | At least one scan exists. |
| **Main flow** | (1) User clicks History tab. (2) Frontend requests `GET /history`. (3) Backend returns the most recent fifty rows, newest first. (4) Frontend renders thumbnails with verdict, score, and timestamp. |
| **Alternate flow** | History empty — empty-state message displayed. |

### 5.3.4 UC-4 Clear All History

| Field | Content |
| --- | --- |
| **Actor** | User |
| **Goal** | Permanently remove all stored scans and uploaded files. |
| **Preconditions** | History tab active. |
| **Main flow** | (1) User clicks Clear History. (2) Backend deletes all files in `uploads/` and truncates the `history` table. (3) Frontend refreshes to the empty state. |
| **Postconditions** | `history` table empty; `uploads/` directory empty. |

## 5.4 Activity Diagrams

### 5.4.1 `/predict` request lifecycle

```mermaid
flowchart TD
    Start([User clicks Analyze]) --> A[Frontend validates type and size]
    A -->|invalid| ErrToast[Display error toast]
    ErrToast --> End1([End])
    A -->|valid| B[POST /predict]
    B --> C[Backend: extension whitelist]
    C -->|reject| Err400a[400 Unsupported file type]
    C -->|accept| D[secure_filename + UUID rename]
    D --> E[Save to uploads/]
    E --> F[PIL: magic-byte check]
    F -->|format mismatch| DelFile[Delete file]
    DelFile --> Err400b[400 Not a valid image]
    F -->|valid| G[Read width, height, EXIF, JPEG quant]
    G --> H{Dimensions OK?}
    H -->|fail| ErrDim[Error: too large or too small]
    H -->|valid| I[Call Sightengine: genai + deepfake]
    I -->|API error| ErrSE[Error: detection unavailable]
    I -->|success| J[Parse ai_generated and deepfake]
    J --> K{ai_score >= 50%?}
    K -->|no| M[Skip Hive: real-photo path]
    K -->|yes| L[Call Hive for attribution]
    L -->|success| L1[Parse attribution engines]
    L -->|failure| L2[Log warning, continue without attribution]
    L1 --> M
    L2 --> M
    M --> N[Build signals and reasons]
    N --> O[Apply LABEL_THRESHOLDS]
    O --> P[INSERT into history]
    P --> Q[Return JSON to frontend]
    Q --> R[Frontend animates verdict card]
    R --> End2([End])
```

The diamond at `ai_score >= 50%` is the central design decision of the project — it gates whether Hive is called. The diamonds at format and dimension validation close off the validation stack before any external API is contacted, ensuring no API quota is spent on invalid input.

### 5.4.2 Input validation stack

```mermaid
flowchart TD
    Start([File arrives at backend]) --> L1{File present?}
    L1 -->|no| R1[400 No image uploaded]
    L1 -->|yes| L2{Filename non-empty?}
    L2 -->|no| R2[400 Empty filename]
    L2 -->|yes| L3{Extension whitelisted?}
    L3 -->|no| R3[400 Unsupported]
    L3 -->|yes| L4[secure_filename + UUID rename]
    L4 --> L5[Save to uploads/]
    L5 --> L6[Open with PIL]
    L6 --> L7{Format is JPEG/PNG/WEBP/BMP/TIFF/JPEG2000?}
    L7 -->|no| L7a[Delete saved file]
    L7a --> R4[400 Not a valid image]
    L7 -->|yes| L8{width * height <= 64 MP?}
    L8 -->|no| R5[Error: too large]
    L8 -->|yes| L9{min side >= 8 px?}
    L9 -->|no| R6[Error: too small]
    L9 -->|yes| OK([Proceed to detection])
```

The five layers are deliberately ordered cheapest first: presence and extension checks complete in microseconds; PIL parsing and dimension reading are reserved for files that have already cleared the cheaper gates.
