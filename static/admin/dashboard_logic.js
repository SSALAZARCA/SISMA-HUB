let trainingChart;

document.addEventListener('DOMContentLoaded', () => {
    initApp();
    initChart();
    refreshData();
    setInterval(refreshData, 5000); // 5s refresh
    startClock();
});

function initApp() {
    // Navegación Modular (Single Page feel)
    const navLinks = document.querySelectorAll('.side-nav a:not(.logout-link)');
    const sections = document.querySelectorAll('.dashboard-section');

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href').substring(1);
            
            // Actualizar UI
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // Swapping Módulos
            sections.forEach(s => s.style.display = 'none');
            const targetSection = document.getElementById(targetId);
            if (targetSection) {
                targetSection.style.display = 'block';
                addLog(`Accediendo al módulo: ${targetId.toUpperCase()}`);
            }
        });
    });
}

function startClock() {
    const clockEl = document.getElementById('digitalClock');
    setInterval(() => {
        const now = new Date();
        clockEl.innerText = now.getUTCHours().toString().padStart(2, '0') + ":" + 
                            now.getUTCMinutes().toString().padStart(2, '0') + ":" + 
                            now.getUTCSeconds().toString().padStart(2, '0') + " UTC";
    }, 1000);
}

function initChart() {
    const chartEl = document.getElementById('trainingChart');
    if (!chartEl) return;
    const ctx = chartEl.getContext('2d');
    trainingChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'mAP50 (Fuerza)',
                    data: [],
                    borderColor: '#00D1FF',
                    backgroundColor: 'rgba(0, 209, 255, 0.1)',
                    borderWidth: 3,
                    pointRadius: 4,
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Recall (Sensibilidad)',
                    data: [],
                    borderColor: '#00FF94',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' } },
                x: { grid: { display: false }, ticks: { color: '#94A3B8' } }
            },
            plugins: {
                legend: { position: 'top', labels: { color: '#E2E8F0', font: { family: 'Rajdhani', size: 12 } } }
            }
        }
    });
}

async function refreshData() {
    try {
        await Promise.all([fetchLicenses(), fetchTraining(), fetchVault(), fetchOperators(), fetchConfig()]);
        // addLog("Sincronización de núcleos exitosa.");
    } catch (err) {
        addLog("ERR: Error de enlace con DB maestra.", "error");
    }
}

async function fetchConfig() {
    const resp = await fetch('/api/admin/config/webhook');
    const data = await resp.json();
    
    if (document.getElementById('webhookUrlInput')) {
        document.getElementById('webhookUrlInput').value = data.webhook_url;
    }
    if (document.getElementById('hubIdConfig')) {
        document.getElementById('hubIdConfig').innerText = data.hub_id;
    }
    if (document.getElementById('hubStatusConfig')) {
        document.getElementById('hubStatusConfig').innerText = data.status.toUpperCase();
    }
}

function copyWebhook() {
    const input = document.getElementById('webhookUrlInput');
    if (!input) return;
    
    input.select();
    input.setSelectionRange(0, 99999); // For mobile devices
    navigator.clipboard.writeText(input.value);
    
    addLog("Webhook copiado al portapapeles. Listo para enlace táctico.");
    
    // Feedback visual en el botón
    const btn = event.target.closest('button');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-check"></i> ¡COPIADO!';
    btn.style.background = 'var(--matrix-green)';
    btn.style.color = 'black';
    
    setTimeout(() => {
        btn.innerHTML = originalText;
        btn.style.background = '';
        btn.style.color = '';
    }, 2000);
}

