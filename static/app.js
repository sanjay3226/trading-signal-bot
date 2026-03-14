var state = {
    market: 'crypto',
    asset: 'BTC/USDT',
    timeframe: '1h',
    mode: 'single',
    chart: null,
    candleSeries: null,
    volumeSeries: null,
    lastResult: null
};

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

document.addEventListener('DOMContentLoaded', function() {
    setupClock();
    setupNavTabs();
    setupFilterPills();
    setupEventListeners();
    loadAssets();
    initChart();
});

function setupClock() {
    var el = $('#clock');
    function update() {
        var now = new Date();
        if (el) el.textContent = now.toLocaleTimeString('en-GB');
    }
    update();
    setInterval(update, 1000);
}

function setupNavTabs() {
    $$('.nav-tab').forEach(function(tab) {
        tab.addEventListener('click', function() {
            $$('.nav-tab').forEach(function(t) { t.classList.remove('active'); });
            tab.classList.add('active');
            state.mode = tab.dataset.mode;
            if (state.mode === 'single') {
                $('#singleView').classList.remove('hidden');
                $('#scannerView').classList.add('hidden');
                $('#assetGroup').classList.remove('hidden');
            } else {
                $('#singleView').classList.add('hidden');
                $('#scannerView').classList.remove('hidden');
                $('#assetGroup').classList.add('hidden');
            }
        });
    });
}

function setupFilterPills() {
    $$('.filter-pills .pill').forEach(function(pill) {
        pill.addEventListener('click', function() {
            $$('.filter-pills .pill').forEach(function(p) { p.classList.remove('active'); });
            pill.classList.add('active');
            filterIndicators(pill.dataset.cat);
        });
    });
}

