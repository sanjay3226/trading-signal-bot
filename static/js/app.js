/**
 * ╔══════════════════════════════════════════════════════════╗
 * ║  TRADING SIGNAL BOT — Frontend Logic                     ║
 * ╚══════════════════════════════════════════════════════════╝
 *
 * HOW THIS WORKS:
 * ───────────────
 * 1. User selects market + asset + timeframe
 * 2. Clicks "Analyse" → calls /api/analyze on our FastAPI server
 * 3. Server runs 30 indicators + patterns + divergences + MTF
 * 4. Returns a JSON result
 * 5. This JS renders it into charts, cards, tables
 *
 * KEY CONCEPTS:
 * - We use TradingView's Lightweight Charts for candlestick rendering
 * - All data comes from our Python backend (we just display it)
 * - The "confidence" is calculated server-side from weighted indicator votes
 */

// ═══════════════════════════════════════
//  STATE — what we're currently viewing
// ═══════════════════════════════════════
const state = {
    market: 'crypto',
    asset: 'BTC/USDT',
    timeframe: '1h',
    mode: 'single',   // 'single' or 'scanner'
    chart: null,       // TradingView chart instance
    candleSeries: null,
    volumeSeries: null,
    lastResult: null,  // last analysis result
};


// ═══════════════════════════════════════
//  DOM ELEMENTS
// ═══════════════════════════════════════
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const els = {
    market: $('#marketSelect'),
    asset: $('#assetSelect'),
    tf: $('#tfSelect'),
    btnAnalyse: $('#btnAnalyse'),
    btnScan: $('#btnScan'),
    btnAlert: $('#btnAlert'),
    loading: $('#loadingOverlay'),
    singleView: $('#singleView'),
    scannerView: $('#scannerView'),
    clock: $('#clock'),
};


// ═══════════════════════════════════════
//  INITIALISATION
// ═══════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    setupClock();
    setupNavTabs();
    setupFilterPills();
    setupEventListeners();
    loadAssets();
    initChart();
});


// ═══════════════════════════════════════
//  CLOCK — top right corner
// ═══════════════════════════════════════
function setupClock() {
    const update = () => {
        const now = new Date();
        els.clock.textContent = now.toLocaleTimeString('en-GB');
    };
    update();
    setInterval(update, 1000);
}


// ═══════════════════════════════════════
//  NAV TABS — switch between views
// ═══════════════════════════════════════
function setupNavTabs() {
    $$('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            $$('.nav-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            state.mode = tab.dataset.mode;

            if (state.mode === 'single') {
                els.singleView.classList.remove('hidden');
                els.scannerView.classList.add('hidden');
                $('#assetGroup').classList.remove('hidden');
            } else {
                els.singleView.classList.add('hidden');
                els.scannerView.classList.remove('hidden');
                $('#assetGroup').classList.add('hidden');
            }
        });
    });
}


