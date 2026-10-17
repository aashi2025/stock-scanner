// Global Application State
const state = {
    currentTab: 'dashboard',
    upstoxStatus: null,
    scanResult: null,
    swingResult: null,
    monthlyResult: null,
    sectorsData: [],
    watchlist: [],
    chartInstance: null
};

// DOM Initialization
document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    checkUpstoxStatus();
    runGlobalScan();
});

// Tab Navigation
function switchTab(tabId) {
    state.currentTab = tabId;
    
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    
    // Deactivate desktop & mobile nav links
    document.querySelectorAll('.nav-link').forEach(el => el.classList.remove('active', 'bg-brand-600', 'text-white'));
    document.querySelectorAll('.mob-link').forEach(el => el.classList.remove('active', 'text-brand-400'));

    // Activate selected tab
    const targetTab = document.getElementById(`tab-${tabId}`);
    if (targetTab) targetTab.classList.remove('hidden');

    const dtNav = document.getElementById(`nav-${tabId}`);
    if (dtNav) dtNav.classList.add('active', 'bg-brand-600', 'text-white');

    const mobNav = document.getElementById(`mob-${tabId}`);
    if (mobNav) mobNav.classList.add('active', 'text-brand-400');

    // Trigger tab-specific fetches if needed
    if (tabId === 'swing' && !state.swingResult) runSwingScan();
    if (tabId === 'monthly' && !state.monthlyResult) runMonthlyScan();
    if (tabId === 'sectors') loadSectors();
    lucide.createIcons();
}

// Check Upstox API Status
async function checkUpstoxStatus() {
    try {
        const res = await fetch('/api/upstox/status');
        const data = await res.json();
        state.upstoxStatus = data;

        const dot = document.getElementById('upstox-dot');
        const label = document.getElementById('upstox-badge-label');
        const sourceText = document.getElementById('data-source-text');
        const settingsBadge = document.getElementById('settings-mode-badge');
        const settingsReason = document.getElementById('settings-token-reason');

        if (data.is_authenticated) {
            dot.className = "w-2 h-2 rounded-full bg-emerald-400";
            label.innerText = `Upstox: ${data.user_name || 'Live'}`;
            sourceText.innerText = "Upstox API v2 (Live Authenticated Market Quotes & Candles)";
            if (settingsBadge) {
                settingsBadge.className = "px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
                settingsBadge.innerText = "Live Authenticated";
            }
            if (settingsReason) {
                settingsReason.innerText = `Connected as ${data.user_name} (${data.user_id}). Real-time quotes, historical candles & fundamentals active.`;
            }
        } else {
            dot.className = "w-2 h-2 rounded-full bg-amber-400";
            label.innerText = "Upstox: Free EOD";
            sourceText.innerText = "Upstox API v2 (Verified Historical Candle Mode - ₹0/mo)";
            if (settingsBadge) {
                settingsBadge.className = "px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30";
                settingsBadge.innerText = "Free Historical Candle Mode";
            }
            if (settingsReason) {
                settingsReason.innerText = "Running on Upstox's public historical candle API (100% free). Connect Upstox broker account for live tick-by-tick quotes.";
            }
        }
        if (data.redirect_url && document.getElementById('display-redirect-url')) {
            document.getElementById('display-redirect-url').value = data.redirect_url;
        } else if (document.getElementById('display-redirect-url')) {
            document.getElementById('display-redirect-url').value = `${window.location.origin}/api/upstox/callback`;
        }

        if (data.masked_api_key && document.getElementById('cfg-upstox-api-key')) {
            document.getElementById('cfg-upstox-api-key').placeholder = `Configured: ${data.masked_api_key}`;
        }
    } catch (e) {
        console.error("Failed to check Upstox status:", e);
    }
}

// Copy Exact Redirect URL to Clipboard
function copyRedirectUrl() {
    const el = document.getElementById('display-redirect-url');
    if (!el) return;
    el.select();
    navigator.clipboard.writeText(el.value).then(() => {
        showToast("✅ Exact Redirect URL copied to clipboard! Paste it into Upstox Developer Console.", "success");
    }).catch(() => {
        document.execCommand('copy');
        showToast("✅ Redirect URL copied!", "success");
    });
}

