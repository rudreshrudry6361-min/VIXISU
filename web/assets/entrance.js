"use strict";
(() => {
  const byId = id => document.getElementById(id);
  const rail = byId("rail");
  const layout = byId("layout");
  const dialog = byId("artwork");
  const motion = matchMedia("(prefers-reduced-motion: reduce)");
  const portraits = [
    ["Virat Kohli", "kohli", "https://commons.wikimedia.org/wiki/File:Virat_Kohli_batting_2013.jpg"],
    ["Jasprit Bumrah", "bumrah", "https://commons.wikimedia.org/wiki/File:Jasprit_Bumrah_(4).jpg"],
    ["Ellyse Perry", "perry", "https://commons.wikimedia.org/wiki/File:Ellyse_Perry_WTest_2017%E2%80%9318.jpg"],
  ];

  function move(direction) {
    rail.scrollBy({left:direction * (rail.firstElementChild.clientWidth + 16), behavior:motion.matches ? "auto" : "smooth"});
  }

  byId("prev").onclick = () => move(-1);
  byId("next").onclick = () => move(1);
  layout.onclick = () => {
    const grid = rail.classList.toggle("grid");
    layout.setAttribute("aria-pressed", String(grid));
    layout.textContent = grid ? "Carousel view" : "Grid view";
    byId("prev").hidden = grid;
    byId("next").hidden = grid;
  };
  rail.onkeydown = event => {
    if (rail.classList.contains("grid") || !["ArrowLeft","ArrowRight"].includes(event.key)) return;
    event.preventDefault();
    move(event.key === "ArrowLeft" ? -1 : 1);
  };
  rail.querySelectorAll(".poster").forEach(poster => {
    poster.addEventListener("click", event => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      const [name, photo, source] = portraits[Number(poster.dataset.index)];
      byId("artwork-title").textContent = name;
      byId("artwork-image").src = "/assets/photos/" + photo + "-ink.webp";
      byId("artwork-image").alt = poster.querySelector("img").alt + " in a poster treatment";
      byId("original-photo").href = source;
      byId("open-profile").href = poster.href;
      dialog.showModal();
    });
  });
  byId("close-artwork").onclick = () => dialog.close();
  byId("poster-controls").hidden = false;

  if ("IntersectionObserver" in window) {
    const room = document.querySelector(".doorway");
    const observer = new IntersectionObserver(([entry]) => {
      room.classList.toggle("in-view", entry.isIntersecting);
    }, {threshold:0.5});
    observer.observe(room);
  }
})();
