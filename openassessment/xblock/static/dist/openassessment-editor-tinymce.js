/*
 * ATTENTION: An "eval-source-map" devtool has been used.
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file with attached SourceMaps in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
/******/ (() => { // webpackBootstrap
/******/ 	var __webpack_modules__ = ({

/***/ "./openassessment/xblock/static/js/src/lms/editors/oa_editor_tinymce.js":
/*!******************************************************************************!*\
  !*** ./openassessment/xblock/static/js/src/lms/editors/oa_editor_tinymce.js ***!
  \******************************************************************************/
/***/ (() => {

eval("function _typeof(o) { \"@babel/helpers - typeof\"; return _typeof = \"function\" == typeof Symbol && \"symbol\" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && \"function\" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? \"symbol\" : typeof o; }, _typeof(o); }\nfunction _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError(\"Cannot call a class as a function\"); } }\nfunction _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if (\"value\" in descriptor) descriptor.writable = true; Object.defineProperty(target, _toPropertyKey(descriptor.key), descriptor); } }\nfunction _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); Object.defineProperty(Constructor, \"prototype\", { writable: false }); return Constructor; }\nfunction _defineProperty(obj, key, value) { key = _toPropertyKey(key); if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }\nfunction _toPropertyKey(arg) { var key = _toPrimitive(arg, \"string\"); return _typeof(key) === \"symbol\" ? key : String(key); }\nfunction _toPrimitive(input, hint) { if (_typeof(input) !== \"object\" || input === null) return input; var prim = input[Symbol.toPrimitive]; if (prim !== undefined) { var res = prim.call(input, hint || \"default\"); if (_typeof(res) !== \"object\") return res; throw new TypeError(\"@@toPrimitive must return a primitive value.\"); } return (hint === \"string\" ? String : Number)(input); }\n/**\n Handles Response Editor of tinymce type.\n * */\n\n(function (define) {\n  var dependencies = [];\n\n  // Create a flag to determine if we are in lms\n  var isLMS = typeof window.LmsRuntime !== 'undefined';\n\n  // Determine which css file should be loaded to style text in the editor\n  var baseUrl = '/static/studio/js/vendor/tinymce/js/tinymce/';\n  if (isLMS) {\n    baseUrl = '/static/js/vendor/tinymce/js/tinymce/';\n  }\n  if (typeof window.tinymce === 'undefined') {\n    // If tinymce is not available, we need to load it\n    dependencies.push('tinymce');\n    dependencies.push('jquery.tinymce');\n  }\n  define(dependencies, function () {\n    var EditorTinymce = /*#__PURE__*/function () {\n      function EditorTinymce() {\n        _classCallCheck(this, EditorTinymce);\n        _defineProperty(this, \"editorInstances\", []);\n      }\n      _createClass(EditorTinymce, [{\n        key: \"getTinyMCEConfig\",\n        value:\n        /**\n         Build and return TinyMCE Configuration.\n         * */\n        function getTinyMCEConfig(readonly) {\n          var config = {\n            menubar: false,\n            statusbar: false,\n            base_url: baseUrl,\n            theme: 'silver',\n            skin: 'studio-tmce5',\n            content_css: 'studio-tmce5',\n            height: '300',\n            schema: 'html5',\n            plugins: 'code image link lists',\n            toolbar: 'formatselect | bold italic underline | link blockquote image | numlist bullist outdent indent | strikethrough | code | undo redo'\n          };\n\n          // if readonly hide toolbar, menubar and statusbar\n          if (readonly) {\n            config = Object.assign(config, {\n              toolbar: false,\n              readonly: 1\n            });\n          }\n          return config;\n        }\n\n        /**\n         Loads TinyMCE editor.\n         Args:\n         elements (object): editor elements selected by jQuery\n         * */\n      }, {\n        key: \"load\",\n        value: function load(elements) {\n          this.elements = elements;\n          var ctrl = this;\n          return Promise.all(this.elements.map(function () {\n            var _this = this;\n            // check if it's readonly\n            var disabled = $(this).attr('disabled');\n\n            // In LMS with multiple Unit containing ORA Block with tinyMCE enabled,\n            // We need to destroy if any previously intialized editor exists for current element.\n            var id = $(this).attr('id');\n            if (id !== undefined) {\n              var existingEditor = tinymce.get(id); // eslint-disable-line\n              if (existingEditor) {\n                existingEditor.destroy();\n              }\n            }\n            var config = ctrl.getTinyMCEConfig(disabled);\n            return new Promise(function (resolve) {\n              config.setup = function (editor) {\n                return editor.on('init', function () {\n                  ctrl.editorInstances.push(editor);\n                  resolve();\n                });\n              };\n              $(_this).tinymce(config);\n            });\n          }));\n        }\n\n        /**\n         Set on change listener to the editor.\n         Args:\n         handler (Function)\n         * */\n      }, {\n        key: \"setOnChangeListener\",\n        value: function setOnChangeListener(handler) {\n          var _this2 = this;\n          ['change', 'keyup', 'drop', 'paste'].forEach(function (eventName) {\n            _this2.editorInstances.forEach(function (editor) {\n              editor.on(eventName, handler);\n            });\n          });\n        }\n\n        /**\n         Set the response texts.\n         Retrieve the response texts.\n         Args:\n         texts (array of strings): If specified, the texts to set for the response.\n         Returns:\n         array of strings: The current response texts.\n         * */\n        /* eslint-disable-next-line consistent-return */\n      }, {\n        key: \"response\",\n        value: function response(texts) {\n          if (typeof texts === 'undefined') {\n            return this.editorInstances.map(function (editor) {\n              return editor.getContent();\n            });\n          }\n          this.editorInstances.forEach(function (editor, index) {\n            editor.setContent(texts[index]);\n          });\n        }\n      }]);\n      return EditorTinymce;\n    }(); // return a function, to be able to create new instance every time.\n    return function () {\n      return new EditorTinymce();\n    };\n  });\n}).call(window, window.define || window.RequireJS.define);//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJuYW1lcyI6WyJkZWZpbmUiLCJkZXBlbmRlbmNpZXMiLCJpc0xNUyIsIndpbmRvdyIsIkxtc1J1bnRpbWUiLCJiYXNlVXJsIiwidGlueW1jZSIsInB1c2giLCJFZGl0b3JUaW55bWNlIiwiX2NsYXNzQ2FsbENoZWNrIiwiX2RlZmluZVByb3BlcnR5IiwiX2NyZWF0ZUNsYXNzIiwia2V5IiwidmFsdWUiLCJnZXRUaW55TUNFQ29uZmlnIiwicmVhZG9ubHkiLCJjb25maWciLCJtZW51YmFyIiwic3RhdHVzYmFyIiwiYmFzZV91cmwiLCJ0aGVtZSIsInNraW4iLCJjb250ZW50X2NzcyIsImhlaWdodCIsInNjaGVtYSIsInBsdWdpbnMiLCJ0b29sYmFyIiwiT2JqZWN0IiwiYXNzaWduIiwibG9hZCIsImVsZW1lbnRzIiwiY3RybCIsIlByb21pc2UiLCJhbGwiLCJtYXAiLCJfdGhpcyIsImRpc2FibGVkIiwiJCIsImF0dHIiLCJpZCIsInVuZGVmaW5lZCIsImV4aXN0aW5nRWRpdG9yIiwiZ2V0IiwiZGVzdHJveSIsInJlc29sdmUiLCJzZXR1cCIsImVkaXRvciIsIm9uIiwiZWRpdG9ySW5zdGFuY2VzIiwic2V0T25DaGFuZ2VMaXN0ZW5lciIsImhhbmRsZXIiLCJfdGhpczIiLCJmb3JFYWNoIiwiZXZlbnROYW1lIiwicmVzcG9uc2UiLCJ0ZXh0cyIsImdldENvbnRlbnQiLCJpbmRleCIsInNldENvbnRlbnQiLCJjYWxsIiwiUmVxdWlyZUpTIl0sInNvdXJjZXMiOlsid2VicGFjazovL2VkeC1vcmEyLy4vb3BlbmFzc2Vzc21lbnQveGJsb2NrL3N0YXRpYy9qcy9zcmMvbG1zL2VkaXRvcnMvb2FfZWRpdG9yX3RpbnltY2UuanM/NjJmYSJdLCJzb3VyY2VzQ29udGVudCI6WyIvKipcbiBIYW5kbGVzIFJlc3BvbnNlIEVkaXRvciBvZiB0aW55bWNlIHR5cGUuXG4gKiAqL1xuXG4oZnVuY3Rpb24gKGRlZmluZSkge1xuICBjb25zdCBkZXBlbmRlbmNpZXMgPSBbXTtcblxuICAvLyBDcmVhdGUgYSBmbGFnIHRvIGRldGVybWluZSBpZiB3ZSBhcmUgaW4gbG1zXG4gIGNvbnN0IGlzTE1TID0gdHlwZW9mIHdpbmRvdy5MbXNSdW50aW1lICE9PSAndW5kZWZpbmVkJztcblxuICAvLyBEZXRlcm1pbmUgd2hpY2ggY3NzIGZpbGUgc2hvdWxkIGJlIGxvYWRlZCB0byBzdHlsZSB0ZXh0IGluIHRoZSBlZGl0b3JcbiAgbGV0IGJhc2VVcmwgPSAnL3N0YXRpYy9zdHVkaW8vanMvdmVuZG9yL3RpbnltY2UvanMvdGlueW1jZS8nO1xuICBpZiAoaXNMTVMpIHtcbiAgICBiYXNlVXJsID0gJy9zdGF0aWMvanMvdmVuZG9yL3RpbnltY2UvanMvdGlueW1jZS8nO1xuICB9XG5cbiAgaWYgKHR5cGVvZiB3aW5kb3cudGlueW1jZSA9PT0gJ3VuZGVmaW5lZCcpIHtcbiAgICAvLyBJZiB0aW55bWNlIGlzIG5vdCBhdmFpbGFibGUsIHdlIG5lZWQgdG8gbG9hZCBpdFxuICAgIGRlcGVuZGVuY2llcy5wdXNoKCd0aW55bWNlJyk7XG4gICAgZGVwZW5kZW5jaWVzLnB1c2goJ2pxdWVyeS50aW55bWNlJyk7XG4gIH1cblxuICBkZWZpbmUoZGVwZW5kZW5jaWVzLCAoKSA9PiB7XG4gICAgY2xhc3MgRWRpdG9yVGlueW1jZSB7XG4gICAgICBlZGl0b3JJbnN0YW5jZXMgPSBbXTtcblxuICAgICAgLyoqXG4gICAgICAgQnVpbGQgYW5kIHJldHVybiBUaW55TUNFIENvbmZpZ3VyYXRpb24uXG4gICAgICAgKiAqL1xuICAgICAgZ2V0VGlueU1DRUNvbmZpZyhyZWFkb25seSkge1xuICAgICAgICBsZXQgY29uZmlnID0ge1xuICAgICAgICAgIG1lbnViYXI6IGZhbHNlLFxuICAgICAgICAgIHN0YXR1c2JhcjogZmFsc2UsXG4gICAgICAgICAgYmFzZV91cmw6IGJhc2VVcmwsXG4gICAgICAgICAgdGhlbWU6ICdzaWx2ZXInLFxuICAgICAgICAgIHNraW46ICdzdHVkaW8tdG1jZTUnLFxuICAgICAgICAgIGNvbnRlbnRfY3NzOiAnc3R1ZGlvLXRtY2U1JyxcbiAgICAgICAgICBoZWlnaHQ6ICczMDAnLFxuICAgICAgICAgIHNjaGVtYTogJ2h0bWw1JyxcbiAgICAgICAgICBwbHVnaW5zOiAnY29kZSBpbWFnZSBsaW5rIGxpc3RzJyxcbiAgICAgICAgICB0b29sYmFyOiAnZm9ybWF0c2VsZWN0IHwgYm9sZCBpdGFsaWMgdW5kZXJsaW5lIHwgbGluayBibG9ja3F1b3RlIGltYWdlIHwgbnVtbGlzdCBidWxsaXN0IG91dGRlbnQgaW5kZW50IHwgc3RyaWtldGhyb3VnaCB8IGNvZGUgfCB1bmRvIHJlZG8nLFxuICAgICAgICB9O1xuXG4gICAgICAgIC8vIGlmIHJlYWRvbmx5IGhpZGUgdG9vbGJhciwgbWVudWJhciBhbmQgc3RhdHVzYmFyXG4gICAgICAgIGlmIChyZWFkb25seSkge1xuICAgICAgICAgIGNvbmZpZyA9IE9iamVjdC5hc3NpZ24oY29uZmlnLCB7XG4gICAgICAgICAgICB0b29sYmFyOiBmYWxzZSxcbiAgICAgICAgICAgIHJlYWRvbmx5OiAxLFxuICAgICAgICAgIH0pO1xuICAgICAgICB9XG5cbiAgICAgICAgcmV0dXJuIGNvbmZpZztcbiAgICAgIH1cblxuICAgICAgLyoqXG4gICAgICAgTG9hZHMgVGlueU1DRSBlZGl0b3IuXG4gICAgICAgQXJnczpcbiAgICAgICBlbGVtZW50cyAob2JqZWN0KTogZWRpdG9yIGVsZW1lbnRzIHNlbGVjdGVkIGJ5IGpRdWVyeVxuICAgICAgICogKi9cbiAgICAgIGxvYWQoZWxlbWVudHMpIHtcbiAgICAgICAgdGhpcy5lbGVtZW50cyA9IGVsZW1lbnRzO1xuXG4gICAgICAgIGNvbnN0IGN0cmwgPSB0aGlzO1xuXG4gICAgICAgIHJldHVybiBQcm9taXNlLmFsbCh0aGlzLmVsZW1lbnRzLm1hcChmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgLy8gY2hlY2sgaWYgaXQncyByZWFkb25seVxuICAgICAgICAgIGNvbnN0IGRpc2FibGVkID0gJCh0aGlzKS5hdHRyKCdkaXNhYmxlZCcpO1xuXG4gICAgICAgICAgLy8gSW4gTE1TIHdpdGggbXVsdGlwbGUgVW5pdCBjb250YWluaW5nIE9SQSBCbG9jayB3aXRoIHRpbnlNQ0UgZW5hYmxlZCxcbiAgICAgICAgICAvLyBXZSBuZWVkIHRvIGRlc3Ryb3kgaWYgYW55IHByZXZpb3VzbHkgaW50aWFsaXplZCBlZGl0b3IgZXhpc3RzIGZvciBjdXJyZW50IGVsZW1lbnQuXG4gICAgICAgICAgY29uc3QgaWQgPSAkKHRoaXMpLmF0dHIoJ2lkJyk7XG4gICAgICAgICAgaWYgKGlkICE9PSB1bmRlZmluZWQpIHtcbiAgICAgICAgICAgIGNvbnN0IGV4aXN0aW5nRWRpdG9yID0gdGlueW1jZS5nZXQoaWQpOyAvLyBlc2xpbnQtZGlzYWJsZS1saW5lXG4gICAgICAgICAgICBpZiAoZXhpc3RpbmdFZGl0b3IpIHtcbiAgICAgICAgICAgICAgZXhpc3RpbmdFZGl0b3IuZGVzdHJveSgpO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH1cblxuICAgICAgICAgIGNvbnN0IGNvbmZpZyA9IGN0cmwuZ2V0VGlueU1DRUNvbmZpZyhkaXNhYmxlZCk7XG4gICAgICAgICAgcmV0dXJuIG5ldyBQcm9taXNlKHJlc29sdmUgPT4ge1xuICAgICAgICAgICAgY29uZmlnLnNldHVwID0gZWRpdG9yID0+IGVkaXRvci5vbignaW5pdCcsICgpID0+IHtcbiAgICAgICAgICAgICAgY3RybC5lZGl0b3JJbnN0YW5jZXMucHVzaChlZGl0b3IpO1xuICAgICAgICAgICAgICByZXNvbHZlKCk7XG4gICAgICAgICAgICB9KTtcbiAgICAgICAgICAgICQodGhpcykudGlueW1jZShjb25maWcpO1xuICAgICAgICAgIH0pO1xuICAgICAgICB9KSk7XG4gICAgICB9XG5cbiAgICAgIC8qKlxuICAgICAgIFNldCBvbiBjaGFuZ2UgbGlzdGVuZXIgdG8gdGhlIGVkaXRvci5cbiAgICAgICBBcmdzOlxuICAgICAgIGhhbmRsZXIgKEZ1bmN0aW9uKVxuICAgICAgICogKi9cbiAgICAgIHNldE9uQ2hhbmdlTGlzdGVuZXIoaGFuZGxlcikge1xuICAgICAgICBbJ2NoYW5nZScsICdrZXl1cCcsICdkcm9wJywgJ3Bhc3RlJ10uZm9yRWFjaChldmVudE5hbWUgPT4ge1xuICAgICAgICAgIHRoaXMuZWRpdG9ySW5zdGFuY2VzLmZvckVhY2goZWRpdG9yID0+IHtcbiAgICAgICAgICAgIGVkaXRvci5vbihldmVudE5hbWUsIGhhbmRsZXIpO1xuICAgICAgICAgIH0pO1xuICAgICAgICB9KTtcbiAgICAgIH1cblxuICAgICAgLyoqXG4gICAgICAgU2V0IHRoZSByZXNwb25zZSB0ZXh0cy5cbiAgICAgICBSZXRyaWV2ZSB0aGUgcmVzcG9uc2UgdGV4dHMuXG4gICAgICAgQXJnczpcbiAgICAgICB0ZXh0cyAoYXJyYXkgb2Ygc3RyaW5ncyk6IElmIHNwZWNpZmllZCwgdGhlIHRleHRzIHRvIHNldCBmb3IgdGhlIHJlc3BvbnNlLlxuICAgICAgIFJldHVybnM6XG4gICAgICAgYXJyYXkgb2Ygc3RyaW5nczogVGhlIGN1cnJlbnQgcmVzcG9uc2UgdGV4dHMuXG4gICAgICAgKiAqL1xuICAgICAgLyogZXNsaW50LWRpc2FibGUtbmV4dC1saW5lIGNvbnNpc3RlbnQtcmV0dXJuICovXG4gICAgICByZXNwb25zZSh0ZXh0cykge1xuICAgICAgICBpZiAodHlwZW9mIHRleHRzID09PSAndW5kZWZpbmVkJykge1xuICAgICAgICAgIHJldHVybiB0aGlzLmVkaXRvckluc3RhbmNlcy5tYXAoZWRpdG9yID0+IGVkaXRvci5nZXRDb250ZW50KCkpO1xuICAgICAgICB9XG4gICAgICAgIHRoaXMuZWRpdG9ySW5zdGFuY2VzLmZvckVhY2goKGVkaXRvciwgaW5kZXgpID0+IHtcbiAgICAgICAgICBlZGl0b3Iuc2V0Q29udGVudCh0ZXh0c1tpbmRleF0pO1xuICAgICAgICB9KTtcbiAgICAgIH1cbiAgICB9XG5cbiAgICAvLyByZXR1cm4gYSBmdW5jdGlvbiwgdG8gYmUgYWJsZSB0byBjcmVhdGUgbmV3IGluc3RhbmNlIGV2ZXJ5IHRpbWUuXG4gICAgcmV0dXJuIGZ1bmN0aW9uICgpIHtcbiAgICAgIHJldHVybiBuZXcgRWRpdG9yVGlueW1jZSgpO1xuICAgIH07XG4gIH0pO1xufSkuY2FsbCh3aW5kb3csIHdpbmRvdy5kZWZpbmUgfHwgd2luZG93LlJlcXVpcmVKUy5kZWZpbmUpO1xuIl0sIm1hcHBpbmdzIjoiOzs7Ozs7O0FBQUE7QUFDQTtBQUNBOztBQUVBLENBQUMsVUFBVUEsTUFBTSxFQUFFO0VBQ2pCLElBQU1DLFlBQVksR0FBRyxFQUFFOztFQUV2QjtFQUNBLElBQU1DLEtBQUssR0FBRyxPQUFPQyxNQUFNLENBQUNDLFVBQVUsS0FBSyxXQUFXOztFQUV0RDtFQUNBLElBQUlDLE9BQU8sR0FBRyw4Q0FBOEM7RUFDNUQsSUFBSUgsS0FBSyxFQUFFO0lBQ1RHLE9BQU8sR0FBRyx1Q0FBdUM7RUFDbkQ7RUFFQSxJQUFJLE9BQU9GLE1BQU0sQ0FBQ0csT0FBTyxLQUFLLFdBQVcsRUFBRTtJQUN6QztJQUNBTCxZQUFZLENBQUNNLElBQUksQ0FBQyxTQUFTLENBQUM7SUFDNUJOLFlBQVksQ0FBQ00sSUFBSSxDQUFDLGdCQUFnQixDQUFDO0VBQ3JDO0VBRUFQLE1BQU0sQ0FBQ0MsWUFBWSxFQUFFLFlBQU07SUFBQSxJQUNuQk8sYUFBYTtNQUFBLFNBQUFBLGNBQUE7UUFBQUMsZUFBQSxPQUFBRCxhQUFBO1FBQUFFLGVBQUEsMEJBQ0MsRUFBRTtNQUFBO01BQUFDLFlBQUEsQ0FBQUgsYUFBQTtRQUFBSSxHQUFBO1FBQUFDLEtBQUE7UUFFcEI7QUFDTjtBQUNBO1FBQ00sU0FBQUMsaUJBQWlCQyxRQUFRLEVBQUU7VUFDekIsSUFBSUMsTUFBTSxHQUFHO1lBQ1hDLE9BQU8sRUFBRSxLQUFLO1lBQ2RDLFNBQVMsRUFBRSxLQUFLO1lBQ2hCQyxRQUFRLEVBQUVkLE9BQU87WUFDakJlLEtBQUssRUFBRSxRQUFRO1lBQ2ZDLElBQUksRUFBRSxjQUFjO1lBQ3BCQyxXQUFXLEVBQUUsY0FBYztZQUMzQkMsTUFBTSxFQUFFLEtBQUs7WUFDYkMsTUFBTSxFQUFFLE9BQU87WUFDZkMsT0FBTyxFQUFFLHVCQUF1QjtZQUNoQ0MsT0FBTyxFQUFFO1VBQ1gsQ0FBQzs7VUFFRDtVQUNBLElBQUlYLFFBQVEsRUFBRTtZQUNaQyxNQUFNLEdBQUdXLE1BQU0sQ0FBQ0MsTUFBTSxDQUFDWixNQUFNLEVBQUU7Y0FDN0JVLE9BQU8sRUFBRSxLQUFLO2NBQ2RYLFFBQVEsRUFBRTtZQUNaLENBQUMsQ0FBQztVQUNKO1VBRUEsT0FBT0MsTUFBTTtRQUNmOztRQUVBO0FBQ047QUFDQTtBQUNBO0FBQ0E7TUFKTTtRQUFBSixHQUFBO1FBQUFDLEtBQUEsRUFLQSxTQUFBZ0IsS0FBS0MsUUFBUSxFQUFFO1VBQ2IsSUFBSSxDQUFDQSxRQUFRLEdBQUdBLFFBQVE7VUFFeEIsSUFBTUMsSUFBSSxHQUFHLElBQUk7VUFFakIsT0FBT0MsT0FBTyxDQUFDQyxHQUFHLENBQUMsSUFBSSxDQUFDSCxRQUFRLENBQUNJLEdBQUcsQ0FBQyxZQUFZO1lBQUEsSUFBQUMsS0FBQTtZQUMvQztZQUNBLElBQU1DLFFBQVEsR0FBR0MsQ0FBQyxDQUFDLElBQUksQ0FBQyxDQUFDQyxJQUFJLENBQUMsVUFBVSxDQUFDOztZQUV6QztZQUNBO1lBQ0EsSUFBTUMsRUFBRSxHQUFHRixDQUFDLENBQUMsSUFBSSxDQUFDLENBQUNDLElBQUksQ0FBQyxJQUFJLENBQUM7WUFDN0IsSUFBSUMsRUFBRSxLQUFLQyxTQUFTLEVBQUU7Y0FDcEIsSUFBTUMsY0FBYyxHQUFHbkMsT0FBTyxDQUFDb0MsR0FBRyxDQUFDSCxFQUFFLENBQUMsQ0FBQyxDQUFDO2NBQ3hDLElBQUlFLGNBQWMsRUFBRTtnQkFDbEJBLGNBQWMsQ0FBQ0UsT0FBTyxDQUFDLENBQUM7Y0FDMUI7WUFDRjtZQUVBLElBQU0zQixNQUFNLEdBQUdlLElBQUksQ0FBQ2pCLGdCQUFnQixDQUFDc0IsUUFBUSxDQUFDO1lBQzlDLE9BQU8sSUFBSUosT0FBTyxDQUFDLFVBQUFZLE9BQU8sRUFBSTtjQUM1QjVCLE1BQU0sQ0FBQzZCLEtBQUssR0FBRyxVQUFBQyxNQUFNO2dCQUFBLE9BQUlBLE1BQU0sQ0FBQ0MsRUFBRSxDQUFDLE1BQU0sRUFBRSxZQUFNO2tCQUMvQ2hCLElBQUksQ0FBQ2lCLGVBQWUsQ0FBQ3pDLElBQUksQ0FBQ3VDLE1BQU0sQ0FBQztrQkFDakNGLE9BQU8sQ0FBQyxDQUFDO2dCQUNYLENBQUMsQ0FBQztjQUFBO2NBQ0ZQLENBQUMsQ0FBQ0YsS0FBSSxDQUFDLENBQUM3QixPQUFPLENBQUNVLE1BQU0sQ0FBQztZQUN6QixDQUFDLENBQUM7VUFDSixDQUFDLENBQUMsQ0FBQztRQUNMOztRQUVBO0FBQ047QUFDQTtBQUNBO0FBQ0E7TUFKTTtRQUFBSixHQUFBO1FBQUFDLEtBQUEsRUFLQSxTQUFBb0Msb0JBQW9CQyxPQUFPLEVBQUU7VUFBQSxJQUFBQyxNQUFBO1VBQzNCLENBQUMsUUFBUSxFQUFFLE9BQU8sRUFBRSxNQUFNLEVBQUUsT0FBTyxDQUFDLENBQUNDLE9BQU8sQ0FBQyxVQUFBQyxTQUFTLEVBQUk7WUFDeERGLE1BQUksQ0FBQ0gsZUFBZSxDQUFDSSxPQUFPLENBQUMsVUFBQU4sTUFBTSxFQUFJO2NBQ3JDQSxNQUFNLENBQUNDLEVBQUUsQ0FBQ00sU0FBUyxFQUFFSCxPQUFPLENBQUM7WUFDL0IsQ0FBQyxDQUFDO1VBQ0osQ0FBQyxDQUFDO1FBQ0o7O1FBRUE7QUFDTjtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtRQUNNO01BQUE7UUFBQXRDLEdBQUE7UUFBQUMsS0FBQSxFQUNBLFNBQUF5QyxTQUFTQyxLQUFLLEVBQUU7VUFDZCxJQUFJLE9BQU9BLEtBQUssS0FBSyxXQUFXLEVBQUU7WUFDaEMsT0FBTyxJQUFJLENBQUNQLGVBQWUsQ0FBQ2QsR0FBRyxDQUFDLFVBQUFZLE1BQU07Y0FBQSxPQUFJQSxNQUFNLENBQUNVLFVBQVUsQ0FBQyxDQUFDO1lBQUEsRUFBQztVQUNoRTtVQUNBLElBQUksQ0FBQ1IsZUFBZSxDQUFDSSxPQUFPLENBQUMsVUFBQ04sTUFBTSxFQUFFVyxLQUFLLEVBQUs7WUFDOUNYLE1BQU0sQ0FBQ1ksVUFBVSxDQUFDSCxLQUFLLENBQUNFLEtBQUssQ0FBQyxDQUFDO1VBQ2pDLENBQUMsQ0FBQztRQUNKO01BQUM7TUFBQSxPQUFBakQsYUFBQTtJQUFBLEtBR0g7SUFDQSxPQUFPLFlBQVk7TUFDakIsT0FBTyxJQUFJQSxhQUFhLENBQUMsQ0FBQztJQUM1QixDQUFDO0VBQ0gsQ0FBQyxDQUFDO0FBQ0osQ0FBQyxFQUFFbUQsSUFBSSxDQUFDeEQsTUFBTSxFQUFFQSxNQUFNLENBQUNILE1BQU0sSUFBSUcsTUFBTSxDQUFDeUQsU0FBUyxDQUFDNUQsTUFBTSxDQUFDIiwiZmlsZSI6Ii4vb3BlbmFzc2Vzc21lbnQveGJsb2NrL3N0YXRpYy9qcy9zcmMvbG1zL2VkaXRvcnMvb2FfZWRpdG9yX3RpbnltY2UuanMiLCJzb3VyY2VSb290IjoiIn0=\n//# sourceURL=webpack-internal:///./openassessment/xblock/static/js/src/lms/editors/oa_editor_tinymce.js\n");

/***/ })

/******/ 	});
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			if (cachedModule.error !== undefined) throw cachedModule.error;
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		try {
/******/ 			var execOptions = { id: moduleId, module: module, factory: __webpack_modules__[moduleId], require: __webpack_require__ };
/******/ 			__webpack_require__.i.forEach(function(handler) { handler(execOptions); });
/******/ 			module = execOptions.module;
/******/ 			execOptions.factory.call(module.exports, module, module.exports, execOptions.require);
/******/ 		} catch(e) {
/******/ 			module.error = e;
/******/ 			throw e;
/******/ 		}
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = __webpack_modules__;
/******/ 	
/******/ 	// expose the module cache
/******/ 	__webpack_require__.c = __webpack_module_cache__;
/******/ 	
/******/ 	// expose the module execution interceptor
/******/ 	__webpack_require__.i = [];
/******/ 	
/************************************************************************/
/******/ 	/* webpack/runtime/get javascript update chunk filename */
/******/ 	(() => {
/******/ 		// This function allow to reference all chunks
/******/ 		__webpack_require__.hu = (chunkId) => {
/******/ 			// return url for filenames based on template
/******/ 			return "" + chunkId + "." + __webpack_require__.h() + ".hot-update.js";
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/get mini-css chunk filename */
/******/ 	(() => {
/******/ 		// This function allow to reference all chunks
/******/ 		__webpack_require__.miniCssF = (chunkId) => {
/******/ 			// return url for filenames based on template
/******/ 			return undefined;
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/get update manifest filename */
/******/ 	(() => {
/******/ 		__webpack_require__.hmrF = () => ("openassessment-editor-tinymce." + __webpack_require__.h() + ".hot-update.json");
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/getFullHash */
/******/ 	(() => {
/******/ 		__webpack_require__.h = () => ("db0ab770823fcdf9420b")
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/global */
/******/ 	(() => {
/******/ 		__webpack_require__.g = (function() {
/******/ 			if (typeof globalThis === 'object') return globalThis;
/******/ 			try {
/******/ 				return this || new Function('return this')();
/******/ 			} catch (e) {
/******/ 				if (typeof window === 'object') return window;
/******/ 			}
/******/ 		})();
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/hasOwnProperty shorthand */
/******/ 	(() => {
/******/ 		__webpack_require__.o = (obj, prop) => (Object.prototype.hasOwnProperty.call(obj, prop))
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/load script */
/******/ 	(() => {
/******/ 		var inProgress = {};
/******/ 		var dataWebpackPrefix = "edx-ora2:";
/******/ 		// loadScript function to load a script via script tag
/******/ 		__webpack_require__.l = (url, done, key, chunkId) => {
/******/ 			if(inProgress[url]) { inProgress[url].push(done); return; }
/******/ 			var script, needAttach;
/******/ 			if(key !== undefined) {
/******/ 				var scripts = document.getElementsByTagName("script");
/******/ 				for(var i = 0; i < scripts.length; i++) {
/******/ 					var s = scripts[i];
/******/ 					if(s.getAttribute("src") == url || s.getAttribute("data-webpack") == dataWebpackPrefix + key) { script = s; break; }
/******/ 				}
/******/ 			}
/******/ 			if(!script) {
/******/ 				needAttach = true;
/******/ 				script = document.createElement('script');
/******/ 		
/******/ 				script.charset = 'utf-8';
/******/ 				script.timeout = 120;
/******/ 				if (__webpack_require__.nc) {
/******/ 					script.setAttribute("nonce", __webpack_require__.nc);
/******/ 				}
/******/ 				script.setAttribute("data-webpack", dataWebpackPrefix + key);
/******/ 		
/******/ 				script.src = url;
/******/ 			}
/******/ 			inProgress[url] = [done];
/******/ 			var onScriptComplete = (prev, event) => {
/******/ 				// avoid mem leaks in IE.
/******/ 				script.onerror = script.onload = null;
/******/ 				clearTimeout(timeout);
/******/ 				var doneFns = inProgress[url];
/******/ 				delete inProgress[url];
/******/ 				script.parentNode && script.parentNode.removeChild(script);
/******/ 				doneFns && doneFns.forEach((fn) => (fn(event)));
/******/ 				if(prev) return prev(event);
/******/ 			}
/******/ 			var timeout = setTimeout(onScriptComplete.bind(null, undefined, { type: 'timeout', target: script }), 120000);
/******/ 			script.onerror = onScriptComplete.bind(null, script.onerror);
/******/ 			script.onload = onScriptComplete.bind(null, script.onload);
/******/ 			needAttach && document.head.appendChild(script);
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/hot module replacement */
/******/ 	(() => {
/******/ 		var currentModuleData = {};
/******/ 		var installedModules = __webpack_require__.c;
/******/ 		
/******/ 		// module and require creation
/******/ 		var currentChildModule;
/******/ 		var currentParents = [];
/******/ 		
/******/ 		// status
/******/ 		var registeredStatusHandlers = [];
/******/ 		var currentStatus = "idle";
/******/ 		
/******/ 		// while downloading
/******/ 		var blockingPromises = 0;
/******/ 		var blockingPromisesWaiting = [];
/******/ 		
/******/ 		// The update info
/******/ 		var currentUpdateApplyHandlers;
/******/ 		var queuedInvalidatedModules;
/******/ 		
/******/ 		// eslint-disable-next-line no-unused-vars
/******/ 		__webpack_require__.hmrD = currentModuleData;
/******/ 		
/******/ 		__webpack_require__.i.push(function (options) {
/******/ 			var module = options.module;
/******/ 			var require = createRequire(options.require, options.id);
/******/ 			module.hot = createModuleHotObject(options.id, module);
/******/ 			module.parents = currentParents;
/******/ 			module.children = [];
/******/ 			currentParents = [];
/******/ 			options.require = require;
/******/ 		});
/******/ 		
/******/ 		__webpack_require__.hmrC = {};
/******/ 		__webpack_require__.hmrI = {};
/******/ 		
/******/ 		function createRequire(require, moduleId) {
/******/ 			var me = installedModules[moduleId];
/******/ 			if (!me) return require;
/******/ 			var fn = function (request) {
/******/ 				if (me.hot.active) {
/******/ 					if (installedModules[request]) {
/******/ 						var parents = installedModules[request].parents;
/******/ 						if (parents.indexOf(moduleId) === -1) {
/******/ 							parents.push(moduleId);
/******/ 						}
/******/ 					} else {
/******/ 						currentParents = [moduleId];
/******/ 						currentChildModule = request;
/******/ 					}
/******/ 					if (me.children.indexOf(request) === -1) {
/******/ 						me.children.push(request);
/******/ 					}
/******/ 				} else {
/******/ 					console.warn(
/******/ 						"[HMR] unexpected require(" +
/******/ 							request +
/******/ 							") from disposed module " +
/******/ 							moduleId
/******/ 					);
/******/ 					currentParents = [];
/******/ 				}
/******/ 				return require(request);
/******/ 			};
/******/ 			var createPropertyDescriptor = function (name) {
/******/ 				return {
/******/ 					configurable: true,
/******/ 					enumerable: true,
/******/ 					get: function () {
/******/ 						return require[name];
/******/ 					},
/******/ 					set: function (value) {
/******/ 						require[name] = value;
/******/ 					}
/******/ 				};
/******/ 			};
/******/ 			for (var name in require) {
/******/ 				if (Object.prototype.hasOwnProperty.call(require, name) && name !== "e") {
/******/ 					Object.defineProperty(fn, name, createPropertyDescriptor(name));
/******/ 				}
/******/ 			}
/******/ 			fn.e = function (chunkId) {
/******/ 				return trackBlockingPromise(require.e(chunkId));
/******/ 			};
/******/ 			return fn;
/******/ 		}
/******/ 		
/******/ 		function createModuleHotObject(moduleId, me) {
/******/ 			var _main = currentChildModule !== moduleId;
/******/ 			var hot = {
/******/ 				// private stuff
/******/ 				_acceptedDependencies: {},
/******/ 				_acceptedErrorHandlers: {},
/******/ 				_declinedDependencies: {},
/******/ 				_selfAccepted: false,
/******/ 				_selfDeclined: false,
/******/ 				_selfInvalidated: false,
/******/ 				_disposeHandlers: [],
/******/ 				_main: _main,
/******/ 				_requireSelf: function () {
/******/ 					currentParents = me.parents.slice();
/******/ 					currentChildModule = _main ? undefined : moduleId;
/******/ 					__webpack_require__(moduleId);
/******/ 				},
/******/ 		
/******/ 				// Module API
/******/ 				active: true,
/******/ 				accept: function (dep, callback, errorHandler) {
/******/ 					if (dep === undefined) hot._selfAccepted = true;
/******/ 					else if (typeof dep === "function") hot._selfAccepted = dep;
/******/ 					else if (typeof dep === "object" && dep !== null) {
/******/ 						for (var i = 0; i < dep.length; i++) {
/******/ 							hot._acceptedDependencies[dep[i]] = callback || function () {};
/******/ 							hot._acceptedErrorHandlers[dep[i]] = errorHandler;
/******/ 						}
/******/ 					} else {
/******/ 						hot._acceptedDependencies[dep] = callback || function () {};
/******/ 						hot._acceptedErrorHandlers[dep] = errorHandler;
/******/ 					}
/******/ 				},
/******/ 				decline: function (dep) {
/******/ 					if (dep === undefined) hot._selfDeclined = true;
/******/ 					else if (typeof dep === "object" && dep !== null)
/******/ 						for (var i = 0; i < dep.length; i++)
/******/ 							hot._declinedDependencies[dep[i]] = true;
/******/ 					else hot._declinedDependencies[dep] = true;
/******/ 				},
/******/ 				dispose: function (callback) {
/******/ 					hot._disposeHandlers.push(callback);
/******/ 				},
/******/ 				addDisposeHandler: function (callback) {
/******/ 					hot._disposeHandlers.push(callback);
/******/ 				},
/******/ 				removeDisposeHandler: function (callback) {
/******/ 					var idx = hot._disposeHandlers.indexOf(callback);
/******/ 					if (idx >= 0) hot._disposeHandlers.splice(idx, 1);
/******/ 				},
/******/ 				invalidate: function () {
/******/ 					this._selfInvalidated = true;
/******/ 					switch (currentStatus) {
/******/ 						case "idle":
/******/ 							currentUpdateApplyHandlers = [];
/******/ 							Object.keys(__webpack_require__.hmrI).forEach(function (key) {
/******/ 								__webpack_require__.hmrI[key](
/******/ 									moduleId,
/******/ 									currentUpdateApplyHandlers
/******/ 								);
/******/ 							});
/******/ 							setStatus("ready");
/******/ 							break;
/******/ 						case "ready":
/******/ 							Object.keys(__webpack_require__.hmrI).forEach(function (key) {
/******/ 								__webpack_require__.hmrI[key](
/******/ 									moduleId,
/******/ 									currentUpdateApplyHandlers
/******/ 								);
/******/ 							});
/******/ 							break;
/******/ 						case "prepare":
/******/ 						case "check":
/******/ 						case "dispose":
/******/ 						case "apply":
/******/ 							(queuedInvalidatedModules = queuedInvalidatedModules || []).push(
/******/ 								moduleId
/******/ 							);
/******/ 							break;
/******/ 						default:
/******/ 							// ignore requests in error states
/******/ 							break;
/******/ 					}
/******/ 				},
/******/ 		
/******/ 				// Management API
/******/ 				check: hotCheck,
/******/ 				apply: hotApply,
/******/ 				status: function (l) {
/******/ 					if (!l) return currentStatus;
/******/ 					registeredStatusHandlers.push(l);
/******/ 				},
/******/ 				addStatusHandler: function (l) {
/******/ 					registeredStatusHandlers.push(l);
/******/ 				},
/******/ 				removeStatusHandler: function (l) {
/******/ 					var idx = registeredStatusHandlers.indexOf(l);
/******/ 					if (idx >= 0) registeredStatusHandlers.splice(idx, 1);
/******/ 				},
/******/ 		
/******/ 				//inherit from previous dispose call
/******/ 				data: currentModuleData[moduleId]
/******/ 			};
/******/ 			currentChildModule = undefined;
/******/ 			return hot;
/******/ 		}
/******/ 		
/******/ 		function setStatus(newStatus) {
/******/ 			currentStatus = newStatus;
/******/ 			var results = [];
/******/ 		
/******/ 			for (var i = 0; i < registeredStatusHandlers.length; i++)
/******/ 				results[i] = registeredStatusHandlers[i].call(null, newStatus);
/******/ 		
/******/ 			return Promise.all(results);
/******/ 		}
/******/ 		
/******/ 		function unblock() {
/******/ 			if (--blockingPromises === 0) {
/******/ 				setStatus("ready").then(function () {
/******/ 					if (blockingPromises === 0) {
/******/ 						var list = blockingPromisesWaiting;
/******/ 						blockingPromisesWaiting = [];
/******/ 						for (var i = 0; i < list.length; i++) {
/******/ 							list[i]();
/******/ 						}
/******/ 					}
/******/ 				});
/******/ 			}
/******/ 		}
/******/ 		
/******/ 		function trackBlockingPromise(promise) {
/******/ 			switch (currentStatus) {
/******/ 				case "ready":
/******/ 					setStatus("prepare");
/******/ 				/* fallthrough */
/******/ 				case "prepare":
/******/ 					blockingPromises++;
/******/ 					promise.then(unblock, unblock);
/******/ 					return promise;
/******/ 				default:
/******/ 					return promise;
/******/ 			}
/******/ 		}
/******/ 		
/******/ 		function waitForBlockingPromises(fn) {
/******/ 			if (blockingPromises === 0) return fn();
/******/ 			return new Promise(function (resolve) {
/******/ 				blockingPromisesWaiting.push(function () {
/******/ 					resolve(fn());
/******/ 				});
/******/ 			});
/******/ 		}
/******/ 		
/******/ 		function hotCheck(applyOnUpdate) {
/******/ 			if (currentStatus !== "idle") {
/******/ 				throw new Error("check() is only allowed in idle status");
/******/ 			}
/******/ 			return setStatus("check")
/******/ 				.then(__webpack_require__.hmrM)
/******/ 				.then(function (update) {
/******/ 					if (!update) {
/******/ 						return setStatus(applyInvalidatedModules() ? "ready" : "idle").then(
/******/ 							function () {
/******/ 								return null;
/******/ 							}
/******/ 						);
/******/ 					}
/******/ 		
/******/ 					return setStatus("prepare").then(function () {
/******/ 						var updatedModules = [];
/******/ 						currentUpdateApplyHandlers = [];
/******/ 		
/******/ 						return Promise.all(
/******/ 							Object.keys(__webpack_require__.hmrC).reduce(function (
/******/ 								promises,
/******/ 								key
/******/ 							) {
/******/ 								__webpack_require__.hmrC[key](
/******/ 									update.c,
/******/ 									update.r,
/******/ 									update.m,
/******/ 									promises,
/******/ 									currentUpdateApplyHandlers,
/******/ 									updatedModules
/******/ 								);
/******/ 								return promises;
/******/ 							},
/******/ 							[])
/******/ 						).then(function () {
/******/ 							return waitForBlockingPromises(function () {
/******/ 								if (applyOnUpdate) {
/******/ 									return internalApply(applyOnUpdate);
/******/ 								} else {
/******/ 									return setStatus("ready").then(function () {
/******/ 										return updatedModules;
/******/ 									});
/******/ 								}
/******/ 							});
/******/ 						});
/******/ 					});
/******/ 				});
/******/ 		}
/******/ 		
/******/ 		function hotApply(options) {
/******/ 			if (currentStatus !== "ready") {
/******/ 				return Promise.resolve().then(function () {
/******/ 					throw new Error(
/******/ 						"apply() is only allowed in ready status (state: " +
/******/ 							currentStatus +
/******/ 							")"
/******/ 					);
/******/ 				});
/******/ 			}
/******/ 			return internalApply(options);
/******/ 		}
/******/ 		
/******/ 		function internalApply(options) {
/******/ 			options = options || {};
/******/ 		
/******/ 			applyInvalidatedModules();
/******/ 		
/******/ 			var results = currentUpdateApplyHandlers.map(function (handler) {
/******/ 				return handler(options);
/******/ 			});
/******/ 			currentUpdateApplyHandlers = undefined;
/******/ 		
/******/ 			var errors = results
/******/ 				.map(function (r) {
/******/ 					return r.error;
/******/ 				})
/******/ 				.filter(Boolean);
/******/ 		
/******/ 			if (errors.length > 0) {
/******/ 				return setStatus("abort").then(function () {
/******/ 					throw errors[0];
/******/ 				});
/******/ 			}
/******/ 		
/******/ 			// Now in "dispose" phase
/******/ 			var disposePromise = setStatus("dispose");
/******/ 		
/******/ 			results.forEach(function (result) {
/******/ 				if (result.dispose) result.dispose();
/******/ 			});
/******/ 		
/******/ 			// Now in "apply" phase
/******/ 			var applyPromise = setStatus("apply");
/******/ 		
/******/ 			var error;
/******/ 			var reportError = function (err) {
/******/ 				if (!error) error = err;
/******/ 			};
/******/ 		
/******/ 			var outdatedModules = [];
/******/ 			results.forEach(function (result) {
/******/ 				if (result.apply) {
/******/ 					var modules = result.apply(reportError);
/******/ 					if (modules) {
/******/ 						for (var i = 0; i < modules.length; i++) {
/******/ 							outdatedModules.push(modules[i]);
/******/ 						}
/******/ 					}
/******/ 				}
/******/ 			});
/******/ 		
/******/ 			return Promise.all([disposePromise, applyPromise]).then(function () {
/******/ 				// handle errors in accept handlers and self accepted module load
/******/ 				if (error) {
/******/ 					return setStatus("fail").then(function () {
/******/ 						throw error;
/******/ 					});
/******/ 				}
/******/ 		
/******/ 				if (queuedInvalidatedModules) {
/******/ 					return internalApply(options).then(function (list) {
/******/ 						outdatedModules.forEach(function (moduleId) {
/******/ 							if (list.indexOf(moduleId) < 0) list.push(moduleId);
/******/ 						});
/******/ 						return list;
/******/ 					});
/******/ 				}
/******/ 		
/******/ 				return setStatus("idle").then(function () {
/******/ 					return outdatedModules;
/******/ 				});
/******/ 			});
/******/ 		}
/******/ 		
/******/ 		function applyInvalidatedModules() {
/******/ 			if (queuedInvalidatedModules) {
/******/ 				if (!currentUpdateApplyHandlers) currentUpdateApplyHandlers = [];
/******/ 				Object.keys(__webpack_require__.hmrI).forEach(function (key) {
/******/ 					queuedInvalidatedModules.forEach(function (moduleId) {
/******/ 						__webpack_require__.hmrI[key](
/******/ 							moduleId,
/******/ 							currentUpdateApplyHandlers
/******/ 						);
/******/ 					});
/******/ 				});
/******/ 				queuedInvalidatedModules = undefined;
/******/ 				return true;
/******/ 			}
/******/ 		}
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/publicPath */
/******/ 	(() => {
/******/ 		var scriptUrl;
/******/ 		if (__webpack_require__.g.importScripts) scriptUrl = __webpack_require__.g.location + "";
/******/ 		var document = __webpack_require__.g.document;
/******/ 		if (!scriptUrl && document) {
/******/ 			if (document.currentScript)
/******/ 				scriptUrl = document.currentScript.src;
/******/ 			if (!scriptUrl) {
/******/ 				var scripts = document.getElementsByTagName("script");
/******/ 				if(scripts.length) {
/******/ 					var i = scripts.length - 1;
/******/ 					while (i > -1 && !scriptUrl) scriptUrl = scripts[i--].src;
/******/ 				}
/******/ 			}
/******/ 		}
/******/ 		// When supporting browsers where an automatic publicPath is not supported you must specify an output.publicPath manually via configuration
/******/ 		// or pass an empty string ("") and set the __webpack_public_path__ variable from your code to use your own logic.
/******/ 		if (!scriptUrl) throw new Error("Automatic publicPath is not supported in this browser");
/******/ 		scriptUrl = scriptUrl.replace(/#.*$/, "").replace(/\?.*$/, "").replace(/\/[^\/]+$/, "/");
/******/ 		__webpack_require__.p = scriptUrl;
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/css loading */
/******/ 	(() => {
/******/ 		var createStylesheet = (chunkId, fullhref, resolve, reject) => {
/******/ 			var linkTag = document.createElement("link");
/******/ 		
/******/ 			linkTag.rel = "stylesheet";
/******/ 			linkTag.type = "text/css";
/******/ 			var onLinkComplete = (event) => {
/******/ 				// avoid mem leaks.
/******/ 				linkTag.onerror = linkTag.onload = null;
/******/ 				if (event.type === 'load') {
/******/ 					resolve();
/******/ 				} else {
/******/ 					var errorType = event && (event.type === 'load' ? 'missing' : event.type);
/******/ 					var realHref = event && event.target && event.target.href || fullhref;
/******/ 					var err = new Error("Loading CSS chunk " + chunkId + " failed.\n(" + realHref + ")");
/******/ 					err.code = "CSS_CHUNK_LOAD_FAILED";
/******/ 					err.type = errorType;
/******/ 					err.request = realHref;
/******/ 					linkTag.parentNode.removeChild(linkTag)
/******/ 					reject(err);
/******/ 				}
/******/ 			}
/******/ 			linkTag.onerror = linkTag.onload = onLinkComplete;
/******/ 			linkTag.href = fullhref;
/******/ 		
/******/ 			document.head.appendChild(linkTag);
/******/ 			return linkTag;
/******/ 		};
/******/ 		var findStylesheet = (href, fullhref) => {
/******/ 			var existingLinkTags = document.getElementsByTagName("link");
/******/ 			for(var i = 0; i < existingLinkTags.length; i++) {
/******/ 				var tag = existingLinkTags[i];
/******/ 				var dataHref = tag.getAttribute("data-href") || tag.getAttribute("href");
/******/ 				if(tag.rel === "stylesheet" && (dataHref === href || dataHref === fullhref)) return tag;
/******/ 			}
/******/ 			var existingStyleTags = document.getElementsByTagName("style");
/******/ 			for(var i = 0; i < existingStyleTags.length; i++) {
/******/ 				var tag = existingStyleTags[i];
/******/ 				var dataHref = tag.getAttribute("data-href");
/******/ 				if(dataHref === href || dataHref === fullhref) return tag;
/******/ 			}
/******/ 		};
/******/ 		var loadStylesheet = (chunkId) => {
/******/ 			return new Promise((resolve, reject) => {
/******/ 				var href = __webpack_require__.miniCssF(chunkId);
/******/ 				var fullhref = __webpack_require__.p + href;
/******/ 				if(findStylesheet(href, fullhref)) return resolve();
/******/ 				createStylesheet(chunkId, fullhref, resolve, reject);
/******/ 			});
/******/ 		}
/******/ 		// no chunk loading
/******/ 		
/******/ 		var oldTags = [];
/******/ 		var newTags = [];
/******/ 		var applyHandler = (options) => {
/******/ 			return { dispose: () => {
/******/ 				for(var i = 0; i < oldTags.length; i++) {
/******/ 					var oldTag = oldTags[i];
/******/ 					if(oldTag.parentNode) oldTag.parentNode.removeChild(oldTag);
/******/ 				}
/******/ 				oldTags.length = 0;
/******/ 			}, apply: () => {
/******/ 				for(var i = 0; i < newTags.length; i++) newTags[i].rel = "stylesheet";
/******/ 				newTags.length = 0;
/******/ 			} };
/******/ 		}
/******/ 		__webpack_require__.hmrC.miniCss = (chunkIds, removedChunks, removedModules, promises, applyHandlers, updatedModulesList) => {
/******/ 			applyHandlers.push(applyHandler);
/******/ 			chunkIds.forEach((chunkId) => {
/******/ 				var href = __webpack_require__.miniCssF(chunkId);
/******/ 				var fullhref = __webpack_require__.p + href;
/******/ 				var oldTag = findStylesheet(href, fullhref);
/******/ 				if(!oldTag) return;
/******/ 				promises.push(new Promise((resolve, reject) => {
/******/ 					var tag = createStylesheet(chunkId, fullhref, () => {
/******/ 						tag.as = "style";
/******/ 						tag.rel = "preload";
/******/ 						resolve();
/******/ 					}, reject);
/******/ 					oldTags.push(oldTag);
/******/ 					newTags.push(tag);
/******/ 				}));
/******/ 			});
/******/ 		}
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/jsonp chunk loading */
/******/ 	(() => {
/******/ 		// no baseURI
/******/ 		
/******/ 		// object to store loaded and loading chunks
/******/ 		// undefined = chunk not loaded, null = chunk preloaded/prefetched
/******/ 		// [resolve, reject, Promise] = chunk loading, 0 = chunk loaded
/******/ 		var installedChunks = __webpack_require__.hmrS_jsonp = __webpack_require__.hmrS_jsonp || {
/******/ 			"openassessment-editor-tinymce": 0
/******/ 		};
/******/ 		
/******/ 		// no chunk on demand loading
/******/ 		
/******/ 		// no prefetching
/******/ 		
/******/ 		// no preloaded
/******/ 		
/******/ 		var currentUpdatedModulesList;
/******/ 		var waitingUpdateResolves = {};
/******/ 		function loadUpdateChunk(chunkId, updatedModulesList) {
/******/ 			currentUpdatedModulesList = updatedModulesList;
/******/ 			return new Promise((resolve, reject) => {
/******/ 				waitingUpdateResolves[chunkId] = resolve;
/******/ 				// start update chunk loading
/******/ 				var url = __webpack_require__.p + __webpack_require__.hu(chunkId);
/******/ 				// create error before stack unwound to get useful stacktrace later
/******/ 				var error = new Error();
/******/ 				var loadingEnded = (event) => {
/******/ 					if(waitingUpdateResolves[chunkId]) {
/******/ 						waitingUpdateResolves[chunkId] = undefined
/******/ 						var errorType = event && (event.type === 'load' ? 'missing' : event.type);
/******/ 						var realSrc = event && event.target && event.target.src;
/******/ 						error.message = 'Loading hot update chunk ' + chunkId + ' failed.\n(' + errorType + ': ' + realSrc + ')';
/******/ 						error.name = 'ChunkLoadError';
/******/ 						error.type = errorType;
/******/ 						error.request = realSrc;
/******/ 						reject(error);
/******/ 					}
/******/ 				};
/******/ 				__webpack_require__.l(url, loadingEnded);
/******/ 			});
/******/ 		}
/******/ 		
/******/ 		self["webpackHotUpdateedx_ora2"] = (chunkId, moreModules, runtime) => {
/******/ 			for(var moduleId in moreModules) {
/******/ 				if(__webpack_require__.o(moreModules, moduleId)) {
/******/ 					currentUpdate[moduleId] = moreModules[moduleId];
/******/ 					if(currentUpdatedModulesList) currentUpdatedModulesList.push(moduleId);
/******/ 				}
/******/ 			}
/******/ 			if(runtime) currentUpdateRuntime.push(runtime);
/******/ 			if(waitingUpdateResolves[chunkId]) {
/******/ 				waitingUpdateResolves[chunkId]();
/******/ 				waitingUpdateResolves[chunkId] = undefined;
/******/ 			}
/******/ 		};
/******/ 		
/******/ 		var currentUpdateChunks;
/******/ 		var currentUpdate;
/******/ 		var currentUpdateRemovedChunks;
/******/ 		var currentUpdateRuntime;
/******/ 		function applyHandler(options) {
/******/ 			if (__webpack_require__.f) delete __webpack_require__.f.jsonpHmr;
/******/ 			currentUpdateChunks = undefined;
/******/ 			function getAffectedModuleEffects(updateModuleId) {
/******/ 				var outdatedModules = [updateModuleId];
/******/ 				var outdatedDependencies = {};
/******/ 		
/******/ 				var queue = outdatedModules.map(function (id) {
/******/ 					return {
/******/ 						chain: [id],
/******/ 						id: id
/******/ 					};
/******/ 				});
/******/ 				while (queue.length > 0) {
/******/ 					var queueItem = queue.pop();
/******/ 					var moduleId = queueItem.id;
/******/ 					var chain = queueItem.chain;
/******/ 					var module = __webpack_require__.c[moduleId];
/******/ 					if (
/******/ 						!module ||
/******/ 						(module.hot._selfAccepted && !module.hot._selfInvalidated)
/******/ 					)
/******/ 						continue;
/******/ 					if (module.hot._selfDeclined) {
/******/ 						return {
/******/ 							type: "self-declined",
/******/ 							chain: chain,
/******/ 							moduleId: moduleId
/******/ 						};
/******/ 					}
/******/ 					if (module.hot._main) {
/******/ 						return {
/******/ 							type: "unaccepted",
/******/ 							chain: chain,
/******/ 							moduleId: moduleId
/******/ 						};
/******/ 					}
/******/ 					for (var i = 0; i < module.parents.length; i++) {
/******/ 						var parentId = module.parents[i];
/******/ 						var parent = __webpack_require__.c[parentId];
/******/ 						if (!parent) continue;
/******/ 						if (parent.hot._declinedDependencies[moduleId]) {
/******/ 							return {
/******/ 								type: "declined",
/******/ 								chain: chain.concat([parentId]),
/******/ 								moduleId: moduleId,
/******/ 								parentId: parentId
/******/ 							};
/******/ 						}
/******/ 						if (outdatedModules.indexOf(parentId) !== -1) continue;
/******/ 						if (parent.hot._acceptedDependencies[moduleId]) {
/******/ 							if (!outdatedDependencies[parentId])
/******/ 								outdatedDependencies[parentId] = [];
/******/ 							addAllToSet(outdatedDependencies[parentId], [moduleId]);
/******/ 							continue;
/******/ 						}
/******/ 						delete outdatedDependencies[parentId];
/******/ 						outdatedModules.push(parentId);
/******/ 						queue.push({
/******/ 							chain: chain.concat([parentId]),
/******/ 							id: parentId
/******/ 						});
/******/ 					}
/******/ 				}
/******/ 		
/******/ 				return {
/******/ 					type: "accepted",
/******/ 					moduleId: updateModuleId,
/******/ 					outdatedModules: outdatedModules,
/******/ 					outdatedDependencies: outdatedDependencies
/******/ 				};
/******/ 			}
/******/ 		
/******/ 			function addAllToSet(a, b) {
/******/ 				for (var i = 0; i < b.length; i++) {
/******/ 					var item = b[i];
/******/ 					if (a.indexOf(item) === -1) a.push(item);
/******/ 				}
/******/ 			}
/******/ 		
/******/ 			// at begin all updates modules are outdated
/******/ 			// the "outdated" status can propagate to parents if they don't accept the children
/******/ 			var outdatedDependencies = {};
/******/ 			var outdatedModules = [];
/******/ 			var appliedUpdate = {};
/******/ 		
/******/ 			var warnUnexpectedRequire = function warnUnexpectedRequire(module) {
/******/ 				console.warn(
/******/ 					"[HMR] unexpected require(" + module.id + ") to disposed module"
/******/ 				);
/******/ 			};
/******/ 		
/******/ 			for (var moduleId in currentUpdate) {
/******/ 				if (__webpack_require__.o(currentUpdate, moduleId)) {
/******/ 					var newModuleFactory = currentUpdate[moduleId];
/******/ 					/** @type {TODO} */
/******/ 					var result;
/******/ 					if (newModuleFactory) {
/******/ 						result = getAffectedModuleEffects(moduleId);
/******/ 					} else {
/******/ 						result = {
/******/ 							type: "disposed",
/******/ 							moduleId: moduleId
/******/ 						};
/******/ 					}
/******/ 					/** @type {Error|false} */
/******/ 					var abortError = false;
/******/ 					var doApply = false;
/******/ 					var doDispose = false;
/******/ 					var chainInfo = "";
/******/ 					if (result.chain) {
/******/ 						chainInfo = "\nUpdate propagation: " + result.chain.join(" -> ");
/******/ 					}
/******/ 					switch (result.type) {
/******/ 						case "self-declined":
/******/ 							if (options.onDeclined) options.onDeclined(result);
/******/ 							if (!options.ignoreDeclined)
/******/ 								abortError = new Error(
/******/ 									"Aborted because of self decline: " +
/******/ 										result.moduleId +
/******/ 										chainInfo
/******/ 								);
/******/ 							break;
/******/ 						case "declined":
/******/ 							if (options.onDeclined) options.onDeclined(result);
/******/ 							if (!options.ignoreDeclined)
/******/ 								abortError = new Error(
/******/ 									"Aborted because of declined dependency: " +
/******/ 										result.moduleId +
/******/ 										" in " +
/******/ 										result.parentId +
/******/ 										chainInfo
/******/ 								);
/******/ 							break;
/******/ 						case "unaccepted":
/******/ 							if (options.onUnaccepted) options.onUnaccepted(result);
/******/ 							if (!options.ignoreUnaccepted)
/******/ 								abortError = new Error(
/******/ 									"Aborted because " + moduleId + " is not accepted" + chainInfo
/******/ 								);
/******/ 							break;
/******/ 						case "accepted":
/******/ 							if (options.onAccepted) options.onAccepted(result);
/******/ 							doApply = true;
/******/ 							break;
/******/ 						case "disposed":
/******/ 							if (options.onDisposed) options.onDisposed(result);
/******/ 							doDispose = true;
/******/ 							break;
/******/ 						default:
/******/ 							throw new Error("Unexception type " + result.type);
/******/ 					}
/******/ 					if (abortError) {
/******/ 						return {
/******/ 							error: abortError
/******/ 						};
/******/ 					}
/******/ 					if (doApply) {
/******/ 						appliedUpdate[moduleId] = newModuleFactory;
/******/ 						addAllToSet(outdatedModules, result.outdatedModules);
/******/ 						for (moduleId in result.outdatedDependencies) {
/******/ 							if (__webpack_require__.o(result.outdatedDependencies, moduleId)) {
/******/ 								if (!outdatedDependencies[moduleId])
/******/ 									outdatedDependencies[moduleId] = [];
/******/ 								addAllToSet(
/******/ 									outdatedDependencies[moduleId],
/******/ 									result.outdatedDependencies[moduleId]
/******/ 								);
/******/ 							}
/******/ 						}
/******/ 					}
/******/ 					if (doDispose) {
/******/ 						addAllToSet(outdatedModules, [result.moduleId]);
/******/ 						appliedUpdate[moduleId] = warnUnexpectedRequire;
/******/ 					}
/******/ 				}
/******/ 			}
/******/ 			currentUpdate = undefined;
/******/ 		
/******/ 			// Store self accepted outdated modules to require them later by the module system
/******/ 			var outdatedSelfAcceptedModules = [];
/******/ 			for (var j = 0; j < outdatedModules.length; j++) {
/******/ 				var outdatedModuleId = outdatedModules[j];
/******/ 				var module = __webpack_require__.c[outdatedModuleId];
/******/ 				if (
/******/ 					module &&
/******/ 					(module.hot._selfAccepted || module.hot._main) &&
/******/ 					// removed self-accepted modules should not be required
/******/ 					appliedUpdate[outdatedModuleId] !== warnUnexpectedRequire &&
/******/ 					// when called invalidate self-accepting is not possible
/******/ 					!module.hot._selfInvalidated
/******/ 				) {
/******/ 					outdatedSelfAcceptedModules.push({
/******/ 						module: outdatedModuleId,
/******/ 						require: module.hot._requireSelf,
/******/ 						errorHandler: module.hot._selfAccepted
/******/ 					});
/******/ 				}
/******/ 			}
/******/ 		
/******/ 			var moduleOutdatedDependencies;
/******/ 		
/******/ 			return {
/******/ 				dispose: function () {
/******/ 					currentUpdateRemovedChunks.forEach(function (chunkId) {
/******/ 						delete installedChunks[chunkId];
/******/ 					});
/******/ 					currentUpdateRemovedChunks = undefined;
/******/ 		
/******/ 					var idx;
/******/ 					var queue = outdatedModules.slice();
/******/ 					while (queue.length > 0) {
/******/ 						var moduleId = queue.pop();
/******/ 						var module = __webpack_require__.c[moduleId];
/******/ 						if (!module) continue;
/******/ 		
/******/ 						var data = {};
/******/ 		
/******/ 						// Call dispose handlers
/******/ 						var disposeHandlers = module.hot._disposeHandlers;
/******/ 						for (j = 0; j < disposeHandlers.length; j++) {
/******/ 							disposeHandlers[j].call(null, data);
/******/ 						}
/******/ 						__webpack_require__.hmrD[moduleId] = data;
/******/ 		
/******/ 						// disable module (this disables requires from this module)
/******/ 						module.hot.active = false;
/******/ 		
/******/ 						// remove module from cache
/******/ 						delete __webpack_require__.c[moduleId];
/******/ 		
/******/ 						// when disposing there is no need to call dispose handler
/******/ 						delete outdatedDependencies[moduleId];
/******/ 		
/******/ 						// remove "parents" references from all children
/******/ 						for (j = 0; j < module.children.length; j++) {
/******/ 							var child = __webpack_require__.c[module.children[j]];
/******/ 							if (!child) continue;
/******/ 							idx = child.parents.indexOf(moduleId);
/******/ 							if (idx >= 0) {
/******/ 								child.parents.splice(idx, 1);
/******/ 							}
/******/ 						}
/******/ 					}
/******/ 		
/******/ 					// remove outdated dependency from module children
/******/ 					var dependency;
/******/ 					for (var outdatedModuleId in outdatedDependencies) {
/******/ 						if (__webpack_require__.o(outdatedDependencies, outdatedModuleId)) {
/******/ 							module = __webpack_require__.c[outdatedModuleId];
/******/ 							if (module) {
/******/ 								moduleOutdatedDependencies =
/******/ 									outdatedDependencies[outdatedModuleId];
/******/ 								for (j = 0; j < moduleOutdatedDependencies.length; j++) {
/******/ 									dependency = moduleOutdatedDependencies[j];
/******/ 									idx = module.children.indexOf(dependency);
/******/ 									if (idx >= 0) module.children.splice(idx, 1);
/******/ 								}
/******/ 							}
/******/ 						}
/******/ 					}
/******/ 				},
/******/ 				apply: function (reportError) {
/******/ 					// insert new code
/******/ 					for (var updateModuleId in appliedUpdate) {
/******/ 						if (__webpack_require__.o(appliedUpdate, updateModuleId)) {
/******/ 							__webpack_require__.m[updateModuleId] = appliedUpdate[updateModuleId];
/******/ 						}
/******/ 					}
/******/ 		
/******/ 					// run new runtime modules
/******/ 					for (var i = 0; i < currentUpdateRuntime.length; i++) {
/******/ 						currentUpdateRuntime[i](__webpack_require__);
/******/ 					}
/******/ 		
/******/ 					// call accept handlers
/******/ 					for (var outdatedModuleId in outdatedDependencies) {
/******/ 						if (__webpack_require__.o(outdatedDependencies, outdatedModuleId)) {
/******/ 							var module = __webpack_require__.c[outdatedModuleId];
/******/ 							if (module) {
/******/ 								moduleOutdatedDependencies =
/******/ 									outdatedDependencies[outdatedModuleId];
/******/ 								var callbacks = [];
/******/ 								var errorHandlers = [];
/******/ 								var dependenciesForCallbacks = [];
/******/ 								for (var j = 0; j < moduleOutdatedDependencies.length; j++) {
/******/ 									var dependency = moduleOutdatedDependencies[j];
/******/ 									var acceptCallback =
/******/ 										module.hot._acceptedDependencies[dependency];
/******/ 									var errorHandler =
/******/ 										module.hot._acceptedErrorHandlers[dependency];
/******/ 									if (acceptCallback) {
/******/ 										if (callbacks.indexOf(acceptCallback) !== -1) continue;
/******/ 										callbacks.push(acceptCallback);
/******/ 										errorHandlers.push(errorHandler);
/******/ 										dependenciesForCallbacks.push(dependency);
/******/ 									}
/******/ 								}
/******/ 								for (var k = 0; k < callbacks.length; k++) {
/******/ 									try {
/******/ 										callbacks[k].call(null, moduleOutdatedDependencies);
/******/ 									} catch (err) {
/******/ 										if (typeof errorHandlers[k] === "function") {
/******/ 											try {
/******/ 												errorHandlers[k](err, {
/******/ 													moduleId: outdatedModuleId,
/******/ 													dependencyId: dependenciesForCallbacks[k]
/******/ 												});
/******/ 											} catch (err2) {
/******/ 												if (options.onErrored) {
/******/ 													options.onErrored({
/******/ 														type: "accept-error-handler-errored",
/******/ 														moduleId: outdatedModuleId,
/******/ 														dependencyId: dependenciesForCallbacks[k],
/******/ 														error: err2,
/******/ 														originalError: err
/******/ 													});
/******/ 												}
/******/ 												if (!options.ignoreErrored) {
/******/ 													reportError(err2);
/******/ 													reportError(err);
/******/ 												}
/******/ 											}
/******/ 										} else {
/******/ 											if (options.onErrored) {
/******/ 												options.onErrored({
/******/ 													type: "accept-errored",
/******/ 													moduleId: outdatedModuleId,
/******/ 													dependencyId: dependenciesForCallbacks[k],
/******/ 													error: err
/******/ 												});
/******/ 											}
/******/ 											if (!options.ignoreErrored) {
/******/ 												reportError(err);
/******/ 											}
/******/ 										}
/******/ 									}
/******/ 								}
/******/ 							}
/******/ 						}
/******/ 					}
/******/ 		
/******/ 					// Load self accepted modules
/******/ 					for (var o = 0; o < outdatedSelfAcceptedModules.length; o++) {
/******/ 						var item = outdatedSelfAcceptedModules[o];
/******/ 						var moduleId = item.module;
/******/ 						try {
/******/ 							item.require(moduleId);
/******/ 						} catch (err) {
/******/ 							if (typeof item.errorHandler === "function") {
/******/ 								try {
/******/ 									item.errorHandler(err, {
/******/ 										moduleId: moduleId,
/******/ 										module: __webpack_require__.c[moduleId]
/******/ 									});
/******/ 								} catch (err2) {
/******/ 									if (options.onErrored) {
/******/ 										options.onErrored({
/******/ 											type: "self-accept-error-handler-errored",
/******/ 											moduleId: moduleId,
/******/ 											error: err2,
/******/ 											originalError: err
/******/ 										});
/******/ 									}
/******/ 									if (!options.ignoreErrored) {
/******/ 										reportError(err2);
/******/ 										reportError(err);
/******/ 									}
/******/ 								}
/******/ 							} else {
/******/ 								if (options.onErrored) {
/******/ 									options.onErrored({
/******/ 										type: "self-accept-errored",
/******/ 										moduleId: moduleId,
/******/ 										error: err
/******/ 									});
/******/ 								}
/******/ 								if (!options.ignoreErrored) {
/******/ 									reportError(err);
/******/ 								}
/******/ 							}
/******/ 						}
/******/ 					}
/******/ 		
/******/ 					return outdatedModules;
/******/ 				}
/******/ 			};
/******/ 		}
/******/ 		__webpack_require__.hmrI.jsonp = function (moduleId, applyHandlers) {
/******/ 			if (!currentUpdate) {
/******/ 				currentUpdate = {};
/******/ 				currentUpdateRuntime = [];
/******/ 				currentUpdateRemovedChunks = [];
/******/ 				applyHandlers.push(applyHandler);
/******/ 			}
/******/ 			if (!__webpack_require__.o(currentUpdate, moduleId)) {
/******/ 				currentUpdate[moduleId] = __webpack_require__.m[moduleId];
/******/ 			}
/******/ 		};
/******/ 		__webpack_require__.hmrC.jsonp = function (
/******/ 			chunkIds,
/******/ 			removedChunks,
/******/ 			removedModules,
/******/ 			promises,
/******/ 			applyHandlers,
/******/ 			updatedModulesList
/******/ 		) {
/******/ 			applyHandlers.push(applyHandler);
/******/ 			currentUpdateChunks = {};
/******/ 			currentUpdateRemovedChunks = removedChunks;
/******/ 			currentUpdate = removedModules.reduce(function (obj, key) {
/******/ 				obj[key] = false;
/******/ 				return obj;
/******/ 			}, {});
/******/ 			currentUpdateRuntime = [];
/******/ 			chunkIds.forEach(function (chunkId) {
/******/ 				if (
/******/ 					__webpack_require__.o(installedChunks, chunkId) &&
/******/ 					installedChunks[chunkId] !== undefined
/******/ 				) {
/******/ 					promises.push(loadUpdateChunk(chunkId, updatedModulesList));
/******/ 					currentUpdateChunks[chunkId] = true;
/******/ 				} else {
/******/ 					currentUpdateChunks[chunkId] = false;
/******/ 				}
/******/ 			});
/******/ 			if (__webpack_require__.f) {
/******/ 				__webpack_require__.f.jsonpHmr = function (chunkId, promises) {
/******/ 					if (
/******/ 						currentUpdateChunks &&
/******/ 						__webpack_require__.o(currentUpdateChunks, chunkId) &&
/******/ 						!currentUpdateChunks[chunkId]
/******/ 					) {
/******/ 						promises.push(loadUpdateChunk(chunkId));
/******/ 						currentUpdateChunks[chunkId] = true;
/******/ 					}
/******/ 				};
/******/ 			}
/******/ 		};
/******/ 		
/******/ 		__webpack_require__.hmrM = () => {
/******/ 			if (typeof fetch === "undefined") throw new Error("No browser support: need fetch API");
/******/ 			return fetch(__webpack_require__.p + __webpack_require__.hmrF()).then((response) => {
/******/ 				if(response.status === 404) return; // no update available
/******/ 				if(!response.ok) throw new Error("Failed to fetch update manifest " + response.statusText);
/******/ 				return response.json();
/******/ 			});
/******/ 		};
/******/ 		
/******/ 		// no on chunks loaded
/******/ 		
/******/ 		// no jsonp function
/******/ 	})();
/******/ 	
/************************************************************************/
/******/ 	
/******/ 	// module cache are used so entry inlining is disabled
/******/ 	// startup
/******/ 	// Load entry module and return exports
/******/ 	var __webpack_exports__ = __webpack_require__("./openassessment/xblock/static/js/src/lms/editors/oa_editor_tinymce.js");
/******/ 	
/******/ })()
;