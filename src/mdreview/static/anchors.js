// Anchored margin notes.
//
// In the two-column layout each note is placed at its anchor's vertical
// position: the exact source line where the view has lines, otherwise the
// innermost block containing the note's first line, interpolated by line
// fraction inside multi-line blocks. Overlapping notes yield downward in
// anchor order; the comment form joins the pass, idle after the last note or
// anchored to the current selection.
//
// This file only measures and assigns `top`; the stylesheet decides that
// notes are absolute in the wide layout and normal flow in the stacked one.
(function () {
  "use strict";

  var GAP = 14; // px between stacked notes

  // The same query the stylesheet and app.js use for the stacked layout.
  var stacked = window.matchMedia("(max-width: 62rem)");

  var selection = null; // latest range from mdr:selected, for the form

  function margin() {
    return document.getElementById("sidebar");
  }

  // The element a line number points at, with enough context to interpolate
  // inside multi-line blocks. Source view wins with an exact line; rendered
  // view takes the innermost containing block.
  function resolveAnchor(lineStart) {
    var line = document.querySelector('.mdr-line[data-line="' + lineStart + '"]');
    if (line) return { el: line, start: lineStart, end: lineStart };

    var best = null;
    var bestSpan = Infinity;
    document.querySelectorAll(".mdr-block").forEach(function (el) {
      var s = parseInt(el.getAttribute("data-line-start"), 10);
      var e = parseInt(el.getAttribute("data-line-end"), 10);
      if (lineStart >= s && lineStart <= e && e - s < bestSpan) {
        bestSpan = e - s;
        best = { el: el, start: s, end: e };
      }
    });
    return best;
  }

  // Vertical target for a line, in the margin's coordinate space. A line no
  // element covers falls back to the top rather than vanishing.
  function anchorTop(lineStart, marginTop) {
    var anchor = resolveAnchor(lineStart);
    if (!anchor) return 0;
    var rect = anchor.el.getBoundingClientRect();
    var lines = anchor.end - anchor.start + 1;
    var fraction = lines > 1 ? (lineStart - anchor.start) / lines : 0;
    return rect.top + fraction * rect.height - marginTop;
  }

  function layout() {
    var box = margin();
    if (!box) return;

    if (stacked.matches) {
      // Undo anything a wide pass left behind; the stacked list is flow.
      box.style.minHeight = "";
      box.querySelectorAll(".note").forEach(function (el) {
        el.style.top = "";
      });
      return;
    }

    var marginTop = box.getBoundingClientRect().top;

    // Read phase: anchors and heights, no writes yet.
    var items = [];
    box.querySelectorAll(".note").forEach(function (el, index) {
      var isForm = el.id === "comment-panel";
      var anchor;
      if (isForm) {
        anchor = selection ? anchorTop(selection.start, marginTop) : Infinity;
      } else {
        anchor = anchorTop(parseInt(el.getAttribute("data-line-start"), 10), marginTop);
      }
      items.push({
        el: el,
        anchor: anchor,
        // The idle form sorts last; on a shared anchor the form follows the
        // notes it would join.
        tie: isForm ? 1 : 0,
        index: index,
        height: el.offsetHeight,
      });
    });

    items.sort(function (a, b) {
      return a.anchor - b.anchor || a.tie - b.tie || a.index - b.index;
    });

    // Write phase: walk down, each item at its anchor or below its
    // predecessor, whichever is lower.
    var cursor = 0;
    var bottom = 0;
    items.forEach(function (item, i) {
      var top;
      if (item.anchor === Infinity) {
        top = i === 0 ? 0 : cursor;
      } else {
        top = Math.max(item.anchor, i === 0 ? item.anchor : cursor);
      }
      top = Math.max(0, Math.round(top));
      item.el.style.top = top + "px";
      cursor = top + item.height + GAP;
      bottom = top + item.height;
    });

    // The sheet grows to hold the last note instead of letting it overflow.
    box.style.minHeight = bottom + "px";

    // Enable glide only after the first placement, so nothing animates in
    // from the container top on load or after a swap.
    box.classList.add("anchored");
  }

  // -- when geometry changes ----------------------------------------------

  // Watch the content (diagrams rendering, images arriving move every offset
  // below them) and every note (the notes are sans-serif while the prose is
  // not, so a font swap can grow a note without moving the prose at all —
  // stale heights would slide later notes under earlier ones). Re-layout
  // only writes `top` and the margin's min-height, neither of which resizes
  // a note, so this cannot loop.
  var observer = null;

  function observe() {
    if (typeof ResizeObserver === "undefined") return;
    if (observer) observer.disconnect();
    observer = new ResizeObserver(layout);
    var content = document.getElementById("rendered") || document.getElementById("rawlines");
    if (content) observer.observe(content);
    var box = margin();
    if (box) {
      box.querySelectorAll(".note").forEach(function (el) {
        observer.observe(el);
      });
    }
  }

  function refresh() {
    layout();
    observe();
  }

  document.addEventListener("DOMContentLoaded", refresh);
  window.addEventListener("resize", layout);
  stacked.addEventListener("change", layout);
  // A swap replaces the notes wholesale; the observer must adopt the new ones.
  document.addEventListener("htmx:afterSwap", refresh);
  document.addEventListener("mdr:selected", function (event) {
    selection = event.detail.range;
    layout();
  });
  document.addEventListener("mdr:deselected", function () {
    selection = null;
    layout();
  });
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(layout);
  }

  // -- hover: a note points back at its passage ----------------------------

  function clearReferenced() {
    document.querySelectorAll(".referenced").forEach(function (el) {
      el.classList.remove("referenced");
    });
  }

  document.addEventListener("mouseover", function (event) {
    var note = event.target.closest(".note");
    if (!note || note.id === "comment-panel") return;
    var anchor = resolveAnchor(parseInt(note.getAttribute("data-line-start"), 10));
    if (anchor) anchor.el.classList.add("referenced");
  });

  document.addEventListener("mouseout", function (event) {
    if (event.target.closest(".note")) clearReferenced();
  });
})();
