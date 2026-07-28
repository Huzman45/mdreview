// Diagram upgrading.
//
// The server marks a diagram fence and leaves its source in the page. This
// script replaces the source with a rendered diagram, and leaves the source
// visible if anything goes wrong — a malformed diagram must never hide content.
//
// Mermaid is several megabytes, so it is fetched only when a page actually
// contains a diagram, and only once.
(function () {
  "use strict";

  var LIBRARY = "/static/mermaid.min.js";
  var loading = null;

  function blocks() {
    return Array.prototype.slice.call(document.querySelectorAll(".mdr-diagram"));
  }

  function sourceOf(block) {
    var code = block.querySelector("pre code, pre");
    return code ? code.textContent : "";
  }

  // Stock mermaid blue looks pasted-on against warm paper, so the diagram is
  // themed from the same palette as the prose around it.
  var PALETTE = {
    light: {
      background: "#f5f1e8",
      primaryColor: "#efe9db",
      primaryBorderColor: "#cdc4b0",
      primaryTextColor: "#23201b",
      lineColor: "#8f8776",
      secondaryColor: "#f0e8d6",
      tertiaryColor: "#fbf9f4",
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
    dark: {
      background: "#1d1a14",
      primaryColor: "#26221a",
      primaryBorderColor: "#453e30",
      primaryTextColor: "#ece5d6",
      lineColor: "#857c6b",
      secondaryColor: "#2c2418",
      tertiaryColor: "#16140f",
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
  };

  function settings() {
    var dark = isDark();
    return {
      startOnLoad: false,
      // strict sanitises markup in labels: diagram source is agent-authored and
      // therefore untrusted, exactly like the surrounding prose.
      securityLevel: "strict",
      theme: "base",
      themeVariables: dark ? PALETTE.dark : PALETTE.light,
    };
  }

  function isDark() {
    return (
      document.documentElement.getAttribute("data-theme") === "dark" ||
      (!document.documentElement.getAttribute("data-theme") &&
        window.matchMedia("(prefers-color-scheme: dark)").matches)
    );
  }

  function load() {
    if (loading) return loading;
    loading = new Promise(function (resolve, reject) {
      var script = document.createElement("script");
      script.src = LIBRARY;
      script.onload = resolve;
      script.onerror = function () {
        reject(new Error("could not load the diagram library"));
      };
      document.head.appendChild(script);
    });
    return loading;
  }

  function fail(block, message) {
    block.classList.add("mdr-diagram-failed");
    var pre = block.querySelector("pre");
    if (pre) pre.hidden = false;
    if (block.querySelector(".mdr-diagram-error")) return;
    var note = document.createElement("p");
    note.className = "mdr-diagram-error";
    note.textContent = message;
    block.insertBefore(note, block.firstChild);
  }

  function renderInto(block, index) {
    var source = sourceOf(block);
    var pre = block.querySelector("pre");
    var id = "mdr-diagram-" + index + "-" + Date.now();

    return window.mermaid
      .render(id, source)
      .then(function (result) {
        var target = block.querySelector(".mdr-diagram-output");
        if (!target) {
          target = document.createElement("div");
          target.className = "mdr-diagram-output";
          block.appendChild(target);
        }
        target.innerHTML = result.svg;
        block.classList.remove("mdr-diagram-failed");
        var note = block.querySelector(".mdr-diagram-error");
        if (note) note.remove();
        if (pre) pre.hidden = true;
      })
      .catch(function () {
        fail(block, "This diagram could not be rendered. Showing its source.");
      });
  }

  function renderAll() {
    var found = blocks();
    if (!found.length) return;

    load()
      .then(function () {
        // strict sanitises markup in labels: diagram source is agent-authored
        // and therefore untrusted, exactly like the surrounding prose.
        window.mermaid.initialize(settings());
        return Promise.all(found.map(renderInto));
      })
      .catch(function () {
        found.forEach(function (block) {
          fail(block, "The diagram library is unavailable. Showing the source.");
        });
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderAll);
  } else {
    renderAll();
  }

  // A diagram drawn for the other colour scheme is unreadable, so re-render.
  document.addEventListener("mdr:themechange", function () {
    if (!window.mermaid || !blocks().length) return;
    window.mermaid.initialize(settings());
    blocks().forEach(renderInto);
  });
})();
