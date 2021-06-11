/**
 Loader class for response editors.
 * */

export class ResponseEditorLoader {
  /**
   Constructor for ResponseEditorLoader

   Args:
   availableEditors (object): Available Editor configurations
   * */
  constructor(availableEditors) {
    this.availableEditors = availableEditors;
  }

  /**
   Loads an editor for given elements

   Args:
   selectedEditor (string): Which editor to load
   elements (object): Elements selected via Jquery selector

   Returns:
   promise - resolves with an instance of the editor controller
   * */
  load(selectedEditor, elements) {
    // Find configuration for the selected editor
    const editorConfig = this.availableEditors[selectedEditor];

    return new Promise(((resolve, reject) => {
      // use require js to load the editor's javascript files
      // require js available in Studio via ``window.require``
      // and in LMS via ``window.RequireJS.require``
      (function (require) {
        const requiredJSFiles = editorConfig.js;

        /* eslint-disable-next-line import/no-dynamic-require */
        require(requiredJSFiles, (...args) => {
          // create a new instance to avoid overlapping with other ORA blocks
          // assume last item in args will be the editor controller
          const editor = args[args.length - 1]();
          editor.load(elements).then(() => resolve(editor));
        });
      }).call(window, window.require || window.RequireJS.require);

      // if the editor needs css, load them
      const requiredCSSFiles = editorConfig.css;
      if (requiredCSSFiles) {
        Array.from(requiredCSSFiles).forEach(cssFile => {
          if (!$(`link[href='${cssFile}']`).length) {
            $(`<link href="${cssFile}" type="text/css" rel="stylesheet" />`).appendTo('head');
          }
        });
      }
    }));
  }
}

export default ResponseEditorLoader;
