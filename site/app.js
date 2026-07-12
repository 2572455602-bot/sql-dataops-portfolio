document.querySelectorAll(".is-disabled").forEach((link) => {
  link.setAttribute("aria-disabled", "true");
  link.removeAttribute("href");
});
