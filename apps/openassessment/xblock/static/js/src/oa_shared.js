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
