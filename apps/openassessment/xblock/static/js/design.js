// openassessment: design-focused js
// ====================

// NOTES:
// * this is merely for UI behavior and any work here should be folded into production-level JavaScript files and methods.

function $linkNewWindow(e) {
  window.open($(e.target).attr('href'));
  e.preventDefault();
}

// --------------------

jQuery(document).ready(function($) {

  // removing no-js, accessibility/modernizr marker
  $('html').removeClass('no-js');

  // general link management - new window/tab
  $('a[data-rel="external"]').bind('click', $linkNewWindow);
});

