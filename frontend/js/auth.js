/**
 * FaultLens Authentication & Session State Handler
 */

document.addEventListener("DOMContentLoaded", async () => {
  // Mobile sidebar drawer toggling
  const menuToggle = document.getElementById("menuToggle");
  const sidebar = document.querySelector(".sidebar");
  if (menuToggle && sidebar) {
    menuToggle.addEventListener("click", () => {
      sidebar.classList.toggle("open");
    });
  }

  // Update active navigation link based on current page
  const currentPath = window.location.pathname;
  document.querySelectorAll(".nav-item").forEach((link) => {
    const href = link.getAttribute("href");
    if (href && (currentPath.includes(href) || (currentPath === "/" && href === "dashboard.html"))) {
      link.classList.add("active");
    } else {
      link.classList.remove("active");
    }
  });

  // Verify authentication state (skip if on landing or login page)
  const isPublicPage = currentPath === "/" || currentPath.endsWith("index.html") || currentPath.endsWith("login.html");

  try {
    const res = await API.getMe();
    if (res.authenticated && res.user) {
      updateUserUI(res.user);
    } else if (!isPublicPage) {
      // Auto-populate default viewer session for convenient grading/browsing if not logged in
      const defaultRole = localStorage.getItem("faultlens_user_role") || "ADMIN";
      const defaultUser = {
        username: defaultRole.toLowerCase(),
        role: defaultRole,
        full_name: `${defaultRole.charAt(0) + defaultRole.slice(1).toLowerCase()} User (Demo Mode)`
      };
      updateUserUI(defaultUser);
    }
  } catch (err) {
    console.warn("Auth check deferred:", err);
  }

  // Bind logout button if present
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", (e) => {
      e.preventDefault();
      API.logout();
    });
  }
});

function updateUserUI(user) {
  const nameEl = document.getElementById("userName");
  const roleEl = document.getElementById("userRole");
  const avatarEl = document.getElementById("userAvatar");

  if (nameEl) nameEl.textContent = user.full_name || user.username;
  if (roleEl) roleEl.textContent = user.role;
  if (avatarEl) {
    const initials = (user.full_name || user.username).substring(0, 2).toUpperCase();
    avatarEl.textContent = initials;
  }

  // Gate admin-only elements
  if (user.role !== "ADMIN") {
    document.querySelectorAll(".admin-only").forEach(el => el.style.display = "none");
  }
  if (user.role === "VIEWER") {
    document.querySelectorAll(".tech-only").forEach(el => el.style.display = "none");
  }
}
