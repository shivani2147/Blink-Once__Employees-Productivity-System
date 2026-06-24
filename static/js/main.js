// Modal functionality
function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Edit Record Modal
function openEditModal(id, currentStatus, driveLink, comments) {
    document.getElementById('edit_form').action = '/employee/dashboard/edit/' + id;
    document.getElementById('edit_status').value = currentStatus;
    document.getElementById('edit_drive_link').value = driveLink;
    document.getElementById('edit_comments').value = comments;
    openModal('editModal');
}

// Close modals when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('active');
    }
}
