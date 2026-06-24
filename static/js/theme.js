// Apply theme immediately to prevent flashing
(function() {
    const savedTheme = localStorage.getItem("theme") || "light";
    if (savedTheme === "dark") {
        document.documentElement.classList.add("dark-theme");
    }
})();

document.addEventListener("DOMContentLoaded", () => {
    // Sync the theme class to body just in case
    const savedTheme = localStorage.getItem("theme") || "light";
    if (savedTheme === "dark") {
        document.body.classList.add("dark-theme");
    }

    const navLinks = document.querySelector(".nav-links");
    if (!navLinks) return;

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

    toggleBtn.addEventListener("click", (e) => {
        e.preventDefault();
        const isDark = document.body.classList.toggle("dark-theme");
        document.documentElement.classList.toggle("dark-theme", isDark);
        const newTheme = isDark ? "dark" : "light";
        localStorage.setItem("theme", newTheme);
        icon.className = isDark ? "fa-solid fa-sun" : "fa-solid fa-moon";
    });
});
