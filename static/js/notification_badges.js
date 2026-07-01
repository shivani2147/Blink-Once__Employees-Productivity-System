/**
 * Notification Badges System (Frontend-only using LocalStorage)
 */

(function () {
    const POLLING_INTERVAL = 30000; // 30 seconds
    const STORAGE_KEY = 'eps_notifications_state';

    let state = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');

    async function fetchWithCatch(url) {
        try {
            const res = await fetch(url);
            if (!res.ok) return null;
            return await res.json();
        } catch (e) {
            return null;
        }
    }

    function updateBadge(selector, count) {
        const link = document.querySelector(selector);
        if (!link) return;

        let badge = link.querySelector('.nav-badge');
        if (count > 0) {
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'nav-badge';
                link.appendChild(badge);
            }
            badge.textContent = count;
        } else {
            if (badge) {
                badge.remove();
            }
        }
    }

    // Save current count as the "read" state for a specific tab
    function markAsRead(tabKey, currentCount) {
        state[tabKey] = currentCount;
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }

    async function checkEmployeeNotifications() {
        // Attendance & To-Do: New tasks assigned
        const recordsRes = await fetchWithCatch('/api/employee/records');
        if (recordsRes && recordsRes.tasks) {
            // Count tasks
            const taskCount = recordsRes.tasks.length;
            const seenTaskCount = state['employee_attendance'] || 0;
            const unreadTasks = Math.max(0, taskCount - seenTaskCount);
            updateBadge('a[href="/employee/attendance"]', unreadTasks);
            
            // If we are currently on this page, mark as read
            if (window.location.pathname === '/employee/attendance') {
                markAsRead('employee_attendance', taskCount);
                updateBadge('a[href="/employee/attendance"]', 0);
            }
        }

        // Productivity
        if (recordsRes && recordsRes.records) {
            const prodCount = recordsRes.records.length;
            const seenProdCount = state['employee_productivity'] || 0;
            const unreadProd = Math.max(0, prodCount - seenProdCount);
            updateBadge('a[href="/employee/productivity"]', unreadProd);

            if (window.location.pathname === '/employee/productivity') {
                markAsRead('employee_productivity', prodCount);
                updateBadge('a[href="/employee/productivity"]', 0);
            }
        }

        // Leaves & Holidays
        const holidaysRes = await fetchWithCatch('/api/employee/holidays');
        const leavesRes = await fetchWithCatch('/api/employee/leave/history');
        
        let leaveRelatedCount = 0;
        if (holidaysRes) leaveRelatedCount += holidaysRes.length;
        if (leavesRes && leavesRes.history) leaveRelatedCount += leavesRes.history.length;

        const seenLeaveCount = state['employee_leaves'] || 0;
        const unreadLeaves = Math.max(0, leaveRelatedCount - seenLeaveCount);
        updateBadge('a[href="/employee/leaves"]', unreadLeaves);

        if (window.location.pathname === '/employee/leaves') {
            markAsRead('employee_leaves', leaveRelatedCount);
            updateBadge('a[href="/employee/leaves"]', 0);
        }
    }

    async function checkAdminNotifications() {
        // Employee Management
        const empRes = await fetchWithCatch('/api/admin/employees');
        if (empRes && empRes.employees) {
            const empCount = empRes.employees.length;
            const seenEmpCount = state['admin_employees'] || 0;
            const unreadEmp = Math.max(0, empCount - seenEmpCount);
            updateBadge('a[href="/admin/employees"]', unreadEmp);
            updateBadge('a[href="/admin/employees"]', unreadEmp);
            updateBadge('a[href="/admin/view-employees"]', unreadEmp);

            if (window.location.pathname.startsWith('/admin/employees') || window.location.pathname.startsWith('/admin/view-employees')) {
                markAsRead('admin_employees', empCount);
                updateBadge('a[href="/admin/employees"]', 0);
                updateBadge('a[href="/admin/view-employees"]', 0);
            }
        }

        // Attendance Management
        const attRes = await fetchWithCatch('/api/admin/attendance');
        if (attRes && attRes.records) {
            const attCount = attRes.records.length;
            const seenAttCount = state['admin_attendance'] || 0;
            const unreadAtt = Math.max(0, attCount - seenAttCount);
            updateBadge('a[href="/admin/attendance"]', unreadAtt);

            if (window.location.pathname === '/admin/attendance') {
                markAsRead('admin_attendance', attCount);
                updateBadge('a[href="/admin/attendance"]', 0);
            }
        }

        // Task Management
        const taskRes = await fetchWithCatch('/api/admin/tasks');
        if (taskRes && Array.isArray(taskRes)) {
            const taskCount = taskRes.length;
            const seenTaskCount = state['admin_tasks'] || 0;
            const unreadTasks = Math.max(0, taskCount - seenTaskCount);
            updateBadge('a[href="/admin/tasks"]', unreadTasks);

            if (window.location.pathname === '/admin/tasks') {
                markAsRead('admin_tasks', taskCount);
                updateBadge('a[href="/admin/tasks"]', 0);
            }
        }

        // Productivity (Performance)
        const prodRes = await fetchWithCatch('/api/admin/performance-data');
        if (prodRes && prodRes.employees) {
            const prodCount = prodRes.employees.length;
            const seenProdCount = state['admin_productivity'] || 0;
            const unreadProd = Math.max(0, prodCount - seenProdCount);
            updateBadge('a[href="/admin/performance"]', unreadProd);

            if (window.location.pathname === '/admin/performance') {
                markAsRead('admin_productivity', prodCount);
                updateBadge('a[href="/admin/performance"]', 0);
            }
        }

        // Leaves
        const leavesRes = await fetchWithCatch('/api/admin/leaves');
        if (leavesRes && leavesRes.leaves) {
            const leaveCount = leavesRes.leaves.length;
            const seenLeaveCount = state['admin_leaves'] || 0;
            const unreadLeaves = Math.max(0, leaveCount - seenLeaveCount);
            updateBadge('a[href="/admin/leaves"]', unreadLeaves);

            if (window.location.pathname === '/admin/leaves') {
                markAsRead('admin_leaves', leaveCount);
                updateBadge('a[href="/admin/leaves"]', 0);
            }
        }

        // Holidays
        const holidaysRes = await fetchWithCatch('/api/admin/holidays');
        if (holidaysRes && holidaysRes.holidays) {
            const holCount = holidaysRes.holidays.length;
            const seenHolCount = state['admin_holidays'] || 0;
            const unreadHol = Math.max(0, holCount - seenHolCount);
            updateBadge('a[href="/admin/holidays"]', unreadHol);

            if (window.location.pathname === '/admin/holidays') {
                markAsRead('admin_holidays', holCount);
                updateBadge('a[href="/admin/holidays"]', 0);
            }
        }
    }

    async function pollNotifications() {
        const path = window.location.pathname;
        if (path.startsWith('/employee/')) {
            await checkEmployeeNotifications();
        } else if (path.startsWith('/admin/')) {
            await checkAdminNotifications();
        }
    }

    // Attach click listeners to sidebar links to mark as read immediately
    function attachClickListeners() {
        const links = document.querySelectorAll('.sidebar-nav a, .admin-nav-secondary a');
        links.forEach(link => {
            link.addEventListener('click', () => {
                const badge = link.querySelector('.nav-badge');
                if (badge) {
                    badge.remove();
                }
                // Rely on the subsequent page load to actually update the local state correctly,
                // but visually clear it right away.
            });
        });
    }

    // Initialize
    document.addEventListener('DOMContentLoaded', () => {
        pollNotifications();
        attachClickListeners();
        setInterval(pollNotifications, POLLING_INTERVAL);
    });

})();
