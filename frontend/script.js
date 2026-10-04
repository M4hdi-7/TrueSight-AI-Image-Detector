// -------------------------------
// THEME TOGGLE
// -------------------------------
function toggleTheme() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const newTheme = isDark ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

// -------------------------------
// NETWORK SETUP
// -------------------------------
const currentIP = window.location.hostname;
const BASE_URL = `http://${currentIP}:5000`;
const API_URL = `${BASE_URL}/predict`;
const HISTORY_URL = `${BASE_URL}/history`;
const CLEAR_URL = `${BASE_URL}/clear_history`;

// -------------------------------
// APP STATE
// -------------------------------
let currentAnalysis = null;
let lastHistoryJson = "";

// -------------------------------
// LABEL + COLOR (CLEAN VERSION)
// -------------------------------
function getForensicLabel(score) {
    if (score < 20) {
        return { label: "Real Photo", icon: "fa-camera-retro", color: "#27ae60", score };
    } else if (score < 45) {
        return { label: "Likely Real", icon: "fa-check", color: "#2980b9", score };
    } else if (score < 60) {
        return { label: "Hard to Tell", icon: "fa-circle-question", color: "#f39c12", score };
    } else if (score < 85) {
        return { label: "Suspicious", icon: "fa-triangle-exclamation", color: "#e67e22", score };
    } else {
        return { label: "AI Generated", icon: "fa-robot", color: "#c0392b", score };
    }
}

function renderForensicLabel(forensic) {
    const iconClass = forensic.icon || "fa-circle-info";
    const safeLabel = forensic.label
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    return `<i class="fas ${iconClass}" aria-hidden="true" style="margin-right:8px;"></i>${safeLabel}`;
}

// -------------------------------
// TOAST + CONFIRM HELPERS
// -------------------------------
function showToast(message, type = "info", duration = 3500) {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const iconMap = {
        info: "fa-circle-info",
        success: "fa-circle-check",
        warning: "fa-triangle-exclamation",
        error: "fa-circle-exclamation",
    };
    const icon = iconMap[type] || iconMap.info;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.setAttribute("role", type === "error" ? "alert" : "status");
    toast.innerHTML = `<i class="fas ${icon}" aria-hidden="true"></i><span></span>`;
    toast.querySelector("span").textContent = message;
    container.appendChild(toast);

    const dismiss = () => {
        if (!toast.parentNode) return;
        toast.classList.add("leaving");
        toast.addEventListener("animationend", () => toast.remove(), { once: true });
    };
    setTimeout(dismiss, duration);
    toast.addEventListener("click", dismiss);
}

let confirmPreviousFocus = null;
function showConfirm({ title = "Are you sure?", message = "", acceptLabel = "Confirm", cancelLabel = "Cancel" } = {}) {
    return new Promise(resolve => {
        const modal = document.getElementById("confirmModal");
        const titleEl = document.getElementById("confirmTitle");
        const msgEl = document.getElementById("confirmMessage");
        const acceptBtn = document.getElementById("confirmAcceptBtn");
        const cancelBtn = document.getElementById("confirmCancelBtn");

        titleEl.textContent = title;
        msgEl.textContent = message;
        acceptBtn.textContent = acceptLabel;
        cancelBtn.textContent = cancelLabel;

        confirmPreviousFocus = document.activeElement;

        const cleanup = (result) => {
            modal.style.display = "none";
            modal.setAttribute("aria-hidden", "true");
            document.body.classList.remove("modal-open");
            acceptBtn.removeEventListener("click", onAccept);
            cancelBtn.removeEventListener("click", onCancel);
            modal.removeEventListener("click", onOverlay);
            document.removeEventListener("keydown", onKey);
            if (confirmPreviousFocus && typeof confirmPreviousFocus.focus === "function") {
                confirmPreviousFocus.focus();
            }
            resolve(result);
        };

        const onAccept = () => cleanup(true);
        const onCancel = () => cleanup(false);
        const onOverlay = (e) => { if (e.target === modal) cleanup(false); };
        const onKey = (e) => {
            if (e.key === "Escape") cleanup(false);
            if (e.key === "Tab") trapFocus(e, modal);
        };

        acceptBtn.addEventListener("click", onAccept);
        cancelBtn.addEventListener("click", onCancel);
        modal.addEventListener("click", onOverlay);
        document.addEventListener("keydown", onKey);

        modal.style.display = "flex";
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("modal-open");
        requestAnimationFrame(() => cancelBtn.focus());
    });
}

function trapFocus(e, container) {
    const focusables = container.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
    }
}