// Save Upstox Credentials in .env
async function saveUpstoxCredentials() {
    const key = document.getElementById('cfg-upstox-api-key').value.trim();
    const secret = document.getElementById('cfg-upstox-api-secret').value.trim();
    const redirectUrl = document.getElementById('display-redirect-url').value.trim();

    if (!key || !secret) {
        showToast("कृपया Upstox API Key और API Secret दोनों भरें।", "error");
        return;
    }

    try {
        const res = await fetch('/api/upstox/credentials', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                api_key: key,
                api_secret: secret,
                redirect_uri: redirectUrl
            })
        });
        const data = await res.json();
        if (res.ok) {
            showToast("✅ Credentials सुरक्षित रूप से .env में सेव हो गए!", "success");
            document.getElementById('cfg-upstox-api-secret').value = "";
            checkUpstoxStatus();
        } else {
            showToast(data.detail || "Credentials सेव नहीं हो सके", "error");
        }
    } catch (e) {
        showToast("Server connection error while saving credentials", "error");
    }
}

// Upstox Modal Handlers
function openUpstoxModal() {
    document.getElementById('upstox-modal').classList.remove('hidden');
    document.getElementById('upstox-modal').classList.add('flex');
}

function closeUpstoxModal() {
    document.getElementById('upstox-modal').classList.add('hidden');
    document.getElementById('upstox-modal').classList.remove('flex');
}

function openTokenPasteModal() {
    openUpstoxModal();
}

async function submitManualToken() {
    const token = document.getElementById('modal-token-input').value.trim();
    if (!token) {
        showToast("Please paste a valid Upstox Access Token", "error");
        return;
    }
    try {
        const res = await fetch('/api/upstox/set-token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: token })
        });
        const data = await res.json();
        if (res.ok) {
            showToast("Upstox Access Token activated successfully!", "success");
            closeUpstoxModal();
            checkUpstoxStatus();
            runGlobalScan();
        } else {
            showToast(data.detail || "Failed to verify token", "error");
        }
    } catch (e) {
        showToast("Error connecting to server", "error");
    }
}

async function loginWithUpstoxOAuth() {
    try {
        const res = await fetch('/api/upstox/login-url');
        const data = await res.json();
        if (data.auth_url) {
            window.location.href = data.auth_url;
        } else {
            showToast(data.detail || "Could not generate OAuth URL. Check your UPSTOX_API_KEY.", "error");
        }
    } catch (e) {
        showToast("Failed to initiate Upstox OAuth login", "error");
    }
}


async function syncInstruments() {
    showToast("Downloading Upstox NSE instrument master list...", "info");
    try {
        const res = await fetch('/api/upstox/sync-instruments', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast(`Master list updated! Total equities: ${data.total_equities}`, "success");
        } else {
            showToast("Instruments download failed", "error");
        }
    } catch (e) {
        showToast("Error syncing instruments", "error");
    }
}

// Global Multi-Stage Scan (Dashboard)
async function runGlobalScan() {
    const icon = document.getElementById('scan-btn-icon');
    if (icon) icon.classList.add('animate-spin');

    try {
        const res = await fetch('/api/scan/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                universe: 'NIFTY 50',
                min_confirmation_score: 65.0,
                min_sector_score: 55.0
            })
        });
        const data = await res.json();
        state.scanResult = data;

        // Update Dashboard Market Metrics
        document.getElementById('mkt-score-val').innerText = Math.round(data.market_trend.market_score);
        document.getElementById('mkt-class-val').innerText = data.market_trend.classification;
        document.getElementById('mkt-score-bar').style.width = `${data.market_trend.market_score}%`;
        document.getElementById('mkt-score-badge').innerText = data.market_trend.classification;
        document.getElementById('data-timestamp-text').innerText = `Last Scan: ${data.scan_time}`;

        // Sector Counts
        const bullishSecs = data.sector_trends.filter(s => s.trend === 'Bullish').length;
        const neutralSecs = data.sector_trends.filter(s => s.trend === 'Neutral').length;
        const bearishSecs = data.sector_trends.filter(s => s.trend === 'Bearish').length;

        document.getElementById('dash-bullish-sectors-count').innerText = bullishSecs;
        document.getElementById('dash-neutral-sectors-count').innerText = neutralSecs;
        document.getElementById('dash-bearish-sectors-count').innerText = bearishSecs;
        if (data.sector_trends.length > 0) {
            const topSec = [...data.sector_trends].sort((a,b) => b.sector_score - a.sector_score)[0];
            document.getElementById('dash-top-sector').innerText = `${topSec.sector_name} (${topSec.sector_score}/100)`;
        }

        // Render Top Setups Feed
        renderDashboardFeed(data.confirmed_setups);
    } catch (e) {
        console.error("Global scan error:", e);
        showToast("Error running global market scan", "error");
    } finally {
        if (icon) icon.classList.remove('animate-spin');
    }
}

