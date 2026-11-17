// Click an image on a page to fill the window with it; click again (or press Esc) to go back.
(() => {
  let overlay = null;

  const close = () => {
    overlay?.remove();
    overlay = null;
  };

  document.addEventListener("click", (event) => {
    if (overlay) {
      close();
      return;
    }
    const img = event.target instanceof Element ? event.target.closest(".yue img") : null;
    // gallery cards link to their pages
    if (!img || img.closest(".sp-gallery")) return;
    event.preventDefault(); // images that link to their own file stay on the page
    overlay = document.createElement("div");
    overlay.className = "nbdemo-zoom";
    const zoomed = document.createElement("img");
    zoomed.src = img.currentSrc || img.src;
    zoomed.alt = img.alt;
    overlay.append(zoomed);
    document.body.append(overlay);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close();
  });
})();
