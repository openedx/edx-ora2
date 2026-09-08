const { createConfig } = require('@openedx/frontend-build');

const config = createConfig('eslint');

// These rule overrides should be removed at a later date, and the associated code fixed.
config.rules["import/no-named-as-default"] = "off";
config.rules["no-underscore-dangle"] = "off";
config.rules["prefer-rest-params"] = "off";
config.rules["no-unused-vars"] = "off";
config.rules["no-param-reassign"] = "off";
config.rules["no-alert"] = "off";
config.rules["no-new"] = "off";
config.rules["func-names"] = "off";
config.rules["max-classes-per-file"] = "off";
config.rules["prefer-destructuring"] = "off";
config.rules["no-prototype-builtins"] = "off";

config.globals["gettext"] = "readonly";
config.globals["ngettext"] = "readonly";
config.globals["$"] = "readonly";
config.globals["MathJax"] = "readonly";
config.globals["_"] = "readonly";
config.globals["Logger"] = "readonly";
config.globals["XBlock"] = "readonly";
config.globals["Backbone"] = "readonly";
config.globals["Backgrid"] = "readonly";
config.globals["rewriteStaticLinks"] = "readonly";

module.exports = config;
