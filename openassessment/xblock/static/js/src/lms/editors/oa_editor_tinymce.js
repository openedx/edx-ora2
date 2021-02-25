/**
 Handles Response Editor of tinymce type.
 * */

(function (define) {
  const dependencies = [];
  const tinymceCssFile = '/static/js/vendor/tinymce/js/tinymce/skins/studio-tmce4/skin.min.css';

  if (typeof window.tinymce === 'undefined') {
    // If tinymce is not available, we need to load it
    dependencies.push('tinymce');
    dependencies.push('jquery.tinymce');

    // we also need to add css for tinymce
    if (!$(`link[href='${tinymceCssFile}']`).length) {
      $(`<link href="${tinymceCssFile}" type="text/css" rel="stylesheet" />`).appendTo('head');
    }
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
          theme: 'modern',
          skin: 'studio-tmce4',
          height: '300',
          schema: 'html5',
          plugins: 'code image link lists',
          toolbar: 'formatselect | bold italic underline | link blockquote image | numlist bullist outdent indent | strikethrough | code | undo redo',
          setup: (editor) => {
            // keep editor instances for later use
            editor.on('init', () => {
              this.editorInstances.push(editor);
            });
          },
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

        this.elements.each(function () {
          // check if it's readonly
          const disabled = $(this).attr('disabled');
          const config = ctrl.getTinyMCEConfig(disabled);
          $(this).tinymce(config);
        });
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
