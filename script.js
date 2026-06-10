const LEGACY_STORAGE_KEY = "habit-tracker-data";
const TOKEN_KEY = "habit-tracker-token";

const CATEGORY_LABELS = {
  study: "Study",
  fitness: "Fitness",
  Monetization: "Monetization",
  personal: "Personal Development",
  other: "Other",
};

const elements = {
  authScreen: document.getElementById("auth-screen"),
  app: document.getElementById("app"),
  loginForm: document.getElementById("login-form"),
  registerForm: document.getElementById("register-form"),
  authError: document.getElementById("auth-error"),
  authTabs: document.querySelectorAll(".auth-tab"),
  userGreeting: document.getElementById("user-greeting"),
  logoutBtn: document.getElementById("logout-btn"),
  form: document.getElementById("add-habit-form"),
  input: document.getElementById("habit-input"),
  categorySelect: document.getElementById("category-select"),
  filterCategory: document.getElementById("filter-category"),
  habitList: document.getElementById("habit-list"),
  emptyState: document.getElementById("empty-state"),
  themeToggle: document.getElementById("theme-toggle"),
  statTotal: document.getElementById("stat-total"),
  statCompleted: document.getElementById("stat-completed"),
  statRate: document.getElementById("stat-rate"),
  progressText: document.getElementById("progress-text"),
  progressPercent: document.getElementById("progress-percent"),
  progressFill: document.getElementById("progress-fill"),
  progressBar: document.querySelector(".progress-bar"),
};

let state = {
  token: localStorage.getItem(TOKEN_KEY),
  username: "",
  habits: [],
  theme: "light",
  filter: "all",
};

function formatDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function todayString() {
  return formatDate(new Date());
}

function getLegacyHabits() {
  try {
    const raw = localStorage.getItem(LEGACY_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed.habits) ? parsed.habits : [];
  } catch {
    return [];
  }
}

function clearLegacyStorage() {
  localStorage.removeItem(LEGACY_STORAGE_KEY);
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  const response = await fetch(path, { ...options, headers });
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || "Something went wrong");
  }

  return data;
}

function showAuthError(message) {
  elements.authError.textContent = message;
  elements.authError.classList.remove("hidden");
}

function clearAuthError() {
  elements.authError.textContent = "";
  elements.authError.classList.add("hidden");
}

function showAuthScreen() {
  elements.authScreen.classList.remove("hidden");
  elements.app.classList.add("hidden");
}

function showApp() {
  elements.authScreen.classList.add("hidden");
  elements.app.classList.remove("hidden");
  elements.userGreeting.textContent = `Hi, ${state.username}`;
}