function renderDashboardFeed(setups) {
    const container = document.getElementById('top-setups-list');
    document.getElementById('top-setups-count-badge').innerText = `${setups.length} Setups`;
    
    if (!setups || setups.length === 0) {
        container.innerHTML = `
            <div class="p-8 text-center text-slate-500">
                No stocks meeting full 65+ confirmation points right now. Check Swing Scanner for individual setups.
            </div>
        `;
        return;
    }

    container.innerHTML = setups.slice(0, 10).map(s => `
        <div class="p-4 hover:bg-slate-900/60 transition flex items-center justify-between cursor-pointer" onclick="openStockDetail('${s.symbol}')">
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-xs text-white">
                    ${s.symbol.slice(0, 4)}
                </div>
                <div>
                    <div class="font-bold text-sm text-white flex items-center gap-2">
                        ${s.symbol}
                        <span class="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full">${s.sector}</span>
                    </div>
                    <div class="text-xs text-slate-400 mt-0.5">${s.company_name}</div>
                </div>
            </div>
            <div class="flex items-center space-x-6 text-right">
                <div>
                    <div class="font-bold text-sm text-white">₹${s.price}</div>
                    <div class="text-xs font-semibold ${s.change_percent >= 0 ? 'text-emerald-400' : 'text-rose-400'}">
                        ${s.change_percent >= 0 ? '+' : ''}${s.change_percent}%
                    </div>
                </div>
                <div>
                    <div class="text-xs font-extrabold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20">
                        ${s.confirmation_score}/100
                    </div>
                    <div class="text-[10px] text-slate-400 mt-0.5">${s.classification}</div>
                </div>
            </div>
        </div>
    `).join('');
    lucide.createIcons();
}

// Swing Trading Scanner (Requirement #2)
async function runSwingScan() {
    const universe = document.getElementById('swing-universe-select').value;
    const freshOnly = document.getElementById('swing-fresh-only').checked;
    const icon = document.getElementById('swing-btn-icon');
    if (icon) icon.classList.add('animate-spin');

    const container = document.getElementById('swing-results-container');
    container.innerHTML = `
        <div class="col-span-full p-12 text-center text-slate-500 bg-slate-950 rounded-2xl border border-slate-800">
            <i data-lucide="loader-2" class="w-8 h-8 animate-spin mx-auto mb-2 text-amber-500"></i>
            Scanning Upstox historical candles for RSI 50 fresh crossovers, EMA 50/200 uptrend & volume breakouts...
        </div>
    `;
    lucide.createIcons();

    try {
        const res = await fetch('/api/scan/swing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                universe: universe,
                only_fresh_crossover: freshOnly
            })
        });
        const data = await res.json();
        state.swingResult = data;

        // Update counts
        document.getElementById('dash-fresh-cross-count').innerText = `${data.fresh_crossover_count} Stocks`;
        document.getElementById('dash-vol-breakout-count').innerText = `${data.volume_breakout_count} Stocks`;

        renderSwingCards(data.swing_candidates);
    } catch (e) {
        console.error("Swing scan error:", e);
        showToast("Error running swing trading scan", "error");
    } finally {
        if (icon) icon.classList.remove('animate-spin');
    }
}

