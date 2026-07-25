// Block selection.
//
// Every addressable block carries data-line-start / data-line-end, written by
// render.py from markdown-it's token.map. Clicking one selects it; the line
// range is what a comment is anchored to.
(function () {
  "use strict";

  var selected = null;

  function blockOf(target) {
    var el = target.closest(".mdr-block");
    return el || null;
  }

  function range(el) {
    return {
      start: parseInt(el.getAttribute("data-line-start"), 10),
      end: parseInt(el.getAttribute("data-line-end"), 10),
    };
  }

  function clear() {
    if (selected) {
      selected.classList.remove("selected");
      selected = null;
    }
    document.dispatchEvent(new CustomEvent("mdr:deselected"));
  }

  function select(el) {
    if (selected === el) {
      clear();
      return;
    }
    if (selected) selected.classList.remove("selected");
    selected = el;
    el.classList.add("selected");
    document.dispatchEvent(
      new CustomEvent("mdr:selected", { detail: { element: el, range: range(el) } })
    );
  }

  document.addEventListener("click", function (event) {
    // Let links and form controls behave normally.
    if (event.target.closest("a, button, input, textarea, select")) return;

    var block = blockOf(event.target);
    if (!block) {
      if (!event.target.closest(".comment-panel")) clear();
      return;
    }
    // The innermost block wins, so a nested list item beats its parent.
    event.stopPropagation();
    select(block);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") clear();
  });

  window.mdrSelection = {
    current: function () {
      return selected ? range(selected) : null;
    },
    clear: clear,
  };
})();
