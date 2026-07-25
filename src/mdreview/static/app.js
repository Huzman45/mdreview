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

  // -- bind selection to the comment form ---------------------------------

  function form() {
    return {
      start: document.getElementById("line_start"),
      end: document.getElementById("line_end"),
      body: document.getElementById("comment-body"),
      submit: document.getElementById("comment-submit"),
      label: document.getElementById("selection-label"),
    };
  }

  function label(r) {
    return r.start === r.end ? "Line " + r.start : "Lines " + r.start + "–" + r.end;
  }

  document.addEventListener("mdr:selected", function (event) {
    var f = form();
    if (!f.start) return;
    var r = event.detail.range;
    f.start.value = r.start;
    f.end.value = r.end;
    f.body.disabled = false;
    f.submit.disabled = false;
    f.label.textContent = label(r);
    f.body.focus();
  });

  document.addEventListener("mdr:deselected", function () {
    var f = form();
    if (!f.start) return;
    f.start.value = "";
    f.end.value = "";
    f.body.disabled = true;
    f.submit.disabled = true;
    f.label.textContent = "No block selected";
  });

  // Submit with cmd/ctrl+enter.
  document.addEventListener("keydown", function (event) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      var f = form();
      if (f.submit && !f.submit.disabled) f.submit.click();
    }
  });

  // Highlight the block a comment refers to when hovering the comment.
  document.addEventListener("mouseover", function (event) {
    var item = event.target.closest(".comment");
    if (!item) return;
    var start = item.getAttribute("data-line-start");
    var block = document.querySelector('.mdr-block[data-line-start="' + start + '"]');
    if (block) block.classList.add("referenced");
  });

  document.addEventListener("mouseout", function (event) {
    var item = event.target.closest(".comment");
    if (!item) return;
    document.querySelectorAll(".referenced").forEach(function (el) {
      el.classList.remove("referenced");
    });
  });
})();