function renderSwingCards(candidates) {
    const container = document.getElementById('swing-results-container');
    if (!candidates || candidates.length === 0) {
        container.innerHTML = `
            <div class="col-span-full p-10 text-center text-slate-500 bg-slate-950 rounded-2xl border border-slate-800">
                No swing candidates matched the specified filters. Try unchecking 'Only Fresh RSI 50 Crossovers'.
            </div>
        `;
        return;
    }

    container.innerHTML = candidates.map(c => `
        <div class="bg-slate-950 rounded-2xl border border-slate-800 shadow-xl p-5 hover:border-slate-700 transition flex flex-col justify-between">
            <div>
                <!-- Card Header -->
                <div class="flex items-start justify-between">
                    <div>
                        <div class="font-bold text-base text-white flex items-center gap-2">
                            ${c.symbol}
                            <span class="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full">${c.sector}</span>
                        </div>
                        <div class="text-xs text-slate-400 truncate max-w-[200px]">${c.company_name}</div>
                    </div>
                    <div class="text-right">
                        <div class="text-lg font-extrabold text-white">₹${c.price}</div>
                        <div class="text-xs font-semibold ${c.change_percent >= 0 ? 'text-emerald-400' : 'text-rose-400'}">
                            ${c.change_percent >= 0 ? '+' : ''}${c.change_percent}%
                        </div>
                    </div>
                </div>

                <!-- Swing Signal Badges -->
                <div class="flex flex-wrap gap-1.5 my-3">
                    ${c.rsi_fresh_crossover ? `
                        <span class="inline-flex items-center gap-1 text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-md">
                            ⚡ Fresh RSI 50 Cross (${c.rsi_value})
                        </span>
                    ` : `
                        <span class="inline-flex items-center text-[11px] font-medium bg-slate-800 text-slate-400 px-2 py-0.5 rounded-md">
                            RSI: ${c.rsi_value} (${c.rsi_status})
                        </span>
                    `}

                    ${c.ema_trend_bullish ? `
                        <span class="inline-flex items-center gap-1 text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-md">
                            📈 EMA 50/200 Aligned
                        </span>
                    ` : `
                        <span class="inline-flex items-center text-[11px] font-medium bg-slate-800 text-slate-400 px-2 py-0.5 rounded-md">
                            EMA50: ₹${c.ema_50}
                        </span>
                    `}

                    ${c.volume_breakout ? `
                        <span class="inline-flex items-center gap-1 text-[11px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30 px-2 py-0.5 rounded-md">
                            🔥 Volume Surge (${c.vol_ratio}x)
                        </span>
                    ` : ''}

                    <span class="inline-flex items-center text-[11px] font-medium bg-slate-800 text-slate-300 px-2 py-0.5 rounded-md">
                        52W High: -${c.dist_from_52w_high_pct}%
                    </span>
                </div>

                <!-- Signal Reasons Checklist -->
                <div class="bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 text-xs text-slate-300 space-y-1 my-3">
                    ${c.reasons.map(r => `<div class="truncate">${r}</div>`).join('')}
                </div>
            </div>

            <!-- Reference Entry & Risk-Reward -->
            <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <div>
                    <span class="text-slate-400">Ref Entry:</span>
                    <strong class="text-white ml-1">₹${c.reference_levels.entry_reference}</strong>
                </div>
                <div>
                    <span class="text-slate-400">Stop:</span>
                    <strong class="text-rose-400 ml-1">₹${c.reference_levels.stop_loss_reference}</strong>
                </div>
                <div>
                    <span class="text-slate-400">Target (1:2):</span>
                    <strong class="text-emerald-400 ml-1">₹${c.reference_levels.target_1_reference}</strong>
                </div>
            </div>
        </div>
    `).join('');
    lucide.createIcons();
}

