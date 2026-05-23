# Appendix C: CD of the Project

This appendix specifies the contents of the physical deliverable accompanying the dissertation. The "CD" requirement in the university template may be satisfied with any modern equivalent — USB drive, archive download, or repository link — at the discretion of the marker.

## C.1 Repository URL

The complete project source code is published in a public GitHub repository at:

**https://github.com/M4hdi-7/TrueSight-AI-Image-Detector**

The submission branch is **`sighteng`** — this is the version that corresponds to the dissertation. Other branches (`main`, `hive`, `hive-sighteng`) exist for development reference and document alternative or earlier architectures.

The state of `sighteng` at the time of dissertation submission is preserved by the most recent commit reference (commit hash to be filled in at submission time):

> Commit reference: `_________________________________________` (insert short SHA before printing)

## C.2 Contents of the deliverable

The physical CD or USB drive should contain the following items, arranged in the directory layout below.

```
TrueSight-Submission/
    README.txt                       Short pointer to the GitHub repo and PDF
    TrueSight-Dissertation.pdf       The compiled dissertation
    TrueSight-Source.zip             Snapshot of the sighteng branch at submission commit
    Test/                            The 59-image evaluation set
        README.md                    Ground-truth labels for every image
        (59 image files)
    docs/
        ARCHITECTURE.md              Detailed system architecture document
        VIVA_QUESTIONS.md            Examiner-question playbook (private — for student preparation)
        dissertation/                Markdown source of each dissertation section
    evaluation_report.md             Latest evaluation results (Markdown)
    evaluation_results.json          Latest evaluation results (JSON)
    backend/                         All Python source files
    frontend/                        All HTML / CSS / JS source files
    LICENSE                          MIT licence text
    CHANGELOG.md                     Version history
```

## C.3 How to verify the deliverable

A marker who wishes to reproduce the results should:

1. Extract `TrueSight-Source.zip` to a local directory.
2. Follow the setup instructions in `README.md`:
   - Create a Python virtual environment.
   - Install the pinned dependencies from `backend/requirements.txt`.
   - Create `backend/.env` with the three required API credentials (Sightengine user, Sightengine secret, Hive key). Free-tier accounts at https://sightengine.com and https://thehive.ai are sufficient for verification within the daily quota.
3. Run the smoke test: `cd backend ; venv\Scripts\python.exe verify_sightengine.py`. This confirms the credentials are valid and the pipeline returns a verdict on a known AI sample.
4. (Optional) Run the full evaluation: `venv\Scripts\python.exe evaluate.py`. This produces fresh `evaluation_report.md` and `evaluation_results.json` files. Reproducing the exact numbers in the dissertation requires the same test set; the Sightengine API may have evolved since this dissertation was written, so minor variation is possible.
5. Start the application: `.\start.bat` (Windows) or run the Flask backend and `python -m http.server 8000` in `frontend/` (any platform). Open the URL displayed in the launcher's terminal window.

## C.4 Hardware and software requirements

- **Operating system**: Any modern Windows / macOS / Linux. The one-click launcher (`start.bat`) is Windows-only; on other platforms the backend and frontend servers must be started manually as described in `README.md`.
- **Python**: 3.10 or newer.
- **Disk space**: Approximately 200 MB once the virtual environment is created (most of which is Pillow's binary wheel).
- **Network**: Internet access is required for Sightengine and Hive API calls. No other external dependency.
- **API accounts**: Free-tier accounts at Sightengine and Hive AI. The free tiers are sufficient for running the demonstration; reproducing the full 59-image evaluation requires roughly 590 Sightengine operations and 40 Hive calls, which fits inside the standard free monthly allowance.

## C.5 Contact

For any question about the submission or the source code, the author can be contacted at the email address recorded on the dissertation cover page.
