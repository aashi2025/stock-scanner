/**
 * Swing Delivery Trade Screener (Nifty 100) — Client Application Logic
 */

let allResults = [];

document.addEventListener("DOMContentLoaded", () => {
    const scanBtn = document.getElementById("scanBtn");
    const bulkWaBtn = document.getElementById("bulkWaBtn");
    const searchInput = document.getElementById("searchInput");
    const filterSignal = document.getElementById("filterSignal");
    const sortBy = document.getElementById("sortBy");

    scanBtn.addEventListener("click", () => triggerScan(true));
    searchInput.addEventListener("input", renderTable);
    filterSignal.addEventListener("change", renderTable);
    sortBy.addEventListener("change", renderTable);
    bulkWaBtn.addEventListener("click", handleBulkWaShare);

    // Initial check: if cache exists, load immediately
    fetch("/api/scan?force=false")
        .then(res => res.json())
        .then(payload => {
            if (payload.status === "success" && payload.data && payload.data.length > 0) {
                allResults = payload.data;
                updateMetrics(payload);
                renderTable();
            }
        })
        .catch(() => {});
});

async function triggerScan(force = true) {
    const initialState = document.getElementById("initialState");
    const loadingState = document.getElementById("loadingState");
    const resultsSection = document.getElementById("resultsSection");
    const metricsRow = document.getElementById("metricsRow");
    const scanBtn = document.getElementById("scanBtn");

    initialState.style.display = "none";
    resultsSection.style.display = "none";
    loadingState.style.display = "block";
    scanBtn.disabled = true;
    scanBtn.innerText = "⏳ Scanning...";

    try {
        const response = await fetch(`/api/scan?force=${force}`);
        const data = await response.json();

        if (data.status === "success") {
            allResults = data.data || [];
            updateMetrics(data);
            renderTable();
        } else {
            alert("Scan Error: " + (data.message || "Failed to fetch scan results"));
        }
    } catch (err) {
        alert("Network Error: Could not connect to screener backend. " + err.message);
    } finally {
        loadingState.style.display = "none";
        scanBtn.disabled = false;
        scanBtn.innerHTML = '<span class="btn-icon">⚡</span> Scan Market Today';
    }
}

function updateMetrics(payload) {
    const metricsRow = document.getElementById("metricsRow");
    metricsRow.style.display = "grid";

    document.getElementById("valTotalScanned").innerText = payload.total_scanned || 100;
    document.getElementById("valMatches").innerText = allResults.length;

    const readyCount = allResults.filter(r => r.signal.includes("READY")).length;
    const waitCount = allResults.filter(r => r.signal.includes("WAIT")).length;

    document.getElementById("valReady").innerText = readyCount;
    document.getElementById("valWait").innerText = waitCount;

    if (payload.scan_time) {
        document.getElementById("scanTimestamp").innerText = `Scanned: ${payload.scan_time}`;
    }
}

