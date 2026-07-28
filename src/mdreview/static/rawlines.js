// Line selection in the source view.
//
// Click selects a line; shift-click extends to a contiguous range. This is the
// interaction people already know from diff views and file browsers.
//
// The result feeds the same line_start / line_end fields the rendered view
// uses, so a comment made here is indistinguishable from one made on a block.
(function () {
  "use strict";

  var anchor = null;
  var range = null;

  function lines() {
    return Array.prototype.slice.call(document.querySelectorAll(".mdr-line"));
  }

  function numberOf(el) {
    return parseInt(el.getAttribute("data-line"), 10);
  }

  function paint() {
    lines().forEach(function (el) {
      var n = numberOf(el);
      var inRange = range && n >= range.start && n <= range.end;
      el.classList.toggle("selected", Boolean(inRange));
    });
  }

  function clear() {
    anchor = null;
    range = null;
    paint();
    document.dispatchEvent(new CustomEvent("mdr:deselected"));
  }

  function select(start, end) {
    range = { start: Math.min(start, end), end: Math.max(start, end) };
    paint();
    document.dispatchEvent(
      new CustomEvent("mdr:selected", { detail: { range: range } })
    );
  }

  document.addEventListener("click", function (event) {
    if (event.target.closest("a, button, input, textarea, select")) return;

    var line = event.target.closest(".mdr-line");
    if (!line) {
      if (!event.target.closest(".margin")) clear();
      return;
    }

    var n = numberOf(line);
    if (event.shiftKey && anchor !== null) {
      select(anchor, n);
    } else {
      anchor = n;
      select(n, n);
    }
  });

  // Shift-clicking otherwise selects text as well, which looks broken.
  document.addEventListener("mousedown", function (event) {
    if (event.shiftKey && event.target.closest(".mdr-line")) event.preventDefault();
  });
})();
