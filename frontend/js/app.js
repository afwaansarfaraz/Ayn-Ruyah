/**
 * AYN RUYAH — Main Bootstrapper & Lifecycle Controller
 */

window.addEventListener('DOMContentLoaded', async () => {
    // 1. Load public directory of hospital workspaces
    await loadHospitalsList();

    // 2. Check for existing login session
    const user = State.getActiveUser();
    const tenant = State.getActiveTenant();

    if (user && tenant) {
        try {
            const authData = await RetinaLensAPI.getCurrentUser();
            if (authData && authData.authenticated && authData.user) {
                State.setActiveUser(authData.user);
                if (authData.hospital) State.setActiveTenant(authData.hospital);
                updateWorkspaceUI();
                navigate('app-shell');
                switchNav('dashboard');
            } else {
                State.clearAuth();
                navigate('login-page');
            }
        } catch (err) {
            console.error('Session verification error during startup:', err);
            showNotification('Unable to verify session with server. Network/server error.', 'warning');
            updateWorkspaceUI();
            navigate('app-shell');
            switchNav('dashboard');
        }
    } else {
        navigate('login-page');
    }

    // 3. Global keyboard listener for modal closing (Escape key)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.app-modal').forEach(m => {
                m.classList.add('hidden');
                m.classList.remove('flex');
            });
        }
    });
});