function escapeHTML(s) {
    return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

// -------------------------------
// TAB SWITCHING
// -------------------------------
function switchTab(tabName) {
    const buttons = document.querySelectorAll('.tab-btn');
    buttons.forEach(btn => {
        const isActive = btn.getAttribute('aria-controls') === `${tabName}-view`;
        btn.classList.toggle('active', isActive);
        btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
        btn.setAttribute('tabindex', isActive ? '0' : '-1');
    });

    document.querySelectorAll('.view').forEach(view => {
        const show = view.id === `${tabName}-view`;
        view.style.display = show ? 'block' : 'none';
        if (show) view.removeAttribute('hidden');
        else view.setAttribute('hidden', '');
    });

    if (tabName === 'history') {
        fetchHistory();
    }
}

// -------------------------------
// HOME PAGE
// -------------------------------
document.addEventListener("DOMContentLoaded", () => {
    const fileInput = document.getElementById("fileInput");
    const dropZone = document.getElementById("dropZone");
    const previewContainer = document.getElementById("previewContainer");
    const uploadBtn = document.getElementById("uploadBtn");
    const resultContainer = document.getElementById("result");

    dropZone.addEventListener("click", () => fileInput.click());

    // Keyboard support for the dropzone (it's a role="button" div)
    dropZone.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            fileInput.click();
        }
    });

    // --- DRAG & DROP ---
    let dragCounter = 0;

    dropZone.addEventListener("dragenter", (e) => {
        e.preventDefault();
        e.stopPropagation();
        dragCounter++;
        dropZone.classList.add("drag-active");
    });

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        e.stopPropagation();
        e.dataTransfer.dropEffect = "copy";
    });

    dropZone.addEventListener("dragleave", (e) => {
        e.preventDefault();
        e.stopPropagation();
        dragCounter--;
        if (dragCounter <= 0) {
            dragCounter = 0;
            dropZone.classList.remove("drag-active");
        }
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        e.stopPropagation();
        dragCounter = 0;
        dropZone.classList.remove("drag-active");

        const files = e.dataTransfer.files;
        if (!files || files.length === 0) return;

        const file = files[0];
        if (!file.type.startsWith("image/")) {
            showToast("Please drop an image file.", "warning");
            return;
        }

        const dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;
        fileInput.dispatchEvent(new Event("change"));
    });

    // Prevent the browser from opening the file when dropped outside the zone
    ["dragover", "drop"].forEach(evt => {
        window.addEventListener(evt, (e) => {
            if (e.target !== dropZone && !dropZone.contains(e.target)) {
                e.preventDefault();
            }
        });
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];

            if (file.size > 12 * 1024 * 1024) {
                showToast("File too large. Max 12MB.", "error");
                fileInput.value = "";
                return;
            }

            const reader = new FileReader();
            reader.onload = (e) => {
                document.getElementById("preview").src = e.target.result;
                dropZone.style.display = 'none';
                previewContainer.style.display = 'block';
                uploadBtn.disabled = false;
                resultContainer.style.display = 'none';
            };
            reader.readAsDataURL(file);
        }
    });

    function resetForNewAnalysis() {
        fileInput.value = "";
        dropZone.style.display = 'block';
        previewContainer.style.display = 'none';
        uploadBtn.style.display = 'block';
        uploadBtn.disabled = true;
        uploadBtn.innerText = "Analyze Image";
        document.getElementById("loadingIndicator").hidden = true;
        resultContainer.style.display = 'none';
        currentAnalysis = null;
        // Scroll the dropzone into view (helpful after analysis when results were tall)
        dropZone.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        dropZone.focus({ preventScroll: true });
    }

    document.getElementById("removeBtn").addEventListener("click", (e) => {
        e.stopPropagation();
        resetForNewAnalysis();
    });

    document.getElementById("newScanBtn").addEventListener("click", () => {
        resetForNewAnalysis();
    });

    uploadBtn.addEventListener("click", async () => {
        let file = fileInput.files[0];

        uploadBtn.style.display = 'none';
        document.getElementById("loadingIndicator").hidden = false;
        resultContainer.style.display = 'none';

        const formData = new FormData();
        formData.append("image", file);

        try {
            const response = await fetch(API_URL, { method: "POST", body: formData });
            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                const msg = data.error || `Request failed (${response.status})`;
                showToast(msg, "error");
                document.getElementById("loadingIndicator").hidden = true;
                uploadBtn.style.display = 'block';
                uploadBtn.disabled = false;
                uploadBtn.innerText = "Analyze Image";
                return;
            }

            const aiScore = data.score * 100;
            const forensic = getForensicLabel(aiScore);

            // MAIN RESULT
            document.getElementById("resultTitle").innerHTML =
                `<span style="color:${forensic.color}">${renderForensicLabel(forensic)}</span>`;

            document.getElementById("confValue").innerText =
                `${Math.round(aiScore)}% AI Likelihood`;

            const bar = document.getElementById("progressBar");
            bar.style.width = `${aiScore}%`;
            bar.style.backgroundColor = forensic.color;

            document.getElementById("loadingIndicator").hidden = true;
            // Keep upload button hidden — the result card now owns the next CTA
            // ("Analyze Another Image" inside .result-actions)
            uploadBtn.innerText = "Analyze Image";
            uploadBtn.disabled = false;

            resultContainer.style.display = 'block';

            // -------------------------------
            // SIGNALS DISPLAY
            // -------------------------------
            if (data.signals) {
                const s = data.signals;

                let statsHtml = '';
                let attributionHtml = '';
                for (const [expert, score] of Object.entries(s)) {
                    if (expert.startsWith("Attribution")) {
                        const engineMatch = expert.match(/Attribution \(([^)]+)\)/);
                        const engineName = engineMatch ? engineMatch[1] : "Unknown";
                        attributionHtml += `
                            <div class="signal-attribution">
                                <strong><i class="fas fa-robot" aria-hidden="true"></i> AI Engine: ${escapeHTML(engineName)}</strong>
                                <span class="score">${score.toFixed(1)}% Confidence</span>
                            </div>
                        `;
                    } else {
                        statsHtml += `<p>${escapeHTML(expert)}: ${score.toFixed(1)}%</p>`;
                    }
                }

                const signalsHTML = `
                    <div class="signals-list">
                        ${statsHtml}
                        ${attributionHtml}
                    </div>
                `;

                const extra = document.getElementById("extraInfo");
                if (extra) extra.innerHTML = signalsHTML;
            }

            // SAVE CURRENT ANALYSISa
            currentAnalysis = {
                image: `${BASE_URL}/uploads/${data.filename}`,
                result: data.verdict,
                confidence: Math.round(aiScore),
                signals: data.signals,
                metadata: data.metadata,
                reasons: data.reasons
            };

            fetchHistory();

        } catch (error) {
            console.error(error);
            showToast("Server error. Please try again.", "error");
            document.getElementById("loadingIndicator").hidden = true;
            uploadBtn.style.display = 'block';
            uploadBtn.disabled = false;
            uploadBtn.innerText = "Analyze Image";
        }
    });
});