// ═══════════════════════════════════════
//  FILTER PILLS — for indicator categories
// ═══════════════════════════════════════
function setupFilterPills() {
    $$('.filter-pills .pill').forEach(pill => {
        pill.addEventListener('click', () => {
            $$('.filter-pills .pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            filterIndicators(pill.dataset.cat);
        });
    });
}

function filterIndicators(category) {
    $$('.ind-row').forEach(row => {
        if (category === 'all' || row.dataset.category === category) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}


// ═══════════════════════════════════════
//  EVENT LISTENERS
// ═══════════════════════════════════════
function setupEventListeners() {
    // Market changed → reload asset list
    els.market.addEventListener('change', () => {
        state.market = els.market.value;
        loadAssets();
    });

    // Asset changed
    els.asset.addEventListener('change', () => {
        state.asset = els.asset.value;
    });

    // Timeframe changed
    els.tf.addEventListener('change', () => {
        state.timeframe = els.tf.value;
    });

    // Analyse button
    els.btnAnalyse.addEventListener('click', () => {
        runAnalysis();
    });

    // Scan button
    els.btnScan.addEventListener('click', () => {
        runScanner();
    });

    // Alert button
    els.btnAlert.addEventListener('click', () => {
        sendAlert();
    });
}


// ═══════════════════════════════════════
//  LOAD ASSETS — fetch watchlist from API
// ═══════════════════════════════════════
async function loadAssets() {
    try {
        const res = await fetch(`/api/assets?market=${state.market}`);
        const data = await res.json();

        els.asset.innerHTML = '';
        data.assets.forEach(a => {
            const opt = document.createElement('option');
            opt.value = a;
            opt.textContent = a;
            els.asset.appendChild(opt);
        });
        state.asset = data.assets[0];
    } catch (e) {
        console.error('Failed to load assets:', e);
    }
}


// ═══════════════════════════════════════
//  CHART — TradingView Lightweight Charts
// ═══════════════════════════════════════
/**
 * We use TradingView's FREE open-source charting library.
 * It renders beautiful candlestick charts in a <canvas> element.
 * Very fast, handles thousands of candles smoothly.
 */
function initChart() {
    const container = $('#chartContainer');
    if (!container) return;

    state.chart = LightweightCharts.createChart(container, {
        width: container.clientWidth,
        height: 420,
        layout: {
            background: { type: 'solid', color: '#1a1f2e' },
            textColor: '#94a3b8',
            fontFamily: 'Inter',
        },
        grid: {
            vertLines: { color: 'rgba(255,255,255,0.03)' },
            horzLines: { color: 'rgba(255,255,255,0.03)' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
            vertLine: { color: 'rgba(0,212,170,0.3)', labelBackgroundColor: '#0a0e17' },
            horzLine: { color: 'rgba(0,212,170,0.3)', labelBackgroundColor: '#0a0e17' },
        },
        timeScale: {
            borderColor: 'rgba(255,255,255,0.06)',
            timeVisible: true,
        },
        rightPriceScale: {
            borderColor: 'rgba(255,255,255,0.06)',
        },
    });

    // Candlestick series
    state.candleSeries = state.chart.addCandlestickSeries({
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderUpColor: '#22c55e',
        borderDownColor: '#ef4444',
        wickUpColor: '#22c55e',
        wickDownColor: '#ef4444',
    });

    // Volume series (histogram at bottom)
    state.volumeSeries = state.chart.addHistogramSeries({
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
    });
    state.chart.priceScale('volume').applyOptions({
        scaleMargins: { top: 0.85, bottom: 0 },
    });

    // Responsive resize
    const resizeObserver = new ResizeObserver(() => {
        state.chart.applyOptions({
            width: container.clientWidth,
        });
    });
    resizeObserver.observe(container);
}

function updateChart(chartData) {
    if (!state.candleSeries || !chartData || !chartData.length) return;

    // Set candlestick data
    state.candleSeries.setData(chartData);

    // Set volume data with colours
    const volData = chartData.map(d => ({
        time: d.time,
        value: d.volume,
        color: d.close >= d.open
            ? 'rgba(34,197,94,0.3)'
            : 'rgba(239,68,68,0.3)',
    }));
    state.volumeSeries.setData(volData);

    // Fit content
    state.chart.timeScale().fitContent();
}


// ═══════════════════════════════════════
//  RUN ANALYSIS — single asset
// ═══════════════════════════════════════
async function runAnalysis() {
    showLoading(true);

    try {
        const url = `/api/analyze?symbol=${encodeURIComponent(state.asset)}`
            + `&market=${state.market}&tf=${state.timeframe}`;

        const res = await fetch(url);
        const data = await res.json();

        if (data.error) {
            alert(data.error);
            showLoading(false);
            return;
        }

        state.lastResult = data;
        renderAnalysis(data);

    } catch (e) {
        alert('Analysis failed: ' + e.message);
    }

    showLoading(false);
}


// ═══════════════════════════════════════
//  RENDER ANALYSIS — populate all UI
// ═══════════════════════════════════════
function renderAnalysis(data) {
    // 1. Metrics row
    renderMetrics(data);

    // 2. Chart
    updateChart(data.chart_data);
    $('#chartBadge').textContent = `${data.symbol} · ${data.timeframe}`;

    // 3. Signal card
    renderSignalCard(data);

    // 4. Vote breakdown
    renderVotes(data);

    // 5. MTF results
    renderMTF(data.htf_results || []);

    // 6. Levels
    renderLevels(data);

    // 7. Patterns
    renderPatterns(data.patterns || []);

    // 8. Divergences
    renderDivergences(data.divergences || []);

    // 9. Indicators table
    renderIndicators(data.indicators || []);
}


// ─── Metrics row ───
function renderMetrics(d) {
    const chgCol = d.change_pct >= 0 ? 'var(--green)' : 'var(--red)';
    const chgArrow = d.change_pct >= 0 ? '▲' : '▼';

    $('#metricsRow').innerHTML = `
        <div class="metric-card fade-in">
            <div class="label">Asset</div>
            <div class="value">${d.symbol}</div>
        </div>
        <div class="metric-card fade-in">
            <div class="label">Price</div>
            <div class="value">${formatPrice(d.price)}</div>
        </div>
        <div class="metric-card fade-in">
            <div class="label">Change</div>
            <div class="value" style="color:${chgCol}">${chgArrow} ${Math.abs(d.change_pct).toFixed(2)}%</div>
        </div>
        <div class="metric-card fade-in">
            <div class="label">Signal</div>
            <div class="value" style="color:${d.color}">${d.emoji} ${d.tier}</div>
        </div>
        <div class="metric-card fade-in">
            <div class="label">Confidence</div>
            <div class="value" style="color:${d.color}">${d.confidence.toFixed(1)}%</div>
        </div>
        <div class="metric-card fade-in">
            <div class="label">Indicators</div>
            <div class="value">${d.total_signals || d.indicators.length}</div>
        </div>
    `;
}


// ─── Signal card ───
function renderSignalCard(d) {
    const card = $('#signalCard');
    card.style.background = `linear-gradient(135deg, ${d.color}15, ${d.color}05)`;
    card.style.borderColor = `${d.color}33`;

    $('#sigEmoji').textContent = d.emoji;
    $('#sigTier').textContent = d.tier;
    $('#sigTier').style.color = d.color;
    $('#sigConf').textContent = `${d.confidence.toFixed(1)}%`;
    $('#sigConf').style.color = d.color;
    $('#sigPrice').textContent = formatPrice(d.price);

    const chgCol = d.change_pct >= 0 ? 'var(--green)' : 'var(--red)';
    const arrow = d.change_pct >= 0 ? '▲' : '▼';
    $('#sigChange').innerHTML = `<span style="color:${chgCol}">${arrow} ${Math.abs(d.change_pct).toFixed(2)}%</span>`;

    const fill = $('#confFill');
    fill.style.width = `${d.confidence}%`;
    fill.style.background = `linear-gradient(90deg, ${d.color}, ${d.color}aa)`;
}


// ─── Vote breakdown ───
function renderVotes(d) {
    const total = d.buy_count + d.sell_count + d.neutral_count;

    $('#voteBars').innerHTML = `
        ${voteBarHTML('Buy', d.buy_count, total, 'var(--green)')}
        ${voteBarHTML('Sell', d.sell_count, total, 'var(--red)')}
        ${voteBarHTML('Neutral', d.neutral_count, total, 'var(--text-muted)')}
    `;
}

function voteBarHTML(label, count, total, color) {
    const pct = total ? (count / total * 100) : 0;
    return `
        <div class="vote-row">
            <div class="vote-label" style="color:${color}">${label}</div>
            <div class="vote-bar-bg">
                <div class="vote-bar-fill" style="width:${pct}%;background:${color}"></div>
            </div>
            <div class="vote-count" style="color:${color}">${count}</div>
        </div>
    `;
}


// ─── MTF results ───
function renderMTF(htfResults) {
    const el = $('#mtfResults');
    if (!htfResults.length) {
        el.innerHTML = '<p class="muted">No higher TF data (try lower primary TF)</p>';
        return;
    }

    el.innerHTML = htfResults.map(h => `
        <div class="mtf-row">
            <span class="mtf-tf">${h.timeframe.toUpperCase()}</span>
            <span class="mtf-signal" style="color:${h.color}">
                ${h.emoji} ${h.tier}
            </span>
            <span style="color:${h.color};font-size:0.8rem;font-weight:700;">
                ${h.confidence.toFixed(0)}%
            </span>
        </div>
    `).join('');
}


// ─── Levels ───
function renderLevels(d) {
    const el = $('#levelsContent');
    const lv = d.levels;
    if (!lv) {
        el.innerHTML = '<p class="muted">Could not calculate levels</p>';
        return;
    }

    const isLong = d.direction === 'BUY';
    el.innerHTML = `
        <div class="level-row">
            <span class="level-label">📍 Entry</span>
            <span>${formatPrice(lv.price)}</span>
        </div>
        <div class="level-row">
            <span class="level-label" style="color:var(--red)">🛑 Stop Loss</span>
            <span style="color:var(--red)">${formatPrice(isLong ? lv.long_sl : lv.short_sl)}</span>
        </div>
        <div class="level-row">
            <span class="level-label" style="color:var(--green)">🎯 Take Profit</span>
            <span style="color:var(--green)">${formatPrice(isLong ? lv.long_tp : lv.short_tp)}</span>
        </div>
        <div class="level-row">
            <span class="level-label">⚖️ R:R Ratio</span>
            <span>1 : ${lv.rr_ratio}</span>
        </div>
        <div class="level-row">
            <span class="level-label">📏 ATR</span>
            <span>${formatPrice(lv.atr)}</span>
        </div>
    `;
}


// ─── Patterns ───
function renderPatterns(patterns) {
    const el = $('#patternsContent');
    if (!patterns.length) {
        el.innerHTML = '<p class="muted">No candlestick patterns detected</p>';
        return;
    }

    el.innerHTML = patterns.map(p => {
        const col = p.signal > 0 ? 'var(--green)' : p.signal < 0 ? 'var(--red)' : 'var(--text-muted)';
        const bg = p.signal > 0 ? 'var(--green-soft)' : p.signal < 0 ? 'var(--red-soft)' : 'transparent';
        return `
            <div class="pattern-item" style="background:${bg}">
                <span class="pattern-icon">${p.value || '🕯️'}</span>
                <div>
                    <div class="pattern-name" style="color:${col}">${p.name}</div>
                    <div class="pattern-desc">${p.desc}</div>
                </div>
            </div>
        `;
    }).join('');
}


// ─── Divergences ───
function renderDivergences(divs) {
    const el = $('#divergencesContent');
    if (!divs.length) {
        el.innerHTML = '<p class="muted">No divergences detected</p>';
        return;
    }

    el.innerHTML = divs.map(d => {
        const col = d.signal > 0 ? 'var(--green)' : 'var(--red)';
        const bg = d.signal > 0 ? 'var(--green-soft)' : 'var(--red-soft)';
        return `
            <div class="divergence-item" style="background:${bg}">
                <span class="pattern-icon">${d.value || '↗'}</span>
                <div>
                    <div class="pattern-name" style="color:${col}">${d.name}</div>
                    <div class="pattern-desc">${d.desc}</div>
                </div>
            </div>
        `;
    }).join('');
}


// ─── Indicators table ───
function renderIndicators(indicators) {
    const el = $('#indicatorsTable');
    if (!indicators.length) {
        el.innerHTML = '<p class="muted">No indicator data</p>';
        return;
    }

    el.innerHTML = indicators.map(ind => {
        const sig = ind.signal;
        let badgeCol, badgeLabel;

        if (sig > 0.05) {
            badgeCol = 'var(--green)';
            badgeLabel = 'BUY';
        } else if (sig < -0.05) {
            badgeCol = 'var(--red)';
            badgeLabel = 'SELL';
        } else {
            badgeCol = 'var(--text-muted)';
            badgeLabel = 'NEUTRAL';
        }

        const barPct = Math.round(Math.abs(sig) * 100);
        const cat = ind.category || 'oscillator';

        return `
            <div class="ind-row" data-category="${cat}">
                <div class="ind-name">${ind.name}</div>
                <div class="ind-value">${ind.value}</div>
                <div class="ind-bar">
                    <div class="ind-bar-fill"
                         style="width:${barPct}%;background:${badgeCol}"></div>
                </div>
                <div class="ind-signal">
                    <span class="pill" style="background:${badgeCol}22;color:${badgeCol};">
                        ${badgeLabel}
                    </span>
                </div>
                <div class="ind-desc">${ind.desc}</div>
            </div>
        `;
    }).join('');
}


// ═══════════════════════════════════════
//  RUN SCANNER — all assets
// ═══════════════════════════════════════
async function runScanner() {
    // Switch to scanner view
    $$('.nav-tab').forEach(t => t.classList.remove('active'));
    $$('.nav-tab')[1].classList.add('active');
    els.singleView.classList.add('hidden');
    els.scannerView.classList.remove('hidden');
    $('#assetGroup').classList.add('hidden');

    showLoading(true);

    try {
        const url = `/api/scan?market=${state.market}&tf=${state.timeframe}`;
        const res = await fetch(url);
        const data = await res.json();

        renderScanner(data.results);
        $('#scanCount').textContent = `${data.total} assets`;

    } catch (e) {
        alert('Scan failed: ' + e.message);
    }

    showLoading(false);
}


function renderScanner(results) {
    // Strong signals (≥85%)
    const strong = results.filter(r => r.confidence >= 85);
    const strongEl = $('#strongSignals');

    if (strong.length) {
        strongEl.innerHTML = `<h3 style="grid-column:1/-1;margin-bottom:8px;">🔥 Strong Signals</h3>` +
            strong.map(r => scanCardHTML(r)).join('');
    } else {
        strongEl.innerHTML = '';
    }

    // Table
    const tableEl = $('#scannerTable');
    tableEl.innerHTML = `
        <div class="scan-table-row header">
            <span>Symbol</span>
            <span>Price</span>
            <span>Change</span>
            <span>Signal</span>
            <span>Confidence</span>
            <span>Votes</span>
            <span>MTF</span>
        </div>
        ${results.map(r => scanTableRowHTML(r)).join('')}
    `;

    // Click rows to analyse
    $$('.scan-table-row:not(.header)').forEach((row, i) => {
        row.addEventListener('click', () => {
            state.asset = results[i].symbol;
            els.asset.value = results[i].symbol;

            // Switch to single view
            $$('.nav-tab').forEach(t => t.classList.remove('active'));
            $$('.nav-tab')[0].classList.add('active');
            els.singleView.classList.remove('hidden');
            els.scannerView.classList.add('hidden');
            $('#assetGroup').classList.remove('hidden');

            runAnalysis();
        });
    });
}

function scanCardHTML(r) {
    const chgCol = r.change_pct >= 0 ? 'var(--green)' : 'var(--red)';
    const arrow = r.change_pct >= 0 ? '▲' : '▼';
    return `
        <div class="scan-card" style="background:linear-gradient(135deg,${r.color}15,${r.color}05);border-color:${r.color}33;">
            <div class="sc-symbol">${r.symbol}</div>
            <div class="sc-tier" style="color:${r.color}">${r.emoji} ${r.tier}</div>
            <div class="sc-price">${formatPrice(r.price)}</div>
            <div class="sc-conf" style="color:${r.color}">${r.confidence.toFixed(1)}%</div>
            <div class="sc-change" style="color:${chgCol}">${arrow} ${Math.abs(r.change_pct).toFixed(2)}%</div>
        </div>
    `;
}

function scanTableRowHTML(r) {
    const chgCol = r.change_pct >= 0 ? 'var(--green)' : 'var(--red)';
    const arrow = r.change_pct >= 0 ? '▲' : '▼';
    const mtfAlign = r.htf_results?.length
        ? r.htf_results.map(h => h.emoji).join(' ')
        : '—';

    return `
        <div class="scan-table-row">
            <span style="font-weight:700;">${r.symbol}</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.85rem;">${formatPrice(r.price)}</span>
            <span style="color:${chgCol};font-weight:600;">${arrow} ${Math.abs(r.change_pct).toFixed(2)}%</span>
            <span style="color:${r.color};font-weight:700;">${r.emoji} ${r.tier}</span>
            <span style="color:${r.color};font-weight:700;font-family:'JetBrains Mono',monospace;">${r.confidence.toFixed(1)}%</span>
            <span style="font-size:0.8rem;">${r.buy_count}/${r.sell_count}/${r.neutral_count}</span>
            <span>${mtfAlign}</span>
        </div>
    `;
}


// ═══════════════════════════════════════
//  SEND ALERT
// ═══════════════════════════════════════
async function sendAlert() {
    if (!state.lastResult) {
        alert('Run an analysis first!');
        return;
    }
    try {
        const url = `/api/alert?symbol=${encodeURIComponent(state.asset)}`
            + `&market=${state.market}&tf=${state.timeframe}`;
        await fetch(url, { method: 'POST' });
        alert('✅ Alert sent to Telegram/Discord!');
    } catch (e) {
        alert('Failed to send alert: ' + e.message);
    }
}


// ═══════════════════════════════════════
//  UTILITIES
// ═══════════════════════════════════════

function showLoading(show) {
    if (show) {
        els.loading.classList.add('active');
    } else {
        els.loading.classList.remove('active');
    }
}

/**
 * Format price for display.
 * Smart formatting: shows more decimals for small numbers.
 *
 * BTC at $67,234.50 → "67,234.50"
 * DOGE at $0.08234  → "0.08234"
 */
function formatPrice(price) {
    if (price === null || price === undefined) return '—';
    const p = parseFloat(price);
    if (isNaN(p)) return '—';

    if (p >= 1000) return p.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (p >= 1) return p.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
    if (p >= 0.01) return p.toFixed(4);
    return p.toFixed(6);
}
