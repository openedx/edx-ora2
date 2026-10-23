// Karma configuration
const path = require('path');
const webpackConfig = require('./webpack.prod.config.js');

// Use process.cwd() (guaranteed to be project root when `npm test` runs) to compute
// absolute paths for files outside the basePath (node_modules, require-config.js).
// This avoids any path traversal issues since basePath (src/openassessment/xblock/static)
// is 3 levels deep from src/, not the project root.
const projectRoot = process.cwd();

module.exports = function(config) {
  config.set({

    // base path that will be used to resolve all patterns (eg. files, exclude)
    basePath: 'src/openassessment/xblock/static',


    plugins: [
      'karma-jasmine',
      'karma-jasmine-jquery',
      'karma-chrome-launcher',
      'karma-phantomjs-launcher',
      'karma-coverage',
      'karma-sinon',
      'karma-jasmine-html-reporter',
      'karma-spec-reporter',
      'karma-webpack',
      require("karma-firefox-launcher")
    ],

    // frameworks to use
    // available frameworks: https://npmjs.org/browse/keyword/karma-adapter
    frameworks: ['jasmine-jquery', 'jasmine', 'sinon'],


    // list of files / patterns to load in the browser
    files: [
      'js/lib/jquery.min.js',
      'js/lib/codemirror.js',
      'js/lib/jquery.timepicker.min.js',
      'js/lib/jquery-ui-1.10.4.min.js',
      'js/lib/underscore-min.js',
      // Use absolute paths from projectRoot for files outside src/openassessment/ (node_modules,
      // require-config.js) since basePath is 3 levels deep from src/, not the project root.
      path.resolve(projectRoot, 'node_modules/@babel/polyfill/dist/polyfill.js'),
      path.resolve(projectRoot, 'node_modules/backbone/backbone.js'),
      path.resolve(projectRoot, 'node_modules/backgrid/lib/backgrid.min.js'),
      path.resolve(projectRoot, 'node_modules/requirejs/require.js'),
      path.resolve(projectRoot, 'require-config.js'),
      {
        pattern: path.resolve(projectRoot, 'node_modules/moment-timezone/builds/moment-timezone-with-data.min.js'),
        served: true, included: false
      },
      {
        pattern: path.resolve(projectRoot, 'node_modules/moment/min/moment-with-locales.min.js'),
        served: true, included: false
      },
      //
      { pattern: 'js/fixtures/*.html' },
      { pattern: 'js/spec/*.js', watched: false },
      { pattern: 'js/spec/**/*.js', watched: false },
      { pattern: 'js/src/oa_shared.js', watched: false },
      { pattern: 'js/src/*_index.js', watched: false },
      { pattern: 'js/src/lms/editors/**/*.js', included: false},
      { pattern: 'js/src/**/*.js', watched: false },
      { pattern: 'js/src/**/*.jsx', watched: false },
      { pattern: 'js/spec/**/*.jsx', watched: false },

      // fixtures
      {
        pattern: 'js/fixtures/*.json',
        served: true, included: false
      }
    ],

    // list of files to exclude
    exclude: [
      'js/src/design*.js'
    ],

    // preprocess matching files before serving them to the browser
    // available preprocessors: https://npmjs.org/browse/keyword/karma-preprocessor
    preprocessors: {
      'js/src/*_index.js': ['webpack'],
      'js/src/**/*.js': ['webpack', 'coverage'],
      'js/src/**/*.jsx': ['webpack', 'coverage'],
      'js/spec/*.js': ['webpack'],
      'js/spec/**/*.js': ['webpack'],
      'js/src/oa_shared.js': ['webpack'],
      'js/spec/**/*.jsx': ['webpack'],
    },

    webpack: webpackConfig,

    // test results reporter to use
    reporters: ['spec', 'coverage'],

    coverageReporter: {
      type : 'text'
    },

    // web server port
    port: 9876,


    // enable / disable colors in the output (reporters and logs)
    colors: true,


    // level of logging
    // possible values: config.LOG_DISABLE || config.LOG_ERROR || config.LOG_WARN || config.LOG_INFO || config.LOG_DEBUG
    logLevel: config.LOG_INFO,


    // enable / disable watching file and executing tests whenever any file changes
    autoWatch: false,

    // start these browsers
    // available browser launchers: https://npmjs.org/browse/keyword/karma-launcher

    browsers: [
      'HeadlessChrome'
      // 'HeadlessFirefox'
    ],
    // If chrome headless is not working, try swapping out which line is commented above
    // to use firefox for local dev
    customLaunchers: {
        HeadlessChrome: {
            base: 'ChromeHeadless',
            flags: [
                '--no-sandbox',
                '--headless',
                '--disable-gpu',
                '--disable-translate',
                '--disable-extensions'
            ]
        },
        HeadlessFirefox: {
            base: 'Firefox',
            flags: [
                '--headless',
            ]
        },
    },

    // Continuous Integration mode
    // if true, Karma captures browsers, runs the tests and exits
    singleRun: true,

    resolve: {
      extensions: ['', '.js', '.jsx'],
    }

  });
};