// -------------------------------
// HISTORY
// -------------------------------
async function fetchHistory() {
    const list = document.getElementById("historyList");

    try {
        const response = await fetch(`${HISTORY_URL}?t=${Date.now()}`);
        const historyData = await response.json();

        const currentJson = JSON.stringify(historyData);
        if (currentJson === lastHistoryJson && list.children.length > 0) return;
        lastHistoryJson = currentJson;

        if (historyData.length === 0) {
            list.innerHTML = `<div class="history-empty">No history yet.</div>`;
            return;
        }

        list.innerHTML = "";

        historyData.forEach(item => {
            const forensic = getForensicLabel(item.confidence);
            const imageUrl = `${BASE_URL}/uploads/${item.filename}`;

            const div = document.createElement("div");
            div.className = "history-item";

            div.onclick = () => openDetailsModal({
                ...item,
                image: imageUrl
            });

            div.innerHTML = `
                <img src="${imageUrl}" class="history-thumb" alt="${escapeHTML(forensic.label)} scan thumbnail">
                <div class="history-info">
                    <h4 style="color:${forensic.color}">${renderForensicLabel(forensic)}</h4>
                    <p>${item.confidence}% AI Likelihood</p>
                </div>
            `;

            list.appendChild(div);
        });

    } catch (error) {
        console.error(error);
        list.innerHTML = `<div class="history-empty history-error"><i class="fas fa-triangle-exclamation" aria-hidden="true"></i> Connection failed. Check that the backend is running.</div>`;
    }
}

async function clearHistory() {
    const ok = await showConfirm({
        title: "Clear all history?",
        message: "This will permanently delete every scan from your history. This action cannot be undone.",
        acceptLabel: "Clear All",
        cancelLabel: "Cancel",
    });
    if (!ok) return;
    try {
        await fetch(CLEAR_URL, { method: "DELETE" });
        lastHistoryJson = "";
        fetchHistory();
        showToast("History cleared.", "success");
    } catch (e) {
        console.error(e);
        showToast("Failed to clear history.", "error");
    }
}

// -------------------------------
// MODAL
// -------------------------------
let detailsPreviousFocus = null;

function classifySignal(text) {
    const t = text.toLowerCase();
    if (t.includes("✅") || t.includes("clean") || t.includes("no ai")) return "signal-success";
    if (t.includes("❌") || t.includes("ai engine") || t.includes("ai generated") || t.includes("manipulat")) return "signal-danger";
    if (t.includes("⚠️") || t.includes("suspicious") || t.includes("warning")) return "signal-warning";
    return "";
}

