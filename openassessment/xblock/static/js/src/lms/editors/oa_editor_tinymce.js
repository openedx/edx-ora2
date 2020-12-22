/**
 Handles Response Editor of tinymce type.
 * */

/**
 Utility to load TinyMCE editor in both LMS and Studio.
 Studio by default has TinyMCE loaded but LMS doesn't.
 This function uses RequireJS from LMS to load TinyMCE.

 Returns:
 Promise
 * */
function loadTinyMCE() {
  return new Promise(((resolve, reject) => {
    // if tinymce is not loaded
    if (typeof $().tinymce === 'undefined') {
      // try to load tinymce via requirejs (available in LMS)
      (function (require) {
        /* eslint-disable-next-line import/no-dynamic-require */
        require(['jquery.tinymce'], () => {
          resolve();
        });
      }).call(window, window.require || window.RequireJS.require);

      // add tinymce css
      $('head').append('<link rel="stylesheet" href="/static/js/vendor/tinymce/js/tinymce/skins/studio-tmce4/skin.min.css" type="text/css" />');
    } else {
      resolve();
    }
  }));
}


/**
 Build and return TinyMCE Configuration.
 * */
function getTinyMCEConfig() {
  return {};
}


class EditorTinymce {

  /**
   Loads TinyMCE editor.

   Args:
   elements (object): editor elements selected by jQuery

   Returns:
   Promise: Resolves when editor is loaded
   * */
  load(elements) {
    this.elements = elements;
    return new Promise((resolve, reject) => {
      loadTinyMCE().then(() => {
        this.elements.tinymce(getTinyMCEConfig());
        resolve();
      }).catch((reason) => reject(reason));
    });
  }

  /**
   Set event listener to the editor.

   Args:
   eventName (string)
   handler (Function)
   * */
  setEventListener(eventName, handler) {
    this.elements.on(eventName, handler);
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

// Make this editor accessible from openassessment-lms script
window.OpenAssessmentResponseEditor = EditorTinymce;