function filterIndicators(category) {
    $$('.ind-row').forEach(function(row) {
        if (category === 'all' || row.dataset.category === category) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

function setupEventListeners() {
    $('#marketSelect').addEventListener('change', function() {
        state.market = $('#marketSelect').value;
        loadAssets();
    });
    $('#assetSelect').addEventListener('change', function() {
        state.asset = $('#assetSelect').value;
    });
    $('#tfSelect').addEventListener('change', function() {
        state.timeframe = $('#tfSelect').value;
    });
    $('#btnAnalyse').addEventListener('click', function() {
        runAnalysis();
    });
    $('#btnScan').addEventListener('click', function() {
        runScanner();
    });
    $('#btnAlert').addEventListener('click', function() {
        sendAlert();
    });
}

function loadAssets() {
    fetch('/api/assets?market=' + state.market)
        .then(function(res) { return res.json(); })
        .then(function(data) {
            var sel = $('#assetSelect');
            sel.innerHTML = '';
            data.assets.forEach(function(a) {
                var opt = document.createElement('option');
                opt.value = a;
                opt.textContent = a;
                sel.appendChild(opt);
            });
            state.asset = data.assets[0];
        })
        .catch(function(e) {
            console.error('Failed to load assets:', e);
        });
}

function initChart() {
    var container = $('#chartContainer');
    if (!container || typeof LightweightCharts === 'undefined') return;
    state.chart = LightweightCharts.createChart(container, {
        width: container.clientWidth,
        height: 420,
        layout: {
            background: { type: 'solid', color: '#1a1f2e' },
            textColor: '#94a3b8',
            fontFamily: 'Inter'
        },
        grid: {
            vertLines: { color: 'rgba(255,255,255,0.03)' },
            horzLines: { color: 'rgba(255,255,255,0.03)' }
        },
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        timeScale: { borderColor: 'rgba(255,255,255,0.06)', timeVisible: true },
        rightPriceScale: { borderColor: 'rgba(255,255,255,0.06)' }
    });
    state.candleSeries = state.chart.addCandlestickSeries({
        upColor: '#22c55e', downColor: '#ef4444',
        borderUpColor: '#22c55e', borderDownColor: '#ef4444',
        wickUpColor: '#22c55e', wickDownColor: '#ef4444'
    });
    state.volumeSeries = state.chart.addHistogramSeries({
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume'
    });
    state.chart.priceScale('volume').applyOptions({
        scaleMargins: { top: 0.85, bottom: 0 }
    });
    var ro = new ResizeObserver(function() {
        state.chart.applyOptions({ width: container.clientWidth });
    });
    ro.observe(container);
}

function updateChart(chartData) {
    if (!state.candleSeries || !chartData || !chartData.length) return;
    state.candleSeries.setData(chartData);
    var volData = chartData.map(function(d) {
        return {
            time: d.time,
            value: d.volume,
            color: d.close >= d.open ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'
        };
    });
    state.volumeSeries.setData(volData);
    state.chart.timeScale().fitContent();
}

function runAnalysis() {
    showLoading(true);
    var url = '/api/analyze?symbol=' + encodeURIComponent(state.asset) + '&market=' + state.market + '&tf=' + state.timeframe;
    fetch(url)
        .then(function(res) { return res.json(); })
        .then(function(data) {
            if (data.error) {
                alert(data.error);
                showLoading(false);
                return;
            }
            state.lastResult = data;
            renderAnalysis(data);
            showLoading(false);
        })
        .catch(function(e) {
            alert('Analysis failed: ' + e.message);
            showLoading(false);
        });
}

function renderAnalysis(data) {
    renderMetrics(data);
    updateChart(data.chart_data);
    $('#chartBadge').textContent = data.symbol + ' \u00B7 ' + data.timeframe;
    renderSignalCard(data);
    renderVotes(data);
    renderMTF(data.htf_results || []);
    renderLevels(data);
    renderPatterns(data.patterns || []);
    renderDivergences(data.divergences || []);
    renderIndicators(data.indicators || []);
}

function renderMetrics(d) {
    var chgCol = d.change_pct >= 0 ? 'var(--green)' : 'var(--red)';
    var chgArrow = d.change_pct >= 0 ? '\u25B2' : '\u25BC';
    $('#metricsRow').innerHTML =
        '<div class="metric-card fade-in"><div class="label">Asset</div><div class="value">' + d.symbol + '</div></div>' +
        '<div class="metric-card fade-in"><div class="label">Price</div><div class="value">' + formatPrice(d.price) + '</div></div>' +
        '<div class="metric-card fade-in"><div class="label">Change</div><div class="value" style="color:' + chgCol + '">' + chgArrow + ' ' + Math.abs(d.change_pct).toFixed(2) + '%</div></div>' +
        '<div class="metric-card fade-in"><div class="label">Signal</div><div class="value" style="color:' + d.color + '">' + d.emoji + ' ' + d.tier + '</div></div>' +
        '<div class="metric-card fade-in"><div class="label">Confidence</div><div class="value" style="color:' + d.color + '">' + d.confidence.toFixed(1) + '%</div></div>' +
        '<div class="metric-card fade-in"><div class="label">Indicators</div><div class="value">' + (d.total_signals || d.indicators.length) + '</div></div>';
}

function renderSignalCard(d) {
    var card = $('#signalCard');
    card.style.background = 'linear-gradient(135deg, ' + d.color + '15, ' + d.color + '05)';
    card.style.borderColor = d.color + '33';
    $('#sigEmoji').textContent = d.emoji;
    $('#sigTier').textContent = d.tier;
    $('#sigTier').style.color = d.color;
    $('#sigConf').textContent = d.confidence.toFixed(1) + '%';
    $('#sigConf').style.color = d.color;
    $('#sigPrice').textContent = formatPrice(d.price);
    var chgCol = d.change_pct >= 0 ? 'var(--green)' : 'var(--red)';
    var arrow = d.change_pct >= 0 ? '\u25B2' : '\u25BC';
    $('#sigChange').innerHTML = '<span style="color:' + chgCol + '">' + arrow + ' ' + Math.abs(d.change_pct).toFixed(2) + '%</span>';
    var fill = $('#confFill');
    fill.style.width = d.confidence + '%';
    fill.style.background = 'linear-gradient(90deg, ' + d.color + ', ' + d.color + 'aa)';
}

function renderVotes(d) {
    var total = d.buy_count + d.sell_count + d.neutral_count;
    $('#voteBars').innerHTML =
        voteBarHTML('Buy', d.buy_count, total, 'var(--green)') +
        voteBarHTML('Sell', d.sell_count, total, 'var(--red)') +
        voteBarHTML('Neutral', d.neutral_count, total, 'var(--text-muted)');
}

function voteBarHTML(label, count, total, color) {
    var pct = total ? (count / total * 100) : 0;
    return '<div class="vote-row"><div class="vote-label" style="color:' + color + '">' + label + '</div><div class="vote-bar-bg"><div class="vote-bar-fill" style="width:' + pct + '%;background:' + color + '"></div></div><div class="vote-count" style="color:' + color + '">' + count + '</div></div>';
}

function renderMTF(htfResults) {
    var el = $('#mtfResults');
    if (!htfResults.length) {
        el.innerHTML = '<p class="muted">No higher TF data</p>';
        return;
    }
    var html = '';
    htfResults.forEach(function(h) {
        html += '<div class="mtf-row"><span class="mtf-tf">' + h.timeframe.toUpperCase() + '</span><span class="mtf-signal" style="color:' + h.color + '">' + h.emoji + ' ' + h.tier + '</span><span style="color:' + h.color + ';font-size:0.8rem;font-weight:700;">' + h.confidence.toFixed(0) + '%</span></div>';
    });
    el.innerHTML = html;
}

function renderLevels(d) {
    var el = $('#levelsContent');
    var lv = d.levels;
    if (!lv) {
        el.innerHTML = '<p class="muted">Could not calculate levels</p>';
        return;
    }
    var isLong = d.direction === 'BUY';
    el.innerHTML =
        '<div class="level-row"><span class="level-label">Entry</span><span>' + formatPrice(lv.price) + '</span></div>' +
        '<div class="level-row"><span class="level-label" style="color:var(--red)">Stop Loss</span><span style="color:var(--red)">' + formatPrice(isLong ? lv.long_sl : lv.short_sl) + '</span></div>' +
        '<div class="level-row"><span class="level-label" style="color:var(--green)">Take Profit</span><span style="color:var(--green)">' + formatPrice(isLong ? lv.long_tp : lv.short_tp) + '</span></div>' +
        '<div class="level-row"><span class="level-label">R:R</span><span>1 : ' + lv.rr_ratio + '</span></div>' +
        '<div class="level-row"><span class="level-label">ATR</span><span>' + formatPrice(lv.atr) + '</span></div>';
}

function renderPatterns(patterns) {
    var el = $('#patternsContent');
    if (!patterns.length) {
        el.innerHTML = '<p class="muted">No candlestick patterns detected</p>';
        return;
    }
    var html = '';
    patterns.forEach(function(p) {
        var col = p.signal > 0 ? 'var(--green)' : p.signal < 0 ? 'var(--red)' : 'var(--text-muted)';
        var bg = p.signal > 0 ? 'var(--green-soft)' : p.signal < 0 ? 'var(--red-soft)' : 'transparent';
        html += '<div class="pattern-item" style="background:' + bg + '"><span class="pattern-icon">' + (p.value || 'P') + '</span><div><div class="pattern-name" style="color:' + col + '">' + p.name + '</div><div class="pattern-desc">' + p.desc + '</div></div></div>';
    });
    el.innerHTML = html;
}

function renderDivergences(divs) {
    var el = $('#divergencesContent');
    if (!divs.length) {
        el.innerHTML = '<p class="muted">No divergences detected</p>';
        return;
    }
    var html = '';
    divs.forEach(function(d) {
        var col = d.signal > 0 ? 'var(--green)' : 'var(--red)';
        var bg = d.signal > 0 ? 'var(--green-soft)' : 'var(--red-soft)';
        html += '<div class="divergence-item" style="background:' + bg + '"><span class="pattern-icon">' + (d.value || 'D') + '</span><div><div class="pattern-name" style="color:' + col + '">' + d.name + '</div><div class="pattern-desc">' + d.desc + '</div></div></div>';
    });
    el.innerHTML = html;
}

function renderIndicators(indicators) {
    var el = $('#indicatorsTable');
    if (!indicators.length) {
        el.innerHTML = '<p class="muted">No indicator data</p>';
        return;
    }
    var html = '';
    indicators.forEach(function(ind) {
        var sig = ind.signal;
        var badgeCol, badgeLabel;
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
        var barPct = Math.round(Math.abs(sig) * 100);
        var cat = ind.category || 'oscillator';
        html += '<div class="ind-row" data-category="' + cat + '"><div class="ind-name">' + ind.name + '</div><div class="ind-value">' + ind.value + '</div><div class="ind-bar"><div class="ind-bar-fill" style="width:' + barPct + '%;background:' + badgeCol + '"></div></div><div class="ind-signal"><span class="pill" style="background:' + badgeCol + '22;color:' + badgeCol + ';">' + badgeLabel + '</span></div><div class="ind-desc">' + ind.desc + '</div></div>';
    });
    el.innerHTML = html;
}

function runScanner() {
    $$('.nav-tab').forEach(function(t) { t.classList.remove('active'); });
    $$('.nav-tab')[1].classList.add('active');
    $('#singleView').classList.add('hidden');
    $('#scannerView').classList.remove('hidden');
    $('#assetGroup').classList.add('hidden');
    showLoading(true);
    var url = '/api/scan?market=' + state.market + '&tf=' + state.timeframe;
    fetch(url)
        .then(function(res) { return res.json(); })
        .then(function(data) {
            renderScanner(data.results);
            $('#scanCount').textContent = data.total + ' assets';
            showLoading(false);
        })
        .catch(function(e) {
            alert('Scan failed: ' + e.message);
            showLoading(false);
        });
}

function renderScanner(results) {
    var strong = results.filter(function(r) { return r.confidence >= 70; });
    var strongEl = $('#strongSignals');
    if (strong.length) {
        var shtml = '<h3 style="grid-column:1/-1;margin-bottom:8px;">Strong Signals</h3>';
        strong.forEach(function(r) { shtml += scanCardHTML(r); });
        strongEl.innerHTML = shtml;
    } else {
        strongEl.innerHTML = '';
    }
    var tableEl = $('#scannerTable');
    var thtml = '<div class="scan-table-row header"><span>Symbol</span><span>Price</span><span>Change</span><span>Signal</span><span>Confidence</span><span>Votes</span><span>MTF</span></div>';
    results.forEach(function(r) { thtml += scanTableRowHTML(r); });
    tableEl.innerHTML = thtml;
    $$('.scan-table-row:not(.header)').forEach(function(row, i) {
        row.addEventListener('click', function() {
            state.asset = results[i].symbol;
            $('#assetSelect').value = results[i].symbol;
            $$('.nav-tab').forEach(function(t) { t.classList.remove('active'); });
            $$('.nav-tab')[0].classList.add('active');
            $('#singleView').classList.remove('hidden');
            $('#scannerView').classList.add('hidden');
            $('#assetGroup').classList.remove('hidden');
            runAnalysis();
        });
    });
}

function scanCardHTML(r) {
    var chgCol = r.change_pct >= 0 ? 'var(--green)' : 'var(--red)';
    var arrow = r.change_pct >= 0 ? '\u25B2' : '\u25BC';
    return '<div class="scan-card" style="background:linear-gradient(135deg,' + r.color + '15,' + r.color + '05);border-color:' + r.color + '33;"><div class="sc-symbol">' + r.symbol + '</div><div class="sc-tier" style="color:' + r.color + '">' + r.emoji + ' ' + r.tier + '</div><div class="sc-price">' + formatPrice(r.price) + '</div><div class="sc-conf" style="color:' + r.color + '">' + r.confidence.toFixed(1) + '%</div><div class="sc-change" style="color:' + chgCol + '">' + arrow + ' ' + Math.abs(r.change_pct).toFixed(2) + '%</div></div>';
}

function scanTableRowHTML(r) {
    var chgCol = r.change_pct >= 0 ? 'var(--green)' : 'var(--red)';
    var arrow = r.change_pct >= 0 ? '\u25B2' : '\u25BC';
    var mtfAlign = r.htf_results && r.htf_results.length ? r.htf_results.map(function(h) { return h.emoji; }).join(' ') : '\u2014';
    return '<div class="scan-table-row"><span style="font-weight:700;">' + r.symbol + '</span><span style="font-family:JetBrains Mono,monospace;font-size:0.85rem;">' + formatPrice(r.price) + '</span><span style="color:' + chgCol + ';font-weight:600;">' + arrow + ' ' + Math.abs(r.change_pct).toFixed(2) + '%</span><span style="color:' + r.color + ';font-weight:700;">' + r.emoji + ' ' + r.tier + '</span><span style="color:' + r.color + ';font-weight:700;font-family:JetBrains Mono,monospace;">' + r.confidence.toFixed(1) + '%</span><span style="font-size:0.8rem;">' + r.buy_count + '/' + r.sell_count + '/' + r.neutral_count + '</span><span>' + mtfAlign + '</span></div>';
}

function sendAlert() {
    if (!state.lastResult) {
        alert('Run an analysis first!');
        return;
    }
    var url = '/api/alert?symbol=' + encodeURIComponent(state.asset) + '&market=' + state.market + '&tf=' + state.timeframe;
    fetch(url, { method: 'POST' })
        .then(function() { alert('Alert sent!'); })
        .catch(function(e) { alert('Failed: ' + e.message); });
}

function showLoading(show) {
    var el = $('#loadingOverlay');
    if (show) { el.classList.add('active'); } else { el.classList.remove('active'); }
}

function formatPrice(price) {
    if (price === null || price === undefined) return '\u2014';
    var p = parseFloat(price);
    if (isNaN(p)) return '\u2014';
    if (p >= 1000) return p.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (p >= 1) return p.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
    if (p >= 0.01) return p.toFixed(4);
    return p.toFixed(6);
}