function openDetailsModal(data = null) {
    const item = data || currentAnalysis;
    if (!item) return;

    const modal = document.getElementById("detailsModal");
    document.getElementById("modalImg").src = item.image;
    document.getElementById("modalImg").dataset.fullsrc = item.image;

    document.getElementById("metaCamera").innerText =
        item.metadata?.camera || "N/A";

    document.getElementById("metaSoftware").innerText =
        item.metadata?.software || "N/A";

    const reasonsList = document.getElementById("modalReasons");
    reasonsList.innerHTML = "";

    if (item.reasons && item.reasons.length > 0) {
        item.reasons.forEach(r => {
            const li = document.createElement("li");
            li.textContent = r;
            const cls = classifySignal(r);
            if (cls) li.classList.add(cls);
            reasonsList.appendChild(li);
        });
    }

    if (item.signals) {
        const s = item.signals;
        for (const [expert, score] of Object.entries(s)) {
            const li = document.createElement("li");
            li.textContent = `${expert}: ${score.toFixed(1)}% AI Likelihood`;
            const cls = score >= 60 ? "signal-danger" : score >= 30 ? "signal-warning" : "signal-success";
            li.classList.add(cls);
            reasonsList.appendChild(li);
        }
    }

    detailsPreviousFocus = document.activeElement;

    modal.style.display = 'flex';
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");
    document.addEventListener("keydown", detailsKeyHandler);

    requestAnimationFrame(() => {
        const closeBtn = modal.querySelector(".close-modal");
        if (closeBtn) closeBtn.focus();
    });
}

function detailsKeyHandler(e) {
    const modal = document.getElementById("detailsModal");
    if (modal.style.display !== "flex") return;
    if (e.key === "Escape") {
        e.preventDefault();
        closeDetailsModal();
    } else if (e.key === "Tab") {
        trapFocus(e, modal);
    }
}

function closeDetailsModal() {
    const modal = document.getElementById("detailsModal");
    modal.style.display = 'none';
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
    document.removeEventListener("keydown", detailsKeyHandler);
    if (detailsPreviousFocus && typeof detailsPreviousFocus.focus === "function") {
        detailsPreviousFocus.focus();
    }
}

window.onclick = function (event) {
    if (event.target == document.getElementById("detailsModal")) {
        closeDetailsModal();
    }
};

// -------------------------------
// LIGHTBOX
// -------------------------------
let lightboxPreviousFocus = null;

function openLightbox(src) {
    if (!src) return;
    const lb = document.getElementById("imageLightbox");
    const lbImg = document.getElementById("lightboxImg");
    lbImg.src = src;
    lightboxPreviousFocus = document.activeElement;
    lb.classList.add("open");
    lb.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");
    document.addEventListener("keydown", lightboxKeyHandler);
    requestAnimationFrame(() => {
        const closeBtn = document.getElementById("lightboxClose");
        if (closeBtn) closeBtn.focus();
    });
}

function closeLightbox() {
    const lb = document.getElementById("imageLightbox");
    lb.classList.remove("open");
    lb.setAttribute("aria-hidden", "true");
    // Only release body scroll if no other modal is open
    const detailsOpen = document.getElementById("detailsModal").style.display === "flex";
    const confirmOpen = document.getElementById("confirmModal").style.display === "flex";
    if (!detailsOpen && !confirmOpen) {
        document.body.classList.remove("modal-open");
    }
    document.removeEventListener("keydown", lightboxKeyHandler);
    if (lightboxPreviousFocus && typeof lightboxPreviousFocus.focus === "function") {
        lightboxPreviousFocus.focus();
    }
}

function lightboxKeyHandler(e) {
    if (e.key === "Escape") {
        e.preventDefault();
        closeLightbox();
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const imgWrapper = document.querySelector(".modal-image-wrapper");
    if (imgWrapper) {
        imgWrapper.setAttribute("role", "button");
        imgWrapper.setAttribute("tabindex", "0");
        imgWrapper.setAttribute("aria-label", "Open image in full view");
        const trigger = () => {
            const src = document.getElementById("modalImg").src;
            openLightbox(src);
        };
        imgWrapper.addEventListener("click", trigger);
        imgWrapper.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                trigger();
            }
        });
    }

    const lb = document.getElementById("imageLightbox");
    const lbClose = document.getElementById("lightboxClose");
    if (lb) {
        lb.addEventListener("click", (e) => {
            // Click on backdrop closes; click on the image itself also closes
            if (e.target === lb || e.target.id === "lightboxImg") {
                closeLightbox();
            }
        });
    }
    if (lbClose) {
        lbClose.addEventListener("click", (e) => {
            e.stopPropagation();
            closeLightbox();
        });
    }
});