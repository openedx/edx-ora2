/**
JavaScript shared between all open assessment modules.

WARNING: Don't add anything to this file until you're
absolutely sure there isn't a way to encapsulate it in
an object!
**/


/* Namespace for open assessment */
if (typeof OpenAssessment == "undefined" || !OpenAssessment) {
    OpenAssessment = {};
}


// Stub gettext if the runtime doesn't provide it
if (typeof window.gettext === 'undefined') {
    window.gettext = function(text) { return text; };
}


// If ngettext isn't found (workbench, testing, etc.), return the simplistic english version
if (typeof window.ngetgext === 'undefined') {
    window.ngettext = function (singular_text, plural_text, n) {
        if (n > 1) {
            return plural_text;
        } else {
            return singular_text;
        }
    }
}


// Stub event logging if the runtime doesn't provide it
if (typeof window.Logger === 'undefined') {
    window.Logger = {
        log: function(event_type, data, kwargs) {}
    };
}


// Stub MathJax is the runtime doesn't provide it
if (typeof window.MathJax === 'undefined') {
    window.MathJax = {
        Hub: {
            Typeset: function(data){},
            Queue: function(list){}
        }
    };
}