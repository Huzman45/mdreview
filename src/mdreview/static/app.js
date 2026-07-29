// Block selection.
//
// Every addressable block carries data-line-start / data-line-end, written by
// render.py from markdown-it's token.map. Clicking one selects it; shift-click
// extends the selection to a contiguous run of blocks, the same gesture the
// source view uses for lines. The line range is what a comment is anchored to.
(function () {
  "use strict";

  // The anchor is the block a plain click chose; the range is what the
  // comment will cover. Shift-click grows or shrinks the range around the
  // anchor rather than the range creeping with every click.
  var anchor = null;
  var current = null;

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

  // Paint every block the span fully covers, except where an ancestor is
  // already painted: tinting both a list and its items would double-shade
  // the items and read as a heavier, different selection.
  function paint() {
    var covered = [];
    document.querySelectorAll(".mdr-block").forEach(function (el) {
      var r = range(el);
      if (current && r.start >= current.start && r.end <= current.end) {
        covered.push(el);
      } else {
        el.classList.remove("selected");
      }
    });
    covered.forEach(function (el) {
      var parent = el.parentElement && el.parentElement.closest(".mdr-block");
      var parentCovered = false;
      while (parent) {
        var pr = range(parent);
        if (pr.start >= current.start && pr.end <= current.end) {
          parentCovered = true;
          break;
        }
        parent = parent.parentElement && parent.parentElement.closest(".mdr-block");
      }
      el.classList.toggle("selected", !parentCovered);
    });
  }

  function clear() {
    anchor = null;
    current = null;
    document.querySelectorAll(".mdr-block.selected").forEach(function (el) {
      el.classList.remove("selected");
    });
    document.dispatchEvent(new CustomEvent("mdr:deselected"));
  }

  function announce() {
    document.dispatchEvent(
      new CustomEvent("mdr:selected", { detail: { element: anchor, range: current } })
    );
  }

  function select(el) {
    // Plain-clicking the sole selected block toggles it off, as before.
    var r = range(el);
    var soleSelection =
      anchor === el && current && current.start === r.start && current.end === r.end;
    if (soleSelection) {
      clear();
      return;
    }
    anchor = el;
    current = r;
    paint();
    announce();
  }

  function extend(el) {
    var a = range(anchor);
    var b = range(el);
    current = { start: Math.min(a.start, b.start), end: Math.max(a.end, b.end) };
    paint();
    announce();
  }

  // The source view has its own line-based selection and no blocks at all.
  // Without this guard the handler below would clear that view's selection the
  // instant it was made.
  function hasBlocks() {
    return document.querySelector(".mdr-block") !== null;
  }

  document.addEventListener("click", function (event) {
    if (!hasBlocks()) return;
    // Let links and form controls behave normally.
    if (event.target.closest("a, button, input, textarea, select")) return;

    var block = blockOf(event.target);
    if (!block) {
      if (!event.target.closest(".margin")) clear();
      return;
    }
    // The innermost block wins, so a nested list item beats its parent.
    event.stopPropagation();
    if (event.shiftKey && anchor !== null) {
      extend(block);
    } else {
      select(block);
    }
  });

  // Shift-clicking otherwise extends the browser's text selection as well,
  // which looks broken. Same suppression as the source view.
  document.addEventListener("mousedown", function (event) {
    if (event.shiftKey && event.target.closest(".mdr-block")) event.preventDefault();
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") clear();
  });

  window.mdrSelection = {
    current: function () {
      return current;
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

  // On a phone the margin sits below the document, so a selected block leaves
  // the comment box off-screen. Bring it into view instead of focusing it,
  // because focusing alone would scroll abruptly and open the keyboard over
  // the text being commented on.
  function isStackedLayout() {
    return window.matchMedia("(max-width: 62rem)").matches;
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
    // The idle placeholder tells you to pick a block; once one is picked it
    // would be instructing you to do what you just did.
    if (f.body.dataset.idlePlaceholder === undefined) {
      f.body.dataset.idlePlaceholder = f.body.placeholder;
    }
    f.body.placeholder = "Write your comment…";

    if (isStackedLayout()) {
      var panel = document.getElementById("comment-panel");
      if (panel) panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } else {
      f.body.focus();
    }
  });

  document.addEventListener("mdr:deselected", function () {
    var f = form();
    if (!f.start) return;
    f.start.value = "";
    f.end.value = "";
    f.body.disabled = true;
    f.submit.disabled = true;
    f.label.textContent = "Select a block";
    if (f.body.dataset.idlePlaceholder !== undefined) {
      f.body.placeholder = f.body.dataset.idlePlaceholder;
    }
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
