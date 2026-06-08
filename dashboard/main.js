// Kronos Command Center - Main Logic
const API_URL = 'http://localhost:8000';

// DOM Elements
const stats = {
    files: document.getElementById('stat-files'),
    chunks: document.getElementById('stat-chunks'),
    entities: document.getElementById('stat-entities'),
    savings: document.getElementById('stat-savings'),
    topSavings: document.getElementById('top-savings')
};

const jobList = document.getElementById('job-list');
const liveFeed = document.getElementById('live-feed');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const noJobsMsg = document.getElementById('no-jobs');

// State
let jobs = {};

// 1. Initial Data Fetch
async function refreshStats() {
    try {
        const resp = await fetch(`${API_URL}/stats`);
        if (!resp.ok) throw new Error('Stats API offline');
        const data = await resp.ok ? await resp.json() : {};

        stats.files.textContent = data.total_files || '0';
        stats.chunks.textContent = data.total_chunks || '0';
        stats.entities.textContent = data.total_entities || '0';

        // Mocked or calculated savings for now
        stats.savings.textContent = '92.4%';
        stats.topSavings.textContent = '145k';
    } catch (err) {
        console.error('Fetch error:', err);
    }
}

// 2. Connect to SSE Stream
function connectStream() {
    const stream = new EventSource(`${API_URL}/stream`);

    stream.onopen = () => {
        statusDot.style.background = 'var(--success)';
        statusText.textContent = 'Online';
        addLog('info', 'Povezan na Kronos stream.');
    };

    stream.onerror = () => {
        statusDot.style.background = 'var(--error)';
        statusText.textContent = 'Veza prekinuta';
        stream.close();
        setTimeout(connectStream, 5000); // Reconnect loop
    };

    // Handle Job Updates
    stream.addEventListener('job_update', (e) => {
        const data = JSON.parse(e.data);
        updateJobUI(data);
    });

    // Handle Logic Logs
    stream.addEventListener('log', (e) => {
        const data = JSON.parse(e.data);
        addLog(data.level.toLowerCase(), data.message);
    });
}

function updateJobUI(job) {
    if (noJobsMsg) noJobsMsg.style.display = 'none';

    let jobEl = document.getElementById(`job-${job.job_id}`);

    if (!jobEl) {
        jobEl = document.createElement('div');
        jobEl.id = `job-${job.job_id}`;
        jobEl.className = 'job-card';
        jobList.prepend(jobEl);
    }

    jobEl.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <div style="font-weight: 600; font-size: 14px;">Zadatak: ${job.job_id.substring(0, 8)}...</div>
                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">${job.message || 'Procesiranje...'}</div>
            </div>
            <div style="font-size: 12px; font-weight: bold; color: ${job.status === 'completed' ? 'var(--success)' : 'var(--accent-blue)'}">
                ${job.status.toUpperCase()}
            </div>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: ${job.progress}%"></div>
        </div>
    `;

    if (job.status === 'completed') {
        setTimeout(() => {
            refreshStats(); // Update counts after ingest
        }, 1000);
    }
}

function addLog(level, message) {
    const time = new Date().toLocaleTimeString('hr-HR', { hour12: false });
    const logEl = document.createElement('div');
    logEl.className = 'log-entry';
    logEl.innerHTML = `
        <span class="log-time">[${time}]</span>
        <span class="log-level-${level}">${level.toUpperCase()}</span> 
        ${message}
    `;

    liveFeed.prepend(logEl);

    // Limit log count
    if (liveFeed.children.length > 50) {
        liveFeed.removeChild(liveFeed.lastChild);
    }
}

// 3. UI Interactions
document.getElementById('btn-reindex').addEventListener('click', async () => {
    if (confirm('Želiš li pokrenuti potpuno reindeksiranje workspacea? Ovo može potrajati.')) {
        try {
            const resp = await fetch(`${API_URL}/jobs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: 'ingest',
                    params: { path: '.', recursive: true },
                    priority: 10
                })
            });
            const data = await resp.json();
            addLog('job', `Novi ingest posao poslan: ${data.id}`);
        } catch (err) {
            addLog('error', `Greška pri slanju posla: ${err.message}`);
        }
    }
});

// Init
refreshStats();
connectStream();
setInterval(refreshStats, 30000); // Periodic stats update

// ==========================================
// VIEW ROUTING & KNOWLEDGE BASE LOGIC
// ==========================================

const views = {
    dashboard: document.getElementById('view-dashboard'),
    knowledge: document.getElementById('view-knowledge'),
    agenticLogs: document.getElementById('view-agentic-logs'),
    graph: document.getElementById('view-graph')
};
const navBtns = {
    dashboard: document.getElementById('nav-dashboard'),
    knowledge: document.getElementById('nav-knowledge'),
    agenticLogs: document.getElementById('nav-agentic-logs'),
    graph: document.getElementById('nav-graph')
};

