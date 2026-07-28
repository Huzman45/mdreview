// Colour scheme.
//
// This file is inlined into <head> and runs before the stylesheet paints.
// Reading the stored preference after render would flash the wrong colours on
// every load, which is the most noticeable way to get this wrong.
//
// The reader's choice is one of "light", "dark" or "system". "system" is
// resolved here to an explicit data-theme, so the stylesheet needs dark tokens
// in exactly one place rather than duplicating them in a media query.
(function () {
  "use strict";

  var KEY = "mdreview-theme";
  var CHOICES = ["light", "dark", "system"];
  var media = window.matchMedia("(prefers-color-scheme: dark)");

  function stored() {
    try {
      var value = localStorage.getItem(KEY);
      return CHOICES.indexOf(value) === -1 ? "system" : value;
    } catch (e) {
      return "system";
    }
  }

  function resolve(choice) {
    if (choice === "system") return media.matches ? "dark" : "light";
    return choice;
  }

  function apply(choice) {
    var effective = resolve(choice);
    document.documentElement.setAttribute("data-theme", effective);
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", effective === "dark" ? "#161a21" : "#ffffff");
    return effective;
  }

  apply(stored());

  function set(choice) {
    try {
      localStorage.setItem(KEY, choice);
    } catch (e) {
      /* private browsing; the choice still applies for this page */
    }
    var effective = apply(choice);
    sync(choice);
    document.dispatchEvent(
      new CustomEvent("mdr:themechange", { detail: { choice: choice, effective: effective } })
    );
  }

  function sync(choice) {
    var buttons = document.querySelectorAll("[data-theme-choice]");
    Array.prototype.forEach.call(buttons, function (button) {
      var mine = button.getAttribute("data-theme-choice") === choice;
      button.setAttribute("aria-pressed", mine ? "true" : "false");
    });
  }

  // Follow the system if that is what was chosen and it changes underneath us.
  media.addEventListener("change", function () {
    if (stored() === "system") {
      var effective = apply("system");
      document.dispatchEvent(
        new CustomEvent("mdr:themechange", {
          detail: { choice: "system", effective: effective },
        })
      );
    }
  });

  function bind() {
    sync(stored());
    document.addEventListener("click", function (event) {
      var button = event.target.closest("[data-theme-choice]");
      if (!button) return;
      event.preventDefault();
      set(button.getAttribute("data-theme-choice"));
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }

  window.mdrTheme = { get: stored, set: set, resolve: resolve };
})();
