/**
 Handles Response Editor of tinymce type.
 * */
import tinymce from 'tinymce/tinymce';
import 'tinymce/icons/default';
import 'tinymce/themes/silver';

// Tell tinymce from where it should load css, plugins etc
tinymce.baseURL = '/xblock/resource/openassessment/static/vendors/tinymce/';

(function (define) {
  define(() => {
    class EditorTinymce {
      editorInstances = [];

      /**
       Build and return TinyMCE Configuration.
       * */
      getTinyMCEConfig(readonly) {
        let config = {
          menubar: false,
          statusbar: false,
          plugins: 'codesample code image link lists',
          toolbar: 'formatselect | bold italic underline | link blockquote codesample image | numlist bullist outdent indent | strikethrough | code | undo redo',
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

        const ctrl = this;

        this.elements.each(function () {
          // check if it's readonly
          const disabled = $(this).attr('disabled');
          const config = ctrl.getTinyMCEConfig(disabled);

          tinymce.init({
            target: this,
            ...config,
          });
        });
        // this.elements.tinymce(this.getTinyMCEConfig(disabled));
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
          return this.editorInstances.map(editor => editor.getContent());
        }
        this.editorInstances.forEach((editor, index) => {
          editor.setContent(texts[index]);
        });
      }
    }

    // return a function, to be able to create new instance every time.
    return function () {
      return new EditorTinymce();
    };
  });
}).call(window, window.define || window.RequireJS.define);
