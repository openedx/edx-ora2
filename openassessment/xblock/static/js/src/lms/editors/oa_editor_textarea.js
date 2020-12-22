/**
 Handles Response Editor of simple textarea type.
 * */

class EditorTextarea {

  /**
   Loads textarea editor. Just a simple promise that resolves immediately.

   Args:
   elements (object): editor elements selected by jQuery

   Returns:
   Promise: Resolves when editor is loaded
   * */
  load(elements) {
    this.elements = elements;
    return new Promise(((resolve, reject) => {
      resolve();
    }));
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
window.OpenAssessmentResponseEditor = EditorTextarea;
