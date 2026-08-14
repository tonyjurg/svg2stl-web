const navToggle = document.querySelector("#nav-toggle");
const siteNav = document.querySelector("#site-nav");
const motionToggle = document.querySelector("#motion-toggle");
const motionLabel = motionToggle.querySelector(".motion-label");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

function closeNavigation() {
  siteNav.classList.remove("is-open");
  navToggle.setAttribute("aria-expanded", "false");
}

navToggle.addEventListener("click", () => {
  const willOpen = !siteNav.classList.contains("is-open");
  siteNav.classList.toggle("is-open", willOpen);
  navToggle.setAttribute("aria-expanded", String(willOpen));
});

for (const link of siteNav.querySelectorAll("a")) {
  link.addEventListener("click", closeNavigation);
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeNavigation();
});

function setMotionPaused(paused) {
  document.documentElement.classList.toggle("motion-paused", paused);
  motionToggle.setAttribute("aria-pressed", String(paused));
  motionLabel.textContent = paused ? "Play animations" : "Pause animations";
}

function followMotionPreference() {
  const reduce = reducedMotion.matches;
  setMotionPaused(reduce);
  motionToggle.hidden = reduce;
}

motionToggle.addEventListener("click", () => {
  setMotionPaused(!document.documentElement.classList.contains("motion-paused"));
});

reducedMotion.addEventListener("change", followMotionPreference);
followMotionPreference();

document.querySelector("#year").textContent = new Date().getFullYear();