function switchView(viewName) {
    // Sakrij sve views i resetiraj tipke
    Object.values(views).forEach(v => { if (v) v.classList.remove('active'); });
    Object.values(navBtns).forEach(v => {
        if (v) {
            v.classList.remove('btn');
            v.classList.add('btn-outline');
        }
    });

    // Prikaži željeni view
    if (views[viewName]) views[viewName].classList.add('active');
    if (navBtns[viewName]) {
        navBtns[viewName].classList.remove('btn-outline');
        navBtns[viewName].classList.add('btn');
    }
}

// Event Listeners za navigaciju
if (navBtns.dashboard) navBtns.dashboard.addEventListener('click', () => switchView('dashboard'));
if (navBtns.knowledge) navBtns.knowledge.addEventListener('click', () => switchView('knowledge'));
if (navBtns.agenticLogs) {
    navBtns.agenticLogs.addEventListener('click', () => {
        switchView('agenticLogs');
        fetchAgenticLogs(); // Auto load first time
    });
}
if (navBtns.graph) {
    navBtns.graph.addEventListener('click', () => {
        switchView('graph');
        if (!window.graphInitialized) {
            initGraph();
            window.graphInitialized = true;
        }
    });
}

// ----------------------------------------
// MICELIJ (FORCE GRAPH) LOGIC
// ----------------------------------------
async function initGraph() {
    const container = document.getElementById('graph-container');
    container.innerHTML = '<div style="text-align:center; padding: 40px; color: var(--text-secondary);"><i data-lucide="loader" class="logo-icon"></i> Kultiviram micelij iz memorije... Mogu potrajati par sekundi.</div>';
    lucide.createIcons();

    try {
        const resp = await fetch(`${API_URL}/graph_data`);
        if (!resp.ok) throw new Error("Ne mogu dohvatiti podatke za graf.");
        const data = await resp.json();

        container.innerHTML = ''; // Clear loading

        const myGraph = ForceGraph()(container)
            .graphData(data)
            .nodeLabel('label')
            .nodeColor(node => {
                if (node.group === 0) return '#a100ff'; // Kronos root
                if (node.group === 1) return '#00d2ff'; // Project
                if (node.group === 2) return '#ffffff'; // File
                if (node.group === 3) return '#00ff88'; // Entity
                return '#b0b3b8'; // fallback
            })
            // Root has size 10, Projects 6, Entities 4
            .nodeRelSize(4)
            .nodeVal(node => {
                if (node.group === 0) return 10;
                if (node.group === 1) return 6;
                return 4;
            })
            .linkColor(() => 'rgba(255, 255, 255, 0.15)')
            .linkWidth(link => link.value || 1)
            .backgroundColor('transparent'); // We overlay it inside the view

        // Optional: auto-fit after layout stabilizes
        setTimeout(() => {
            myGraph.zoomToFit(400);
        }, 3000);

    } catch (e) {
        container.innerHTML = `<div style="color: var(--error); padding: 20px; text-align:center;">Greška pri učitavanju grafa: ${e.message}</div>`;
    }
}

// Agentic Logs UI Logic
async function fetchAgenticLogs() {
    const container = document.getElementById('agentic-logs-container');
    container.innerHTML = '<div style="text-align:center; padding: 40px;"><i data-lucide="loader" class="logo-icon"></i> Učitavam agentic logove...</div>';
    lucide.createIcons();

    try {
        const resp = await fetch(`${API_URL}/agentic_logs`);
        if (!resp.ok) throw new Error("Ne mogu dohvatiti agentic logove.");
        const data = await resp.json();

        if (!data.logs || data.logs.length === 0) {
            container.innerHTML = '<div style="text-align:center; color: var(--text-secondary); padding: 40px; background: var(--card-bg); border: 1px dashed var(--card-border); border-radius: 12px;">Nema zabilježenih aktivnosti agenata.</div>';
            return;
        }

        container.innerHTML = data.logs.map(log => {
            const utilization = ((log.tokens / log.budget) * 100).toFixed(1);
            const eventsHtml = log.events.map(ev => {
                let color = "var(--text-secondary)";
                if (ev.includes("ADD")) color = "var(--success)";
                if (ev.includes("REJECTED")) color = "var(--warning)";
                if (ev.includes("duplicate")) color = "var(--accent-blue)";

                return `<div style="color: ${color}; padding: 2px 0;">${ev}</div>`;
            }).join('');

            return `
            <div class="stat-card" style="display: flex; flex-direction: column; gap: 10px;">
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid var(--card-border); padding-bottom: 10px; align-items: flex-start;">
                    <div>
                        <strong style="color: var(--accent-blue); font-size: 15px;">Query: "${log.query}"</strong>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                            ${log.timestamp} | <span style="color: #fff">${log.latency}ms</span> | ${log.method}
                        </div>
                    </div>
                </div>
                <div style="display: flex; gap: 15px; font-size: 12px; color: var(--text-secondary)">
                    <span style="background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px;">
                        <b style="color: #fff">Tokens:</b> <span style="color: ${utilization > 90 ? 'var(--warning)' : 'var(--success)'}">${log.tokens} / ${log.budget} (${utilization}%)</span>
                    </span>
                    <span style="background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px;">
                        <b style="color: #fff">Items:</b> ${log.items_count} context chunks
                    </span>
                    <span style="background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px;">
                        <b style="color: #fff">Mode:</b> ${log.mode}
                    </span>
                </div>
                <div style="margin-top: 5px; max-height: 200px; overflow-y: auto; background: rgba(0,0,0,0.5); padding: 12px; border-radius: 6px; font-family: 'Consolas', monospace; font-size: 11px; border: 1px solid rgba(255,255,255,0.05);">
                    ${eventsHtml || '<div style="color: var(--text-secondary); font-style: italic;">No audit events collected.</div>'}
                </div>
            </div>
            `;
        }).join('');
    } catch (e) {
        container.innerHTML = `<div style="color: var(--error); padding: 20px; background: rgba(255,0,0,0.1); border-radius: 8px;">Greška: ${e.message}</div>`;
    }
}

