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

  // Stock mermaid blue is pasted-on against warm paper, so the diagram takes
  // the same palette as the prose around it.
  //
  // The colours are read from the stylesheet's own custom properties rather
  // than repeated here, so a diagram cannot drift from the page it sits in and
  // the dark palette needs no second copy in JavaScript.
  function token(name) {
    return getComputedStyle(document.documentElement)
      .getPropertyValue(name)
      .trim();
  }

  function settings() {
    return {
      startOnLoad: false,
      // strict sanitises markup in labels: diagram source is agent-authored
      // and therefore untrusted, exactly like the surrounding prose.
      securityLevel: "strict",
      theme: "base",
      themeVariables: {
        background: token("--paper-2"),
        primaryColor: token("--wash"),
        primaryBorderColor: token("--rule"),
        primaryTextColor: token("--ink"),
        secondaryColor: token("--select"),
        tertiaryColor: token("--paper"),
        lineColor: token("--accent"),
        fontFamily:
          "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, sans-serif",
        fontSize: "14px",
      },
    };
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

  // A diagram drawn for the other scheme keeps its old fills, so it has to be
  // drawn again rather than merely restyled.
  document.addEventListener("mdr:themechange", function () {
    if (!window.mermaid || !blocks().length) return;
    window.mermaid.initialize(settings());
    blocks().forEach(renderInto);
  });
})();
