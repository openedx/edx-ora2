/**
* Class wrapping a jquery-ui dialog widget to provide a convenient API
*/
export class ConfirmationAlert {
  CONFIRM_STR = gettext('Confirm')

  CANCEL_STR = gettext('Cancel')

  constructor(element) {
    this.dialog = element.dialog({
      dialogClass: 'no-close ora-confirmation-alert',
      autoOpen: false,
      resizable: false,
      height: 'auto',
      width: 'auto',
      modal: true,
    });
    this.messageContainer = this.dialog.find('p.dialog-text');
  }

  /**
  * Set the callback functions for the confirm and cancel buttons.
  * @param {function} confirmCallback
  * @param {function} cancelCallback
  */
  setButtons(confirmCallback, cancelCallback) {
    this.dialog.dialog('option', 'buttons', {
      [this.CONFIRM_STR]: () => {
        this.dialog.dialog('close');
        confirmCallback();
      },
      [this.CANCEL_STR]: () => {
        this.dialog.dialog('close');
        cancelCallback();
      },
    });
  }

  /**
  * Set the message for the body text of the dialog modal
  * @param {string} message
  */
  setMessage(message) {
    this.messageContainer.text(message);
  }

  /**
  * Set the message for the title bar of the dialog modal
  * @param {string} title
  */
  setTitle(title) {
    this.dialog.dialog('option', 'title', title);
  }

  /**
  * Opens the modal with the currently set values
  */
  open() {
    this.dialog.dialog('open');
  }

  /**
  * Set the title, message, and callbacks for the confirm and cancel buttons,
  * and then open the modal.
  *
  * @param {string} title
  * @param {string} message
  * @param {function} confirmCallback
  * @param {function} cancelCallback
  */
  confirm(title, message, confirmCallback, cancelCallback) {
    this.setTitle(title);
    this.setMessage(message);
    this.setButtons(confirmCallback, cancelCallback);
    this.open();
  }
}

export default ConfirmationAlert;