const btnRefreshAgentic = document.getElementById('btn-refresh-agentic');
if (btnRefreshAgentic) btnRefreshAgentic.addEventListener('click', fetchAgenticLogs);

const btnClearAgentic = document.getElementById('btn-clear-agentic');
if (btnClearAgentic) {
    btnClearAgentic.addEventListener('click', () => {
        const container = document.getElementById('agentic-logs-container');
        if (container) container.innerHTML = '<div style="text-align:center; color: var(--text-secondary); padding: 40px; background: var(--card-bg); border: 1px dashed var(--card-border); border-radius: 12px;">Prikaz očišćen.</div>';
    });
}

const tableBody = document.getElementById('knowledge-table-body');

// Učitavanje Entiteta
document.getElementById('btn-load-entities').addEventListener('click', async () => {
    tableBody.innerHTML = '<tr><td colspan="3" style="text-align:center; padding: 40px;"><i data-lucide="loader" class="logo-icon"></i> Učitavam entitete iz memorije...</td></tr>';
    lucide.createIcons();
    try {
        const resp = await fetch(`${API_URL}/entities`);
        if (!resp.ok) throw new Error("Ne mogu dohvatiti entitete.");
        const data = await resp.json();

        if (!data.entities || data.entities.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="3" style="text-align:center; color: var(--text-secondary); padding: 40px;">Baza je trenutno prazna. Nema pronađenih entiteta.</td></tr>';
            return;
        }

        tableBody.innerHTML = data.entities.map(e => `
            <tr>
                <td style="width: 20%;">
                    <span class="badge">${e.type}</span><br>
                    <span style="font-size: 11px; color: var(--text-secondary); display: inline-block; margin-top: 5px;">${e.file}</span>
                </td>
                <td style="width: 55%;">
                    <div style="font-weight: 500; margin-bottom: 6px;">${e.content}</div>
                    <div style="font-size: 12px; color: var(--text-secondary); border-left: 2px solid rgba(255,255,255,0.1); padding-left: 8px;">${e.preview || 'Nema pregleda koda'}</div>
                </td>
                <td style="width: 25%;">
                    <span style="font-size: 11px; padding: 4px 8px; background: rgba(255,255,255,0.05); border-radius: 4px;">Source: ${e.file}</span>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        tableBody.innerHTML = `<tr><td colspan="3" style="color: var(--error); padding: 20px;">Greška: ${e.message}</td></tr>`;
    }
});

// Učitavanje Odluka
document.getElementById('btn-load-decisions').addEventListener('click', async () => {
    tableBody.innerHTML = '<tr><td colspan="3" style="text-align:center; padding: 40px;"><i data-lucide="loader" class="logo-icon"></i> Učitavam Odluke...</td></tr>';
    lucide.createIcons();
    try {
        const resp = await fetch(`${API_URL}/decisions`);
        if (!resp.ok) throw new Error("Ne mogu dohvatiti odluke.");
        const data = await resp.json();

        if (!data.decisions || data.decisions.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="3" style="text-align:center; color: var(--text-secondary); padding: 40px;">Nema donesenih odluka u sustavu.</td></tr>';
            return;
        }

        tableBody.innerHTML = data.decisions.map(d => `
            <tr>
                <td style="width: 20%;">
                    <span class="badge" style="background: rgba(0, 255, 136, 0.1); border-color: rgba(0, 255, 136, 0.2); color: var(--success);">
                        ODLUKA #${d.id}
                    </span>
                </td>
                <td style="width: 55%;">
                    <div style="font-weight: 500; color: #fff; margin-bottom: 4px;">${d.decision_text}</div>
                    <div style="font-size: 11px; color: var(--text-secondary);">
                        Vrijedi od: <span style="color: #fff;">${d.valid_from}</span> | 
                        Do: <span style="color: #fff;">${d.valid_to || 'Trajno / Trenutno'}</span>
                    </div>
                </td>
                <td style="width: 25%;">
                    <span style="font-size: 11px; padding: 4px 8px; background: rgba(0, 210, 255, 0.1); border-radius: 4px; color: var(--accent-blue);">
                        Proces: ${d.project || 'Globalno'}
                    </span>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        tableBody.innerHTML = `<tr><td colspan="3" style="color: var(--error); padding: 20px;">Greška: ${e.message}</td></tr>`;
    }
});
