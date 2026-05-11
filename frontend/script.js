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
        return { label: "Real Photo 📷", color: "#27ae60", score };
    } else if (score < 45) {
        return { label: "Likely Real", color: "#2980b9", score };
    } else if (score < 60) {
        return { label: "Hard to Tell ❓", color: "#f39c12", score };
    } else if (score < 85) {
        return { label: "Suspicious ⚠️", color: "#e67e22", score };
    } else {
        return { label: "AI Generated 🤖", color: "#c0392b", score };
    }
}

// -------------------------------
// CLIENT-SIDE COMPRESSION
// -------------------------------
async function compressImage(file, maxWidth = 1920, maxHeight = 1920) {
    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = event => {
            const img = new Image();
            img.src = event.target.result;
            img.onload = () => {
                let width = img.width;
                let height = img.height;

                if (width > maxWidth || height > maxHeight) {
                    if (width > height) {
                        height = Math.round((height *= maxWidth / width));
                        width = maxWidth;
                    } else {
                        width = Math.round((width *= maxHeight / height));
                        height = maxHeight;
                    }
                }

                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);

                canvas.toBlob(blob => {
                    const compressedFile = new File([blob], file.name, {
                        type: 'image/jpeg',
                        lastModified: Date.now()
                    });
                    resolve(compressedFile);
                }, 'image/jpeg', 0.85);
            };
        };
    });
}

// -------------------------------
// TAB SWITCHING
// -------------------------------
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    const buttons = document.querySelectorAll('.tab-btn');
    if (tabName === 'home') buttons[0].classList.add('active');
    else buttons[1].classList.add('active');

    document.querySelectorAll('.view').forEach(view => view.style.display = 'none');
    document.getElementById(`${tabName}-view`).style.display = 'block';

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
            alert("Please drop an image file");
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

            if (file.size > 16 * 1024 * 1024) {
                alert("File too large (max 16MB)");
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

    document.getElementById("removeBtn").addEventListener("click", (e) => {
        e.stopPropagation();
        fileInput.value = "";
        dropZone.style.display = 'block';
        previewContainer.style.display = 'none';
        uploadBtn.disabled = true;
        resultContainer.style.display = 'none';
        currentAnalysis = null;
    });

    uploadBtn.addEventListener("click", async () => {
        let file = fileInput.files[0];

        uploadBtn.disabled = true;
        uploadBtn.innerText = "Preparing Image...";
        resultContainer.style.display = 'none';

        if (file.size > 500 * 1024) { // Compress if larger than 500KB
            file = await compressImage(file);
        }

        const formData = new FormData();
        formData.append("image", file);

        uploadBtn.innerText = "Analyzing Signals...";

        try {
            const response = await fetch(API_URL, { method: "POST", body: formData });
            const data = await response.json();

            const aiScore = data.score * 100;
            const forensic = getForensicLabel(aiScore);

            // MAIN RESULT
            document.getElementById("resultTitle").innerHTML =
                `<span style="color:${forensic.color}">${forensic.label}</span>`;

            document.getElementById("confValue").innerText =
                `${Math.round(aiScore)}% AI Likelihood`;

            const bar = document.getElementById("progressBar");
            bar.style.width = `${aiScore}%`;
            bar.style.backgroundColor = forensic.color;

            resultContainer.style.display = 'block';

            uploadBtn.innerText = "Analyze Image";
            uploadBtn.disabled = false;

            // -------------------------------
            // SIGNALS DISPLAY
            // -------------------------------
            if (data.signals) {
                const s = data.signals;
                
                let statsHtml = '';
                for (const [expert, score] of Object.entries(s)) {
                    statsHtml += `<p>${expert}: ${score.toFixed(1)}% AI Likelihood</p>`;
                }

                const signalsHTML = `
                    <div style="margin-top:15px; font-size:0.9rem; opacity:0.85; line-height: 1.6;">
                        ${statsHtml}
                    </div>
                `;

                const extra = document.getElementById("extraInfo");
                if (extra) extra.innerHTML = signalsHTML;
            }

            // SAVE CURRENT ANALYSIS
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
            alert("Server Error");
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
            list.innerHTML = `<div style="text-align:center; color:#aaa;">No history yet</div>`;
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
                <img src="${imageUrl}" class="history-thumb">
                <div class="history-info">
                    <h4 style="color:${forensic.color}">${forensic.label}</h4>
                    <p>${item.confidence}% AI Likelihood</p>
                </div>
            `;

            list.appendChild(div);
        });

    } catch (error) {
        console.error(error);
        list.innerHTML = `<div style="color:red;">Connection Failed</div>`;
    }
}

async function clearHistory() {
    if (confirm("Clear all history?")) {
        await fetch(CLEAR_URL, { method: "DELETE" });
        lastHistoryJson = "";
        fetchHistory();
    }
}

// -------------------------------
// MODAL
// -------------------------------
function openDetailsModal(data = null) {
    const item = data || currentAnalysis;
    if (!item) return;

    document.getElementById("modalImg").src = item.image;

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
            reasonsList.appendChild(li);
        });
    }

    if (item.signals) {
        const s = item.signals;
        for (const [expert, score] of Object.entries(s)) {
            const li = document.createElement("li");
            li.textContent = `${expert}: ${score.toFixed(1)}% AI Likelihood`;
            reasonsList.appendChild(li);
        }
    }

    document.getElementById("detailsModal").style.display = 'flex';
}

function closeDetailsModal() {
    document.getElementById("detailsModal").style.display = 'none';
}

window.onclick = function (event) {
    if (event.target == document.getElementById("detailsModal")) {
        closeDetailsModal();
    }
};