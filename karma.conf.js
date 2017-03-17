// Karma configuration

module.exports = function(config) {
  config.set({

    // base path that will be used to resolve all patterns (eg. files, exclude)
    basePath: 'openassessment/xblock/static/',


    plugins: [
      'karma-jasmine',
      'karma-jasmine-jquery',
      'karma-chrome-launcher',
      'karma-phantomjs-launcher',
      'karma-coverage',
      'karma-sinon',
      'karma-jasmine-html-reporter',
      'karma-spec-reporter'
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
      {
        pattern: '../../../node_modules/edx-ui-toolkit/src/js/utils/date-utils.js',
        served: true, included: false
      },
      {
        pattern: '../../../node_modules/edx-ui-toolkit/src/js/utils/string-utils.js',
        served: true, included: false
      },
      //
      'js/src/oa_shared.js',
      'js/src/*.js',
      'js/src/lms/*.js',
      'js/src/studio/*.js',
      'js/spec/test_shared.js',
      'js/spec/*.js',
      'js/spec/lms/*.js',
      'js/spec/studio/*.js',
      // fixtures
      {
        pattern: 'js/fixtures/*.html',
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
      'js/src/*.js': 'coverage',
      'js/src/lms/*.js': 'coverage',
      'js/src/studio/*.js': 'coverage'
    },


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
    browsers: ['PhantomJS'],

    // Continuous Integration mode
    // if true, Karma captures browsers, runs the tests and exits
    singleRun: true

  });

};
