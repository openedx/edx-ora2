// openassessment: design-focused js
// ====================

// NOTES:
// * this is merely for UI behavior and any work here should be folded into production-level JavaScript files and methods.

function $linkNewWindow(e) {
  e.preventDefault();
  window.open($(e.target).attr('href'));
}

function $toggleExpansion(e) {
    e.preventDefault();
    $(e.target).closest('.ui-toggle-visibility').toggleClass('is--collapsed');
}

// --------------------

jQuery(document).ready(function($) {

  // collapse/expand UI
  $('.ui-toggle-visibility ui-toggle-visibility__control').bind('click', toggleExpansion);

  // general link management - new window/tab
  $('a[data-rel="external"]').bind('click', $linkNewWindow);
});

