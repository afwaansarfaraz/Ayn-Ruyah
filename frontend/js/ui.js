/**
 * AYN RUYAH — User Interface & Navigation Controller
 */

let currentNavToken = 0;

function invalidateNavigationToken() {
    currentNavToken++;
    return currentNavToken;
}

function getNavigationToken() {
    return currentNavToken;
}

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

window.escapeHtml = escapeHtml;
window.getNavigationToken = getNavigationToken;
window.invalidateNavigationToken = invalidateNavigationToken;

function navigate(pageId) {
    document.querySelectorAll('.app-page').forEach(p => p.classList.add('hidden'));
    const target = document.getElementById(pageId);
    if (target) {
        target.classList.remove('hidden');
    }
}

function switchNav(tabName) {
    const token = invalidateNavigationToken();

    // 1. Update breadcrumb
    const breadcrumbEl = document.getElementById('breadcrumb-current-tab');
    const tabTitles = {
        'dashboard': 'Clinical Dashboard',
        'patients': 'Diabetic Patients',
        'screening': 'AI Retinal Screening',
        'analytics': 'Clinical Analytics',
        'reports': 'Screening Reports',
        'settings': 'Hospital Settings'
    };
    if (breadcrumbEl) {
        breadcrumbEl.textContent = tabTitles[tabName] || tabName;
    }

    // 2. Update active state in sidebar nav items
    document.querySelectorAll('.nav-btn').forEach(btn => {
        if (btn.dataset.tab === tabName) {
            btn.classList.add('active', 'bg-[#EAF4FF]', 'text-[#087E8B]', 'border-[#087E8B]/20');
            btn.classList.remove('text-[#4B6584]', 'hover:bg-[#EAF4FF]');
        } else {
            btn.classList.remove('active', 'bg-[#EAF4FF]', 'text-[#087E8B]', 'border-[#087E8B]/20');
            btn.classList.add('text-[#4B6584]', 'hover:bg-[#EAF4FF]');
        }
    });

    // 3. Load tab content with cancellation token
    switch (tabName) {
        case 'dashboard':
            loadDashboardContent(token);
            break;
        case 'patients':
            loadPatientsContent(token);
            break;
        case 'screening':
            loadScreeningContent(token);
            break;
        case 'analytics':
            loadAnalyticsContent(token);
            break;
        case 'reports':
            loadReportsContent(token);
            break;
        case 'settings':
            loadSettingsContent(token);
            break;
        default:
            loadDashboardContent(token);
    }
}

function toggleMobileSidebar() {
    const sidebar = document.getElementById('main-sidebar');
    const backdrop = document.getElementById('mobile-sidebar-backdrop');
    if (sidebar) {
        const isOpen = !sidebar.classList.contains('-translate-x-full');
        if (isOpen) {
            sidebar.classList.add('-translate-x-full');
            backdrop?.classList.add('hidden');
        } else {
            sidebar.classList.remove('-translate-x-full');
            backdrop?.classList.remove('hidden');
        }
    }
}

function closeMobileSidebar() {
    const sidebar = document.getElementById('main-sidebar');
    const backdrop = document.getElementById('mobile-sidebar-backdrop');
    if (sidebar) {
        sidebar.classList.add('-translate-x-full');
        backdrop?.classList.add('hidden');
    }
}

let _activeModalOpener = null;
const _modalTraps = new Map();

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    
    _activeModalOpener = document.activeElement;
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.classList.remove('hidden');
    modal.classList.add('flex');

    const focusable = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusable.length > 0) {
        const firstEl = focusable[0];
        const lastEl = focusable[focusable.length - 1];
        setTimeout(() => firstEl.focus(), 50);

        const trapHandler = (e) => {
            if (e.key === 'Tab') {
                if (e.shiftKey) {
                    if (document.activeElement === firstEl) {
                        e.preventDefault();
                        lastEl.focus();
                    }
                } else {
                    if (document.activeElement === lastEl) {
                        e.preventDefault();
                        firstEl.focus();
                    }
                }
            }
        };
        modal.addEventListener('keydown', trapHandler);
        _modalTraps.set(modalId, trapHandler);
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    const trapHandler = _modalTraps.get(modalId);
    if (trapHandler) {
        modal.removeEventListener('keydown', trapHandler);
        _modalTraps.delete(modalId);
    }

    modal.classList.add('hidden');
    modal.classList.remove('flex');

    if (_activeModalOpener && typeof _activeModalOpener.focus === 'function') {
        _activeModalOpener.focus();
        _activeModalOpener = null;
    }
}

function updateAgeFromDob(dobStr) {
    if (!dobStr) return;
    const parts = dobStr.split('-');
    if (parts.length !== 3) return;
    const birthDate = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    if (isNaN(birthDate.getTime())) return;
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const m = today.getMonth() - birthDate.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
        age--;
    }
    const ageInput = document.getElementById('reg-age');
    if (ageInput && age >= 0) {
        ageInput.value = age;
    }
}

function showNotification(message, type = 'info') {
    const container = document.getElementById('notification-toast-container');
    if (!container) return;

    const icons = {
        success: 'fa-check-circle',
        error:   'fa-circle-xmark',
        warning: 'fa-triangle-exclamation',
        info:    'fa-circle-info',
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas ${icons[type] || icons.info} text-lg"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">${escapeHtml(type.toUpperCase())}</div>
            <div class="toast-desc"></div>
        </div>
        <button onclick="this.closest('.toast').remove()" class="text-[#8395A7] hover:text-[#142D4E] text-xs ml-2 cursor-pointer p-1" aria-label="Close notification">
            <i class="fas fa-times"></i>
        </button>
    `;

    toast.querySelector('.toast-desc').textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}
