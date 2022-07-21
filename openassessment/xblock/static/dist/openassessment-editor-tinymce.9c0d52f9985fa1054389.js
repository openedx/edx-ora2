/******/ (function(modules) { // webpackBootstrap
/******/ 	// The module cache
/******/ 	var installedModules = {};
/******/
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/
/******/ 		// Check if module is in cache
/******/ 		if(installedModules[moduleId]) {
/******/ 			return installedModules[moduleId].exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = installedModules[moduleId] = {
/******/ 			i: moduleId,
/******/ 			l: false,
/******/ 			exports: {}
/******/ 		};
/******/
/******/ 		// Execute the module function
/******/ 		modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/
/******/ 		// Flag the module as loaded
/******/ 		module.l = true;
/******/
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/
/******/
/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = modules;
/******/
/******/ 	// expose the module cache
/******/ 	__webpack_require__.c = installedModules;
/******/
/******/ 	// define getter function for harmony exports
/******/ 	__webpack_require__.d = function(exports, name, getter) {
/******/ 		if(!__webpack_require__.o(exports, name)) {
/******/ 			Object.defineProperty(exports, name, { enumerable: true, get: getter });
/******/ 		}
/******/ 	};
/******/
/******/ 	// define __esModule on exports
/******/ 	__webpack_require__.r = function(exports) {
/******/ 		if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 			Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 		}
/******/ 		Object.defineProperty(exports, '__esModule', { value: true });
/******/ 	};
/******/
/******/ 	// create a fake namespace object
/******/ 	// mode & 1: value is a module id, require it
/******/ 	// mode & 2: merge all properties of value into the ns
/******/ 	// mode & 4: return value when already ns object
/******/ 	// mode & 8|1: behave like require
/******/ 	__webpack_require__.t = function(value, mode) {
/******/ 		if(mode & 1) value = __webpack_require__(value);
/******/ 		if(mode & 8) return value;
/******/ 		if((mode & 4) && typeof value === 'object' && value && value.__esModule) return value;
/******/ 		var ns = Object.create(null);
/******/ 		__webpack_require__.r(ns);
/******/ 		Object.defineProperty(ns, 'default', { enumerable: true, value: value });
/******/ 		if(mode & 2 && typeof value != 'string') for(var key in value) __webpack_require__.d(ns, key, function(key) { return value[key]; }.bind(null, key));
/******/ 		return ns;
/******/ 	};
/******/
/******/ 	// getDefaultExport function for compatibility with non-harmony modules
/******/ 	__webpack_require__.n = function(module) {
/******/ 		var getter = module && module.__esModule ?
/******/ 			function getDefault() { return module['default']; } :
/******/ 			function getModuleExports() { return module; };
/******/ 		__webpack_require__.d(getter, 'a', getter);
/******/ 		return getter;
/******/ 	};
/******/
/******/ 	// Object.prototype.hasOwnProperty.call
/******/ 	__webpack_require__.o = function(object, property) { return Object.prototype.hasOwnProperty.call(object, property); };
/******/
/******/ 	// __webpack_public_path__
/******/ 	__webpack_require__.p = "/";
/******/
/******/
/******/ 	// Load entry module and return exports
/******/ 	return __webpack_require__(__webpack_require__.s = "./openassessment/xblock/static/js/src/lms/editors/oa_editor_tinymce.js");
/******/ })
/************************************************************************/
/******/ ({

/***/ "./openassessment/xblock/static/js/src/lms/editors/oa_editor_tinymce.js":
/*!******************************************************************************!*\
  !*** ./openassessment/xblock/static/js/src/lms/editors/oa_editor_tinymce.js ***!
  \******************************************************************************/
/*! no static exports found */
/***/ (function(module, exports) {

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

/**
 Handles Response Editor of tinymce type.
 * */
(function (define) {
  var dependencies = [];
  var tinymceCssFile = '/static/js/vendor/tinymce/js/tinymce/skins/studio-tmce4/skin.min.css'; // Create a flag to determine if we are in lms

  var isLMS = typeof window.LmsRuntime !== 'undefined'; // Determine which css file should be loaded to style text in the editor

  var contentCssFile = '/static/studio/js/vendor/tinymce/js/tinymce/skins/studio-tmce4/content.min.css';

  if (isLMS) {
    contentCssFile = '/static/js/vendor/tinymce/js/tinymce/skins/studio-tmce4/content.min.css';
  }

  if (typeof window.tinymce === 'undefined') {
    // If tinymce is not available, we need to load it
    dependencies.push('tinymce');
    dependencies.push('jquery.tinymce'); // we also need to add css for tinymce

    if (!$("link[href='".concat(tinymceCssFile, "']")).length) {
      $("<link href=\"".concat(tinymceCssFile, "\" type=\"text/css\" rel=\"stylesheet\" />")).appendTo('head');
    }
  }

  define(dependencies, function () {
    var EditorTinymce = /*#__PURE__*/function () {
      function EditorTinymce() {
        _classCallCheck(this, EditorTinymce);

        _defineProperty(this, "editorInstances", []);
      }

      _createClass(EditorTinymce, [{
        key: "getTinyMCEConfig",
        value:
        /**
         Build and return TinyMCE Configuration.
         * */
        function getTinyMCEConfig(readonly) {
          var config = {
            menubar: false,
            statusbar: false,
            theme: 'modern',
            skin: 'studio-tmce4',
            height: '300',
            schema: 'html5',
            plugins: 'code image link lists',
            content_css: contentCssFile,
            toolbar: 'formatselect | bold italic underline | link blockquote image | numlist bullist outdent indent | strikethrough | code | undo redo'
          }; // if readonly hide toolbar, menubar and statusbar

          if (readonly) {
            config = Object.assign(config, {
              toolbar: false,
              readonly: 1
            });
          }

          return config;
        }
        /**
         Loads TinyMCE editor.
         Args:
         elements (object): editor elements selected by jQuery
         * */

      }, {
        key: "load",
        value: function load(elements) {
          this.elements = elements;
          var ctrl = this;
          return Promise.all(this.elements.map(function () {
            var _this = this;

            // check if it's readonly
            var disabled = $(this).attr('disabled'); // In LMS with multiple Unit containing ORA Block with tinyMCE enabled,
            // We need to destroy if any previously intialized editor exists for current element.

            var id = $(this).attr('id');

            if (id !== undefined) {
              var existingEditor = tinymce.get(id); // eslint-disable-line

              if (existingEditor) {
                existingEditor.destroy();
              }
            }

            var config = ctrl.getTinyMCEConfig(disabled);
            return new Promise(function (resolve) {
              config.setup = function (editor) {
                return editor.on('init', function () {
                  ctrl.editorInstances.push(editor);
                  resolve();
                });
              };

              $(_this).tinymce(config);
            });
          }));
        }
        /**
         Set on change listener to the editor.
         Args:
         handler (Function)
         * */

      }, {
        key: "setOnChangeListener",
        value: function setOnChangeListener(handler) {
          var _this2 = this;

          ['change', 'keyup', 'drop', 'paste'].forEach(function (eventName) {
            _this2.editorInstances.forEach(function (editor) {
              editor.on(eventName, handler);
            });
          });
        }
        /**
         Set the response texts.
         Retrieve the response texts.
         Args:
         texts (array of strings): If specified, the texts to set for the response.
         Returns:
         array of strings: The current response texts.
         * */

        /* eslint-disable-next-line consistent-return */

      }, {
        key: "response",
        value: function response(texts) {
          if (typeof texts === 'undefined') {
            return this.editorInstances.map(function (editor) {
              var content = editor.getContent(); // Remove linebreaks from TinyMCE output
              // This is a workaround for TinyMCE 4 only,
              // 5.x does not have this bug.

              return content.replace(/(\r\n|\n|\r)/gm, '');
            });
          }

          this.editorInstances.forEach(function (editor, index) {
            editor.setContent(texts[index]);
          });
        }
      }]);

      return EditorTinymce;
    }(); // return a function, to be able to create new instance every time.


    return function () {
      return new EditorTinymce();
    };
  });
}).call(window, window.define || window.RequireJS.define);

/***/ })

/******/ });
//# sourceMappingURL=openassessment-editor-tinymce.9c0d52f9985fa1054389.js.map