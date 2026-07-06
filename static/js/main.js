// Modal functionality
function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Edit Record Modal
function openEditModal(id, currentStatus, driveLink, pcNumber, uploadedToDrive) {
    const editForm = document.getElementById('edit_form');
    if (editForm) {
        editForm.action = '/employee/dashboard/edit/' + id;
    }

    const statusEl = document.getElementById('edit_status');
    if (statusEl) {
        statusEl.value = currentStatus;
    }

    const driveLinkEl = document.getElementById('edit_drive_link');
    if (driveLinkEl) {
        driveLinkEl.value = driveLink || '';
    }

    const pcNumberEl = document.getElementById('edit_pc_number');
    if (pcNumberEl) {
        pcNumberEl.value = pcNumber || '';
    }

    const uploadedEl = document.getElementById('edit_uploaded_to_drive');
    if (uploadedEl) {
        uploadedEl.value = uploadedToDrive || 'No';
    }

    if (typeof toggleEditDriveLink === 'function') {
        toggleEditDriveLink();
    }
    openModal('editModal');
}

// Close modals when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('active');
    }
}

// Simple client-side navigation: load full page and replace <main> content
async function loadPageIntoMain(url, push=true) {
    try {
        const res = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        if (!res.ok) return window.location.href = url;
        const text = await res.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(text, 'text/html');

        const newMain = doc.querySelector('main.main-container');
        if (!newMain) return window.location.href = url;

        const curMain = document.querySelector('main.main-container');
        if (curMain) {
            curMain.innerHTML = newMain.innerHTML;
            document.title = doc.title || document.title;
        }

        // Execute scripts from fetched page
        const scripts = doc.querySelectorAll('script');
        scripts.forEach(s => {
            const scr = document.createElement('script');
            if (s.src) {
                scr.src = s.src;
                scr.async = false;
            } else {
                scr.textContent = s.textContent;
            }
            document.body.appendChild(scr);
            // remove the script node after it loads to keep DOM clean
            scr.addEventListener('load', () => scr.remove());
        });

        // Update active link in sidebar
        document.querySelectorAll('.sidebar-nav a').forEach(a => a.classList.remove('active'));
        document.querySelectorAll('.sidebar-nav a').forEach(a => {
            try {
                if (new URL(a.href, location.origin).pathname === new URL(url, location.origin).pathname) {
                    a.classList.add('active');
                }
            } catch (e) {}
        });

        if (push) history.pushState({ url }, '', url);
    } catch (err) {
        console.error('Navigation error', err);
        window.location.href = url;
    }
}

// Intercept clicks on sidebar links (single-page-ish)
document.addEventListener('click', function(e) {
    const a = e.target.closest('a');
    if (!a) return;
    const href = a.getAttribute('href');
    if (!href) return;
    // only intercept internal employee links to avoid breaking external links
    if (href.startsWith('/employee/')) {
        e.preventDefault();
        loadPageIntoMain(href);
    }
});

// Handle back/forward
window.addEventListener('popstate', function(e) {
    const state = e.state;
    const url = (state && state.url) ? state.url : location.pathname;
    loadPageIntoMain(url, false);
});