async function fetchOperators() {
    const resp = await fetch('/api/admin/operators/list');
    const data = await resp.json();
    const tbody = document.getElementById('operatorTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    data.forEach(op => {
        const tr = document.createElement('tr');
        const hwidDisplay = op.assigned_hwid ? `<small><code>${op.assigned_hwid}</code></small>` : `<span style="color:#94A3B8; font-size:0.7rem;">(Pendiente de Vinculación)</span>`;
        
        // Calcular si está vencido o activo con seguridad contra nulls
        const expStr = op.expiration_date || new Date().toISOString();
        const expDate = new Date(expStr);
        const isExpired = new Date() > expDate;
        const statusColor = isExpired ? 'var(--accent-red)' : 'var(--matrix-green)';
        const statusText = isExpired ? 'CADUCADO' : (op.status || 'ACTIVO').toUpperCase();

        tr.innerHTML = `
            <td><strong>${op.full_name || 'Sin Nombre'}</strong></td>
            <td><code>${op.username}</code></td>
            <td>${hwidDisplay}</td>
            <td>
                <div style="color:${statusColor}; font-size:0.75rem; font-weight:bold;">${statusText}</div>
                <div style="font-size:0.65rem; color:#94A3B8;">Expira: ${expStr.split(' ')[0]}</div>
            </td>
            <td>
                <div style="display:flex; gap:5px;">
                    <form action="/api/admin/operators/update_time" method="post" style="display:flex; gap:2px;">
                        <input type="hidden" name="op_id" value="${op.id}">
                        <select name="days" style="background:#0F172A; border:1px solid #1E293B; color:white; font-size:0.65rem;">
                            <option value="30">+30d</option>
                            <option value="90">+90d</option>
                        </select>
                        <button type="submit" class="btn-action" title="Extender Tiempo" style="padding:2px 5px;"><i class="fas fa-clock-rotate-left"></i></button>
                    </form>
                    <form action="/api/admin/operators/delete" method="post">
                        <input type="hidden" name="op_id" value="${op.id}">
                        <button type="submit" class="btn-action" style="padding:2px 5px; background:transparent; border:1px solid var(--accent-red); color:var(--accent-red);"><i class="fas fa-user-slash"></i></button>
                    </form>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function fetchVault() {
    const resp = await fetch('/api/data/vault');
    const data = await resp.json();
    const tbody = document.getElementById('vaultTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    data.forEach(m => {
        const tr = document.createElement('tr');
        const shortHash = m.sha256_hash ? m.sha256_hash.substring(0, 8) + '...' + m.sha256_hash.substring(m.sha256_hash.length - 8) : 'N/A';
        
        tr.innerHTML = `
            <td><code style="color:var(--primary-cyan)">${m.version}</code></td>
            <td>
                <div style="font-weight:bold;">${m.filename}</div>
                <div style="font-size:0.6rem; color:#94A3B8; font-family:'Fira Code'; cursor:pointer;" title="Click para copiar Firma Completa" onclick="navigator.clipboard.writeText('${m.sha256_hash}'); addLog('Firma copiada al portapapeles');">
                    <i class="fas fa-fingerprint"></i> ${shortHash}
                </div>
            </td>
            <td>
                <span style="color:var(--matrix-green); font-size:0.7rem; padding:2px 6px; border:1px solid var(--matrix-green); border-radius:4px;">AVALADO</span>
            </td>
            <td>
                <div style="font-size:0.75rem;">${m.upload_date}</div>
                <a href="/api/ops/vault/download/${m.id}" class="btn-action" style="padding:4px 8px; font-size:0.7rem; margin-top:5px; display:inline-block; text-decoration:none;">
                    <i class="fas fa-download"></i> DESCARGAR
                </a>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function fetchLicenses() {
    const resp = await fetch('/api/data/licenses');
    const data = await resp.json();
    const tbody = document.getElementById('licenseTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    data.forEach(lic => {
        const tr = document.createElement('tr');
        const statusColor = lic.status === 'Activo' ? 'var(--matrix-green)' : (lic.status === 'Pendiente' ? '#FFD700' : 'var(--accent-red)');
        
        tr.innerHTML = `
            <td title="${lic.machine_id}"><code>${lic.short_code}</code></td>
            <td><strong>${lic.owner_name || 'S/N'}</strong><br><small>${lic.hostname}</small></td>
            <td><small>${lic.os_version}</small></td>
            <td><span style="color:${statusColor}; font-weight:700; font-size:0.75rem;">${lic.status.toUpperCase()}</span></td>
            <td>${lic.days_remaining}d<br><small>${lic.expiration_date || 'INF'}</small></td>
            <td>
                <form action="/admin/action" method="post" style="display:flex; gap:8px;">
                    <input type="hidden" name="id" value="${lic.id}">
                    <button type="submit" name="act" value="on" class="btn-action" style="padding:4px 8px; font-size:0.7rem;">ALT</button>
                    <button type="submit" name="act" value="off" class="btn-action" style="padding:4px 8px; font-size:0.7rem; background:transparent; border:1px solid var(--accent-red); color:var(--accent-red);">KILL</button>
                </form>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function fetchTraining() {
    const resp = await fetch('/api/data/training');
    const data = await resp.json();
    if (data.length === 0) return;

    const latest = data[0];
    if (document.getElementById('current_epoch')) document.getElementById('current_epoch').innerText = latest.epoch;
    if (document.getElementById('current_map')) document.getElementById('current_map').innerText = (latest.map50 * 100).toFixed(1) + '%';
    if (document.getElementById('current_recall')) document.getElementById('current_recall').innerText = (latest.recall * 100).toFixed(1) + '%';
    if (document.getElementById('raw_effort')) document.getElementById('raw_effort').innerText = latest.raw_effort || '88';

    if (trainingChart) {
        const chartData = [...data].reverse();
        trainingChart.data.labels = chartData.map(d => `E${d.epoch}`);
        trainingChart.data.datasets[0].data = chartData.map(d => d.map50);
        trainingChart.data.datasets[1].data = chartData.map(d => d.recall);
        trainingChart.update('none'); // No animation for periodic updates
    }
}

function addLog(msg, type = "info") {
    const terminal = document.getElementById('logTerminal');
    if (!terminal) return;
    const line = document.createElement('div');
    line.className = 'log-line';
    const now = new Date().toLocaleTimeString();
    line.innerHTML = `<span style="color:#475569">[${now}]</span> ${type === 'error' ? '<span style="color:var(--accent-red)">[ALERT]</span> ' : '<span style="color:var(--primary-cyan)">[EVENT]</span> '} ${msg}`;
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
}
