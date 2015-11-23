/**
 JavaScript shared between all open assessment modules.

 WARNING: Don't add anything to this file until you're
 absolutely sure there isn't a way to encapsulate it in
 an object!
 **/

/* Namespace for open assessment */
/* jshint ignore:start */
if (typeof OpenAssessment == "undefined" || !OpenAssessment) {
    OpenAssessment = {};
}
/* jshint ignore:end */

// Stub gettext if the runtime doesn't provide it
if (typeof window.gettext === 'undefined') {
    window.gettext = function(text) { return text; };
}

// If ngettext isn't found (workbench, testing, etc.), return the simplistic english version
if (typeof window.ngetgext === 'undefined') {
    window.ngettext = function(singularText, pluralText, n) {
        if (n > 1) {
            return pluralText;
        } else {
            return singularText;
        }
    };
}

// Stub event logging if the runtime doesn't provide it
if (typeof window.Logger === 'undefined') {
    window.Logger = {
        log: function() {}
    };
}

// Stub MathJax is the runtime doesn't provide it
if (typeof window.MathJax === 'undefined') {
    window.MathJax = {
        Hub: {
            Typeset: function() {},
            Queue: function() {}
        }
    };
}
