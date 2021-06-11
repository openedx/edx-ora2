/**
 Handles Response Editor of simple textarea type.
 * */

(function (define) {
  define(() => {
    class EditorTextarea {
      /**
       Loads textarea editor.

      Args:
      elements (object): editor elements selected by jQuery
      * */
      load(elements) {
        this.elements = elements;
        return Promise.resolve();
      }

      /**
       Set on change listener to the editor.

      Args:
      handler (Function)
      * */
      setOnChangeListener(handler) {
        this.elements.on('change keyup drop paste', handler);
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

    // return a function, to be able to create new instance everytime.
    return function () {
      return new EditorTextarea();
    };
  });
}).call(window, window.define || window.RequireJS.define);