// Monthly Stock Research (Requirement #3)
async function runMonthlyScan() {
    const universe = document.getElementById('monthly-universe-select').value;
    const buyContainer = document.getElementById('monthly-buy-container');
    const holdContainer = document.getElementById('monthly-hold-container');
    const exitContainer = document.getElementById('monthly-exit-container');

    const loadingHtml = `
        <div class="col-span-full p-8 text-center text-slate-500 bg-slate-950 rounded-2xl border border-slate-800">
            <i data-lucide="loader-2" class="w-8 h-8 animate-spin mx-auto mb-2 text-emerald-500"></i>
            Analyzing monthly technical trends and verified financial fundamentals...
        </div>
    `;
    buyContainer.innerHTML = loadingHtml;
    holdContainer.innerHTML = loadingHtml;
    exitContainer.innerHTML = loadingHtml;
    lucide.createIcons();

    try {
        const res = await fetch('/api/scan/monthly', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ universe: universe })
        });
        const data = await res.json();
        state.monthlyResult = data;

        document.getElementById('monthly-buy-count').innerText = data.buy_candidates.length;
        document.getElementById('monthly-hold-count').innerText = data.hold_candidates.length;
        document.getElementById('monthly-exit-count').innerText = data.exit_reviews.length;
        document.getElementById('dash-monthly-buy-count').innerText = `${data.buy_candidates.length} Stocks`;

        renderMonthlyGroup(buyContainer, data.buy_candidates, 'emerald');
        renderMonthlyGroup(holdContainer, data.hold_candidates, 'blue');
        renderMonthlyGroup(exitContainer, data.exit_reviews, 'rose');
    } catch (e) {
        console.error("Monthly scan error:", e);
        showToast("Error running monthly stock research", "error");
    }
}

function renderMonthlyGroup(container, list, theme) {
    if (!list || list.length === 0) {
        container.innerHTML = `
            <div class="col-span-full p-6 text-center text-slate-500 bg-slate-950 rounded-2xl border border-slate-800 text-xs">
                No stocks categorized in this group.
            </div>
        `;
        return;
    }

    container.innerHTML = list.map(item => `
        <div class="bg-slate-950 rounded-2xl border border-slate-800 shadow-xl p-5 hover:border-${theme}-500/50 transition space-y-3">
            <div class="flex items-start justify-between">
                <div>
                    <div class="font-bold text-base text-white flex items-center gap-2">
                        ${item.symbol}
                        <span class="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full">${item.sector}</span>
                    </div>
                    <div class="text-xs text-slate-400">${item.company_name}</div>
                </div>
                <div class="text-right">
                    <div class="text-lg font-extrabold text-white">₹${item.price}</div>
                    <div class="text-[11px] font-bold text-${theme}-400 bg-${theme}-500/10 px-2 py-0.5 rounded border border-${theme}-500/20 inline-block mt-0.5">
                        Score: ${item.score}/100
                    </div>
                </div>
            </div>

            <!-- Fundamentals Snapshot (ROCE, ROE, Debt/Eq, Growth) -->
            <div class="grid grid-cols-3 gap-2 bg-slate-900/80 p-2.5 rounded-xl border border-slate-800 text-center text-xs">
                <div>
                    <div class="text-[10px] text-slate-400">ROCE</div>
                    <div class="font-bold text-white">${item.fundamental_summary.roce > 0 ? item.fundamental_summary.roce + '%' : '--'}</div>
                </div>
                <div>
                    <div class="text-[10px] text-slate-400">ROE</div>
                    <div class="font-bold text-white">${item.fundamental_summary.roe > 0 ? item.fundamental_summary.roe + '%' : '--'}</div>
                </div>
                <div>
                    <div class="text-[10px] text-slate-400">Debt/Eq</div>
                    <div class="font-bold text-white">${item.fundamental_summary.debt_to_equity || '0.0'}</div>
                </div>
                <div>
                    <div class="text-[10px] text-slate-400">Sales Growth</div>
                    <div class="font-bold text-white">${item.fundamental_summary.sales_growth ? item.fundamental_summary.sales_growth + '%' : '--'}</div>
                </div>
                <div>
                    <div class="text-[10px] text-slate-400">P/E Ratio</div>
                    <div class="font-bold text-white">${item.fundamental_summary.pe_ratio || '--'}</div>
                </div>
                <div>
                    <div class="text-[10px] text-slate-400">52W High Dist</div>
                    <div class="font-bold text-white">-${item.technical_summary.dist_52w_pct}%</div>
                </div>
            </div>

            <!-- Action Plan -->
            <div class="text-xs text-slate-300">
                <span class="text-slate-400 font-semibold">Action Plan:</span> ${item.action_plan}
            </div>

            <!-- Source Tag -->
            <div class="text-[10px] text-slate-400 flex items-center justify-between pt-2 border-t border-slate-800">
                <span>Source: ${item.fundamental_summary.data_source}</span>
                <span>As of: ${item.timestamp}</span>
            </div>
        </div>
    `).join('');
    lucide.createIcons();
}

