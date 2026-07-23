// Apply theme immediately to prevent flashing
(function() {
    const savedTheme = localStorage.getItem("theme") || "light";
    if (savedTheme === "dark") {
        document.documentElement.classList.add("dark-theme");
    }
})();

window.logout = async function() {
    try {
        await fetch("/api/logout", {
            method: "POST",
            credentials: "same-origin",
            headers: { "X-Requested-With": "XMLHttpRequest" }
        });
    } catch (error) {
        console.warn("Logout request failed:", error);
    } finally {
        window.location.replace("/login");
    }
};

document.addEventListener("DOMContentLoaded", () => {
    // Sync the theme class to body just in case
    const savedTheme = localStorage.getItem("theme") || "light";
    if (savedTheme === "dark") {
        document.body.classList.add("dark-theme");
    }

    // Auto-add data-label to all table cells for mobile responsive tables
    document.querySelectorAll('table').forEach(table => {
        const headers = Array.from(table.querySelectorAll('th')).map(th => th.textContent.trim());
        table.querySelectorAll('tbody tr').forEach(row => {
            Array.from(row.querySelectorAll('td')).forEach((td, index) => {
                if (headers[index] && !td.hasAttribute('colspan') && !td.classList.contains('empty-state')) {
                    td.setAttribute('data-label', headers[index]);
                }
            });
        });
    });

    const navLinks = document.querySelector(".nav-links");
    // Global function to allow hardcoded buttons (e.g., in Employee Portal) to trigger theme toggle
    window.toggleTheme = function() {
        const isDark = document.body.classList.toggle("dark-theme");
        document.documentElement.classList.toggle("dark-theme", isDark);
        const newTheme = isDark ? "dark" : "light";
        localStorage.setItem("theme", newTheme);
        
        // Update all theme toggle icons across the UI
        document.querySelectorAll('button[onclick="toggleTheme()"] i, #theme-toggle i').forEach(icon => {
            if(icon.classList.contains('fa-sun') || icon.classList.contains('fa-moon')) {
                icon.className = isDark ? "fa-solid fa-sun" : "fa-solid fa-moon";
            }
        });
    };

    if (!navLinks) {
        // If there are no nav-links, update the icon of any hardcoded toggle buttons immediately based on savedTheme
        document.querySelectorAll('button[onclick="toggleTheme()"] i').forEach(icon => {
             if(icon.classList.contains('fa-sun') || icon.classList.contains('fa-moon')) {
                 icon.className = savedTheme === "light" ? "fa-solid fa-moon" : "fa-solid fa-sun";
             }
        });
        return;
    }

    function updateAdminNavSticky() {
        const adminNav = document.querySelector('.admin-nav-secondary');
        const navbar = document.querySelector('.navbar');
        if (!adminNav) return;
        adminNav.style.top = navbar ? `${navbar.offsetHeight}px` : '0px';
    }

    window.addEventListener('resize', updateAdminNavSticky);
    updateAdminNavSticky();

    // Create the theme toggle button
    const toggleBtn = document.createElement("button");
    toggleBtn.id = "theme-toggle";
    toggleBtn.className = "btn btn-outline btn-sm";
    toggleBtn.style.padding = "0.45rem 0.8rem";
    toggleBtn.style.display = "inline-flex";
    toggleBtn.style.alignItems = "center";
    toggleBtn.style.justifyContent = "center";
    toggleBtn.style.cursor = "pointer";
    toggleBtn.style.marginLeft = "0.5rem";
    toggleBtn.style.border = "1px solid var(--border-color)";
    toggleBtn.style.borderRadius = "var(--border-radius-sm)";
    toggleBtn.title = "Toggle Light/Dark Theme";
    
    const icon = document.createElement("i");
    // Show Moon if currently light theme, show Sun if currently dark theme
    icon.className = savedTheme === "light" ? "fa-solid fa-moon" : "fa-solid fa-sun";
    icon.style.fontSize = "0.95rem";
    icon.style.color = "var(--text-primary)";
    toggleBtn.appendChild(icon);

    // Insert toggle button before logout or as the last item
    const logoutBtn = Array.from(navLinks.querySelectorAll("a")).find(a => 
        a.textContent.toLowerCase().includes("logout") || 
        a.onclick && a.onclick.toString().toLowerCase().includes("logout")
    );
    
    if (logoutBtn) {
        navLinks.insertBefore(toggleBtn, logoutBtn);
    } else {
        navLinks.appendChild(toggleBtn);
    }

    document.addEventListener("click", async (event) => {
        const target = event.target instanceof Element ? event.target.closest("a, button") : null;
        if (!target) return;

        const targetText = (target.textContent || "").toLowerCase();
        const onclickAttr = (target.getAttribute("onclick") || "").toLowerCase();
        const isLogoutControl = targetText.includes("logout") || onclickAttr.includes("logout");

        if (!isLogoutControl) return;

        event.preventDefault();
        event.stopImmediatePropagation();

        await window.logout();
    }, true);

    toggleBtn.addEventListener("click", (e) => {
        e.preventDefault();
        window.toggleTheme();
    });
});
