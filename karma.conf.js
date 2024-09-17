// Karma configuration
const webpackConfig = require('./webpack.prod.config.js');

module.exports = function(config) {
  config.set({

    // base path that will be used to resolve all patterns (eg. files, exclude)
    basePath: 'openassessment/xblock/static',


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
      '../../../node_modules/@babel/polyfill/dist/polyfill.js',
      '../../../node_modules/backbone/backbone.js',
      '../../../node_modules/backgrid/lib/backgrid.min.js',
      '../../../node_modules/requirejs/require.js',
      '../../../require-config.js',
      {
        pattern: '../../../node_modules/moment-timezone/builds/moment-timezone-with-data.min.js',
        served: true, included: false
      },
      {
        pattern: '../../../node_modules/moment/min/moment-with-locales.min.js',
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
