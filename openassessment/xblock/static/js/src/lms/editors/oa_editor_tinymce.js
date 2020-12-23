/**
 Handles Response Editor of tinymce type.
 * */

(function (define) {
  define(['jquery.tinymce'], () => {
    class EditorTinymce {
      editorInstances = [];

      /**
       Build and return TinyMCE Configuration.
       * */
      getTinyMCEConfig(readonly) {
        let config = {
          setup: (ed) => {
            // keep editor instances for later use
            this.editorInstances.push(ed);
          },
        };

        // if readonly hide toolbar, menubar and statusbar
        if (readonly) {
          config = Object.assign(config, {
            menubar: false,
            statusbar: false,
            toolbar: false,
            readonly: 1,
          });
        }

        return config;
      }

      /**
       Loads TinyMCE editor.

       Args:
       elements (object): editor elements selected by jQuery
       * */
      load(elements) {
        this.elements = elements;

        // check if it's readonly
        const disabled = this.elements.attr('disabled');

        this.elements.tinymce(this.getTinyMCEConfig(disabled));
      }

      /**
       Set on change listener to the editor.

       Args:
       handler (Function)
       * */
      setOnChangeListener(handler) {
        ['change', 'keyup', 'drop', 'paste'].forEach(eventName => {
          this.editorInstances.forEach(editor => {
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
      response(texts) {
        if (typeof texts === 'undefined') {
          return this.elements.map(function () {
            return $.trim($(this).val());
          }).get();
        }
        this.elements.each(function (index) {
          $(this).val(texts[index]);
        });
      }
    }

    // return a function, to be able to create new instance every time.
    return function () {
      return new EditorTinymce();
    };
  });
}).call(window, window.define || window.RequireJS.define);