// Sector Trends Loader
async function loadSectors() {
    const grid = document.getElementById('sectors-grid');
    grid.innerHTML = '<div class="col-span-full p-8 text-center text-slate-500">Loading sector performance...</div>';
    try {
        const res = await fetch('/api/market/sectors');
        const sectors = await res.json();
        state.sectorsData = sectors;

        grid.innerHTML = sectors.map(sec => `
            <div class="bg-slate-900 p-4 rounded-xl border border-slate-800 hover:border-slate-700 transition space-y-2">
                <div class="flex items-center justify-between">
                    <span class="font-bold text-sm text-white">${sec.sector_name}</span>
                    <span class="px-2 py-0.5 rounded-full text-[11px] font-bold ${
                        sec.trend === 'Bullish' ? 'bg-emerald-500/20 text-emerald-400' :
                        sec.trend === 'Bearish' ? 'bg-rose-500/20 text-rose-400' : 'bg-amber-500/20 text-amber-400'
                    }">${sec.trend}</span>
                </div>
                <div class="text-xs text-slate-400 flex items-center justify-between">
                    <span>Score: <strong class="text-white">${sec.sector_score}/100</strong></span>
                    <span>RSI: <strong class="text-white">${sec.rsi}</strong></span>
                </div>
                <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div class="bg-brand-500 h-1.5 rounded-full" style="width: ${sec.sector_score}%"></div>
                </div>
            </div>
        `).join('');
        lucide.createIcons();
    } catch (e) {
        grid.innerHTML = '<div class="col-span-full p-8 text-center text-rose-400">Failed to load sector data.</div>';
    }
}

// Historical Backtest Simulation
async function runBacktestSimulation() {
    const universe = document.getElementById('bt-universe').value;
    const start = document.getElementById('bt-start').value;
    const stop = parseFloat(document.getElementById('bt-stop').value);
    const target = parseFloat(document.getElementById('bt-target').value);

    showToast("Running historical backtest simulation with transaction costs...", "info");

    try {
        const res = await fetch('/api/backtest/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                universe: universe,
                start_date: start,
                end_date: new Date().toISOString().split('T')[0],
                min_confirmation_score: 65.0,
                min_sector_score: 60.0,
                stop_loss_pct: stop,
                target_pct: target,
                slippage_pct: 0.2
            })
        });
        const bt = await res.json();

        document.getElementById('backtest-results-area').classList.remove('hidden');
        document.getElementById('bt-total-trades').innerText = bt.total_trades;
        document.getElementById('bt-win-rate').innerText = `${bt.win_rate_pct}%`;
        document.getElementById('bt-profit-factor').innerText = bt.profit_factor;
        document.getElementById('bt-max-dd').innerText = `${bt.max_drawdown_pct}%`;
        showToast("Backtest simulation completed!", "success");
    } catch (e) {
        showToast("Error running backtest simulation", "error");
    }
}

// Toast Notifications Helper
function showToast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    const bg = type === 'success' ? 'bg-emerald-600' : (type === 'error' ? 'bg-rose-600' : 'bg-slate-800 border border-slate-700');
    toast.className = `${bg} text-white text-xs px-4 py-2.5 rounded-xl shadow-2xl flex items-center gap-2 pointer-events-auto transition-all duration-300`;
    toast.innerHTML = `<span>${msg}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Stock Modal Placeholder
function openStockDetail(sym) {
    showToast(`Viewing technical levels for ${sym}`, "info");
}