function renderTable() {
    const resultsSection = document.getElementById("resultsSection");
    const tableBody = document.getElementById("tableBody");
    const bulkWaBtn = document.getElementById("bulkWaBtn");
    const countHeading = document.getElementById("tableCountHeading");

    const searchQuery = document.getElementById("searchInput").value.trim().toUpperCase();
    const filterVal = document.getElementById("filterSignal").value;
    const sortVal = document.getElementById("sortBy").value;

    let filtered = [...allResults];

    // Search filter
    if (searchQuery) {
        filtered = filtered.filter(r => r.symbol.toUpperCase().includes(searchQuery));
    }

    // Signal filter
    if (filterVal === "READY") {
        filtered = filtered.filter(r => r.signal.includes("READY"));
    } else if (filterVal === "WAIT") {
        filtered = filtered.filter(r => r.signal.includes("WAIT"));
    } else if (filterVal === "BREAKOUT") {
        filtered = filtered.filter(r => r.setup_type.includes("Breakout"));
    } else if (filterVal === "PULLBACK") {
        filtered = filtered.filter(r => r.setup_type.includes("Pullback"));
    }

    // Sorting
    filtered.sort((a, b) => {
        if (sortVal === "rr_desc") {
            return b.rr_numeric - a.rr_numeric;
        } else if (sortVal === "rsi_desc") {
            return b.rsi_14 - a.rsi_14;
        } else if (sortVal === "rsi_asc") {
            return a.rsi_14 - b.rsi_14;
        } else if (sortVal === "cmp_desc") {
            return b.cmp - a.cmp;
        }
        return 0;
    });

    tableBody.innerHTML = "";

    if (filtered.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 30px; color: #94a3b8;">No matching stocks found for current filter.</td></tr>`;
        resultsSection.style.display = "block";
        bulkWaBtn.style.display = "none";
        countHeading.innerText = "Screened Opportunities (0)";
        return;
    }

    countHeading.innerText = `Screened Opportunities (${filtered.length})`;
    bulkWaBtn.style.display = "inline-flex";

    filtered.forEach(row => {
        const tr = document.createElement("tr");

        const isReady = row.signal.includes("READY");
        const signalClass = isReady ? "badge-ready" : "badge-wait";

        const waText = `🎯 *SWING ACTION SCREENER ALERT*
━━━━━━━━━━━━━━━━━━━
*${row.symbol}* | *${row.signal}*
• *Setup:* ${row.setup_type}
• *CMP / Entry:* ₹${row.entry_level}
• *Stop Loss (SL):* ₹${row.stop_loss} (-${row.sl_pct}%)
• *Target Level:* ₹${row.target_level} (+${row.target_pct}%)
• *Risk/Reward:* ${row.risk_reward_ratio}
• *RSI (14):* ${row.rsi_14} | *200 EMA:* ₹${row.ema_200}
━━━━━━━━━━━━━━━━━━━
⚠️ _Analytical Research Only. Alerts-only mode._`;

        const waUrl = `https://wa.me/?text=${encodeURIComponent(waText)}`;

        tr.innerHTML = `
            <td><span class="symbol-name">${row.symbol}</span></td>
            <td><span class="price-text">₹${Number(row.cmp).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span></td>
            <td><span class="badge-signal ${signalClass}">${row.signal}</span></td>
            <td><span class="badge-setup">${row.setup_type}</span></td>
            <td><span class="price-text">₹${Number(row.entry_level).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span></td>
            <td><span class="sl-text">₹${Number(row.stop_loss).toLocaleString('en-IN', {minimumFractionDigits: 2})} <small>(-${row.sl_pct}%)</small></span></td>
            <td><span class="target-text">₹${Number(row.target_level).toLocaleString('en-IN', {minimumFractionDigits: 2})} <small>(+${row.target_pct}%)</small></span></td>
            <td><strong>${row.risk_reward_ratio}</strong></td>
            <td><span>${row.rsi_14}</span></td>
            <td><a href="${waUrl}" target="_blank" class="btn-sm-wa">📲 WhatsApp</a></td>
        `;

        tableBody.appendChild(tr);
    });

    resultsSection.style.display = "block";
}

function handleBulkWaShare() {
    const ready = allResults.filter(r => r.signal.includes("READY"));
    const picks = ready.length > 0 ? ready.slice(0, 5) : allResults.slice(0, 5);

    if (picks.length === 0) {
        alert("No stocks to share.");
        return;
    }

    const lines = [
        "🎯 *NIFTY 100 SWING ACTION SCREENER REPORT*",
        `📅 Date: ${new Date().toLocaleDateString('en-GB')}`,
        "━━━━━━━━━━━━━━━━━━━",
        `⚡ *Top Filtered Setups (${picks.length}):*`,
        ""
    ];

    picks.forEach(p => {
        lines.push(`• *${p.symbol}* (${p.signal})`);
        lines.push(`  CMP: ₹${p.cmp} | Setup: ${p.setup_type}`);
        lines.push(`  🎯 Target: ₹${p.target_level} (+${p.target_pct}%) | 🛑 SL: ₹${p.stop_loss} (-${p.sl_pct}%) | RR: ${p.risk_reward_ratio}`);
        lines.push("");
    });

    lines.push("━━━━━━━━━━━━━━━━━━━");
    lines.push("⚠️ _Analytical Research Only. Alerts-only mode._");

    const fullUrl = `https://wa.me/?text=${encodeURIComponent(lines.join("\n"))}`;
    window.open(fullUrl, "_blank");
}
