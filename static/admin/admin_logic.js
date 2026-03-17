document.getElementById('loginForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const user = document.getElementById('username').value.trim();
    const pass = document.getElementById('password').value.trim();
    const errorMsg = document.getElementById('errorMsg');

    // Validación para Superadministrador (santiago.salazar)
    if (user.toLowerCase() === 'santiago.salazar' && pass === 'Ssc841209*') {
        errorMsg.style.color = 'var(--matrix-green)';
        errorMsg.innerText = 'AUTENTICACIÓN EXITOSA. ACCEDIENDO...';
        
        // Simular redirección al dashboard (que será cargado dinámicamente o por servidor)
        setTimeout(() => {
            window.location.href = '/admin/dashboard'; // El servidor controlará esta ruta
        }, 1500);
    } else {
        errorMsg.innerText = 'CREDENCIALES INVÁLIDAS. ACCESO RECHAZADO.';
    }
});
