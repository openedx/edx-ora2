/**
 Handles Response Editor of tinymce type.
 * */

(function (define) {
  const dependencies = [];
  const tinymceCssFile = '/static/js/vendor/tinymce/js/tinymce/skins/studio-tmce4/skin.min.css';

  // Create a flag to determine if we are in lms
  const isLMS = typeof window.LmsRuntime !== 'undefined';

  // Determine which css file should be loaded to style text in the editor
  let contentCssFile = '/static/studio/js/vendor/tinymce/js/tinymce/skins/studio-tmce4/content.min.css';
  if (isLMS) {
    contentCssFile = '/static/js/vendor/tinymce/js/tinymce/skins/studio-tmce4/content.min.css';
  }

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
          content_css: contentCssFile,
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
          return this.editorInstances.map(editor => {
            const content = editor.getContent();
            // Remove linebreaks from TinyMCE output
            // This is a workaround for TinyMCE 4 only,
            // 5.x does not have this bug.
            return content.replace(/(\r\n|\n|\r)/gm, '');
          });
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