function setToken(token) {
  state.token = token;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

function isCompleteToday(habit) {
  return habit.completedDates.includes(todayString());
}

function calculateStreak(habit) {
  const dates = new Set(habit.completedDates);
  let count = 0;
  const current = new Date();

  while (dates.has(formatDate(current))) {
    count += 1;
    current.setDate(current.getDate() - 1);
  }

  return count;
}

function getFilteredHabits() {
  if (state.filter === "all") return state.habits;
  return state.habits.filter((h) => h.category === state.filter);
}

function updateStats() {
  const total = state.habits.length;
  const completed = state.habits.filter(isCompleteToday).length;
  const rate = total === 0 ? 0 : Math.round((completed / total) * 100);

  elements.statTotal.textContent = total;
  elements.statCompleted.textContent = completed;
  elements.statRate.textContent = `${rate}%`;

  elements.progressText.textContent = `Progress: ${completed} / ${total} Habits Completed`;
  elements.progressPercent.textContent = `${rate}%`;
  elements.progressFill.style.width = `${rate}%`;
  elements.progressBar.setAttribute("aria-valuenow", rate);
}

function createHabitElement(habit) {
  const li = document.createElement("li");
  li.className = `habit-item${isCompleteToday(habit) ? " completed" : ""}`;
  li.dataset.id = habit.id;

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.className = "habit-checkbox";
  checkbox.checked = isCompleteToday(habit);
  checkbox.setAttribute("aria-label", `Mark ${habit.name} as complete`);
  checkbox.addEventListener("change", () => toggleHabit(habit.id));

  const info = document.createElement("div");
  info.className = "habit-info";

  const name = document.createElement("span");
  name.className = "habit-name";
  name.textContent = habit.name;

  const meta = document.createElement("div");
  meta.className = "habit-meta";

  const badge = document.createElement("span");
  badge.className = `category-badge ${habit.category}`;
  badge.textContent = CATEGORY_LABELS[habit.category] || habit.category;

  const streak = document.createElement("span");
  streak.className = "streak-badge";
  const streakCount = calculateStreak(habit);
  streak.textContent = streakCount > 0 ? `🔥 ${streakCount} Day Streak` : "No streak yet";

  meta.append(badge, streak);
  info.append(name, meta);

  const deleteBtn = document.createElement("button");
  deleteBtn.type = "button";
  deleteBtn.className = "btn btn-danger";
  deleteBtn.textContent = "Delete";
  deleteBtn.setAttribute("aria-label", `Delete ${habit.name}`);
  deleteBtn.addEventListener("click", () => deleteHabit(habit.id));

  li.append(checkbox, info, deleteBtn);
  return li;
}

function renderHabits() {
  const filtered = getFilteredHabits();
  elements.habitList.innerHTML = "";

  filtered.forEach((habit) => {
    elements.habitList.appendChild(createHabitElement(habit));
  });

  if (state.habits.length === 0) {
    elements.emptyState.textContent = "No habits yet. Add one above to get started!";
    elements.emptyState.classList.remove("hidden");
  } else if (filtered.length === 0) {
    elements.emptyState.textContent = "No habits in this category.";
    elements.emptyState.classList.remove("hidden");
  } else {
    elements.emptyState.classList.add("hidden");
  }

  updateStats();
}

async function loadHabits() {
  const data = await api("/api/habits");
  state.habits = data.habits;
  renderHabits();
}

async function importLegacyHabitsIfNeeded() {
  const legacy = getLegacyHabits();
  if (legacy.length === 0) return;

  const data = await api("/api/habits/import", {
    method: "POST",
    body: JSON.stringify({ habits: legacy }),
  });
  state.habits = data.habits;
  clearLegacyStorage();
  renderHabits();
}

async function addHabit(name, category) {
  const trimmed = name.trim();
  if (!trimmed) return;

  try {
    const habit = await api("/api/habits", {
      method: "POST",
      body: JSON.stringify({ name: trimmed, category }),
    });
    state.habits.push(habit);
    renderHabits();
  } catch (error) {
    if (error.message === "Habit already exists") {
      elements.input.focus();
    }
  }
}

async function toggleHabit(id) {
  try {
    const habit = await api(`/api/habits/${id}/toggle`, { method: "POST" });
    const index = state.habits.findIndex((h) => h.id === id);
    if (index !== -1) {
      state.habits[index] = habit;
    }
    renderHabits();
  } catch {
    renderHabits();
  }
}

async function deleteHabit(id) {
  try {
    await api(`/api/habits/${id}`, { method: "DELETE" });
    state.habits = state.habits.filter((h) => h.id !== id);
    renderHabits();
  } catch {
    renderHabits();
  }
}

async function saveTheme(theme) {
  try {
    await api("/api/preferences", {
      method: "PUT",
      body: JSON.stringify({ theme }),
    });
  } catch {
    /* theme still applies locally */
  }
}

function applyTheme(theme) {
  state.theme = theme;
  document.documentElement.setAttribute("data-theme", theme);
  elements.themeToggle.querySelector(".theme-icon").textContent =
    theme === "dark" ? "☀️" : "🌙";
}

async function toggleTheme() {
  const next = state.theme === "dark" ? "light" : "dark";
  applyTheme(next);
  await saveTheme(next);
}

async function handleLogin(event) {
  event.preventDefault();
  clearAuthError();

  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;

  try {
    const data = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    setToken(data.token);
    state.username = data.username;
    applyTheme(data.theme);
    showApp();
    await loadHabits();
    await importLegacyHabitsIfNeeded();
    elements.loginForm.reset();
  } catch (error) {
    showAuthError(error.message);
  }
}

async function handleRegister(event) {
  event.preventDefault();
  clearAuthError();

  const username = document.getElementById("register-username").value.trim();
  const password = document.getElementById("register-password").value;
  const confirm = document.getElementById("register-confirm").value;

  if (password !== confirm) {
    showAuthError("Passwords do not match");
    return;
  }

  try {
    const data = await api("/api/register", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    setToken(data.token);
    state.username = data.username;
    applyTheme(data.theme);
    showApp();
    await importLegacyHabitsIfNeeded();
    if (state.habits.length === 0) {
      await loadHabits();
    }
    elements.registerForm.reset();
  } catch (error) {
    showAuthError(error.message);
  }
}

function handleLogout() {
  setToken(null);
  state.username = "";
  state.habits = [];
  showAuthScreen();
  clearAuthError();
}

function switchAuthTab(tab) {
  elements.authTabs.forEach((btn) => {
    const isActive = btn.dataset.tab === tab;
    btn.classList.toggle("active", isActive);
    btn.setAttribute("aria-selected", isActive);
  });
  elements.loginForm.classList.toggle("hidden", tab !== "login");
  elements.registerForm.classList.toggle("hidden", tab !== "register");
  clearAuthError();
}

async function initSession() {
  const legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
  if (legacy) {
    try {
      const parsed = JSON.parse(legacy);
      if (parsed.theme === "dark") applyTheme("dark");
    } catch {
      /* ignore */
    }
  }

  if (!state.token) {
    showAuthScreen();
    return;
  }

  try {
    const data = await api("/api/me");
    state.username = data.username;
    applyTheme(data.theme);
    showApp();
    await loadHabits();
  } catch {
    setToken(null);
    showAuthScreen();
  }
}

elements.loginForm.addEventListener("submit", handleLogin);
elements.registerForm.addEventListener("submit", handleRegister);
elements.logoutBtn.addEventListener("click", handleLogout);

elements.authTabs.forEach((tab) => {
  tab.addEventListener("click", () => switchAuthTab(tab.dataset.tab));
});

elements.form.addEventListener("submit", async (e) => {
  e.preventDefault();
  await addHabit(elements.input.value, elements.categorySelect.value);
  elements.input.value = "";
  elements.input.focus();
});

elements.filterCategory.addEventListener("change", (e) => {
  state.filter = e.target.value;
  renderHabits();
});

elements.themeToggle.addEventListener("click", toggleTheme);

initSession();
