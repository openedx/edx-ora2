/**
 Handles Response Editor of tinymce type.
 * */

(function (define) {
  const dependencies = [];

  // Create a flag to determine if we are in lms
  const isLMS = typeof window.LmsRuntime !== 'undefined';

  // Determine which css file should be loaded to style text in the editor
  let baseUrl = '/static/studio/js/vendor/tinymce/js/tinymce/';
  if (isLMS) {
    baseUrl = '/static/js/vendor/tinymce/js/tinymce/';
  }

  if (typeof window.tinymce === 'undefined') {
    // If tinymce is not available, we need to load it
    dependencies.push('tinymce');
    dependencies.push('jquery.tinymce');
  }

  define(dependencies, () => {
    class EditorTinymce {
      editorInstances = [];

      /**
       Build and return TinyMCE Configuration.
       * */
      getTinyMCEConfig(readonly) {
        let config = {
          menubar: false,
          statusbar: false,
          base_url: baseUrl,
          theme: 'silver',
          skin: 'studio-tmce5',
          content_css: 'studio-tmce5',
          height: '300',
          schema: 'html5',
          plugins: 'code image link lists',
          toolbar: 'formatselect | bold italic underline | link blockquote image | numlist bullist outdent indent | strikethrough | code | undo redo',
        };

        // if readonly hide toolbar, menubar and statusbar
        if (readonly) {
          config = Object.assign(config, {
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

        return Promise.all(this.elements.map(function () {
          // check if it's readonly
          const disabled = $(this).attr('disabled');

          // In LMS with multiple Unit containing ORA Block with tinyMCE enabled,
          // We need to destroy if any previously intialized editor exists for current element.
          const id = $(this).attr('id');
          if (id !== undefined) {
            const existingEditor = tinymce.get(id); // eslint-disable-line
            if (existingEditor) {
              existingEditor.destroy();
            }
          }

          const config = ctrl.getTinyMCEConfig(disabled);
          return new Promise(resolve => {
            config.setup = editor => editor.on('init', () => {
              ctrl.editorInstances.push(editor);
              resolve();
            });
            $(this).tinymce(config);
          });
        }));
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
