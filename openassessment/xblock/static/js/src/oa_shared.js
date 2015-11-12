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
    window.ngettext = function (singular_text, plural_text, n) {
        if (n > 1) {
            return plural_text;
        } else {
            return singular_text;
        }
    };
}



/**
 * Takes a templated string and plugs in the placeholder values. Assumes that internationalization
 * has already been handled if necessary.
 *
 * Example usages:
 *     interpolate_text('{title} ({count})', {title: expectedTitle, count: expectedCount}
 *     interpolate_text(
 *         ngettext("{numUsersAdded} student has been added to this cohort",
 *             "{numUsersAdded} students have been added to this cohort", numUsersAdded),
 *         {numUsersAdded: numUsersAdded}
 *     );
 *
 * @param text the templated text
 * @param values the templated dictionary values
 * @returns the text with placeholder values filled in
 */
if (typeof window.interpolate_text === 'undefined') {
    window.interpolate_text = function (text, values) {
        return _.template(text, values, {interpolate: /\{(.+?)\}/g});
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