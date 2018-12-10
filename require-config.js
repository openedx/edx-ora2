(function(require, define) {
    'use strict';

    var defineDependency;
    // We do not wish to bundle common libraries (that may also be used by non-RequireJS code on the page
    // into the optimized files. Therefore load these libraries through script tags and explicitly define them.
    // Note that when the optimizer executes this code, window will not be defined.
    if (window) {
        defineDependency = function (globalName, name, noShim) {
            var getGlobalValue = function () {
                    var globalNamePath = globalName.split('.'),
                        result = window,
                        i;
                    for (i = 0; i < globalNamePath.length; i++) {
                        result = result[globalNamePath[i]];
                    }
                    return result;
                },
                globalValue = getGlobalValue();
            if (globalValue) {
                if (noShim) {
                    define(name, {});
                } else {
                    define(name, [], function () {
                        return globalValue;
                    });
                }
            } else {
                console.error('Expected library to be included on page, but not found on window object: ' + name);
            }
        };
        defineDependency('jQuery', 'jquery');
    }

    function getBaseUrlPath() {
        // require-config doesn't play nice with relative paths, but
        // the Travis server, devstack, and staging/production servers all place the
        // node_module files differently in absolute paths - this is a way to retrieve the
        // path to the Jasmine req's as nicely as possible
        var scripts = document.getElementsByTagName("script");
        var fullTag = $(scripts[scripts.length-1]);
        var baseUrl = fullTag.attr('src').split(['require-config'])[0];
        return baseUrl
    }

    require.config({
        baseUrl: getBaseUrlPath(),
        paths: {
            'jquery': './openassessment/xblock/static/js/lib/jquery.min',
            'moment': './node_modules/moment/min/moment-with-locales.min',
            'moment-timezone': './node_modules/moment-timezone/builds/moment-timezone-with-data.min',
            'edx-ui-toolkit/js/utils/date-utils': './node_modules/edx-ui-toolkit/src/js/utils/date-utils',
            'edx-ui-toolkit/js/utils/string-utils': './node_modules/edx-ui-toolkit/src/js/utils/string-utils'
        },
        shim: {
            'jquery': {
                exports: 'jQuery'
            }
        }

    })
}).call(this, require || RequireJS.require, define || RequireJS.define);

