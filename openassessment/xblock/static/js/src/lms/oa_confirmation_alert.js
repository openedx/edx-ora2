
export class ConfirmationAlert {
	CONFIRM_STR = gettext("Confirm")
	CANCEL_STR = gettext("Cancel")

	constructor(element) {
		this.dialog = element.dialog({
			dialogClass: "no-close ora-confirmation-alert",
			autoOpen: false,
			resizable: false,
			height: "auto",
			width: "auto",
			modal: true,  
		});
		this.messageContainer = this.dialog.find('p.dialog-text');
	}

	setButtons(confirmCallback, cancelCallback) {
		this.dialog.dialog('option', 'buttons', {
			[this.CONFIRM_STR]: () => {
				this.dialog.dialog("close");
				confirmCallback()
			},
			[this.CANCEL_STR]: () => {
				this.dialog.dialog("close");
				cancelCallback()
			},
		});
	}

	setMessage(message) {
		this.messageContainer.text(message);
	}

	setTitle(title){
		this.dialog.dialog('option', 'title', title);
	}

	open() {
		this.dialog.dialog("open");
	}

	confirm(title, message, confirmCallback, cancelCallback) {
		this.setTitle(title);
		this.setMessage(message);
		this.setButtons(confirmCallback, cancelCallback);
		this.open();
	}
}

export default ConfirmationAlert;