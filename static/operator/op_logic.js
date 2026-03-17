document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    loadOperatorInfo();
    loadDownloads();
    
    document.getElementById('flightForm').addEventListener('submit', handleFlightSubmit);
    document.getElementById('feedbackForm').addEventListener('submit', handleFeedbackSubmit);
});

function setupNavigation() {
    const links = document.querySelectorAll('.side-nav a:not(.logout-link)');
    links.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            links.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            const target = link.getAttribute('href').substring(1);
            document.querySelectorAll('.dashboard-section').forEach(s => s.style.display = 'none');
            document.getElementById(target).style.display = 'block';
        });
    });
}

function loadOperatorInfo() {
    // Simular carga desde sesión (el backend debería servir esto)
    document.getElementById('op_name').innerText = "OP: operador1 (Operador de Prueba)";
}

async function handleFlightSubmit(e) {
    e.preventDefault();
    const data = {
        detections: document.getElementById('detections').value,
        precision: document.getElementById('precision').value,
        comments: document.getElementById('comments').value
    };
    
    // Simular API call
    console.log("Registrando vuelo:", data);
    alert("BITÁCORA CERRADA EXITOSAMENTE. Datos enviados al Centro de Comando.");
    e.target.reset();
}

async function handleFeedbackSubmit(e) {
    e.preventDefault();
    const type = document.getElementById('fb_type').value;
    const content = document.getElementById('fb_content').value;
    const status = document.getElementById('fb_status');

    status.innerText = "Enviando informe...";
    status.style.color = "var(--primary-cyan)";

    // Simular API call
    setTimeout(() => {
        status.innerText = "¡Informe enviado al Dueño exitosamente!";
        status.style.color = "var(--matrix-green)";
        e.target.reset();
    }, 1000);
}

function loadDownloads() {
    const table = document.getElementById('downloadTable');
    const items = [
        { name: "Modelo YOLOv10 - IED/Personnel (High Precision)", version: "v4.2.0", date: "2026-03-17", status: "Avalado" },
        { name: "SISMA Ground Suite - Local Installer", version: "v1.8.5", date: "2026-03-15", status: "Estable" }
    ];

    table.innerHTML = items.map(i => `
        <tr>
            <td><strong>${i.name}</strong></td>
            <td><code>${i.version}</code></td>
            <td>${i.date}</td>
            <td><span style="color:var(--matrix-green)">${i.status}</span></td>
            <td><button class="btn-admin" style="font-size:0.7rem; padding:5px 10px;">BAJAR</button></td>
        </tr>
    `).join('');
}
