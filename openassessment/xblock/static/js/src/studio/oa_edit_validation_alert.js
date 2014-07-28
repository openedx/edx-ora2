/**
A class which controls the validation alert which we place at the top of the rubric page after
changes are made which will propagate to the settings section.

Args:
    element (element): The element that specifies the div that the validation consists of.

Returns:
    Openassessment.ValidationAlert
 */
OpenAssessment.ValidationAlert = function (element) {
    var alert = this;
    this.element = element;
    this.title = $(".openassessment_alert_title", this.element);
    this.message = $(".openassessment_alert_message", this.element);
    $(".openassessment_alert_close", element).click(function(eventObject) {
            eventObject.preventDefault();
            alert.hide();
        }
    );
};

OpenAssessment.ValidationAlert.prototype = {

    /**
     Hides the alert.
     */
    hide: function() {
        this.element.addClass('is--hidden');
    },

    /**
     Displays the alert.
     */
    show : function() {
        this.element.removeClass('is--hidden');
    },

    /**
     Sets the message of the alert.
     How will this work with internationalization?

     Args:
         newTitle (str): the new title that the message will have
         newMessage (str): the new text that the message's body will contain
     */
    setMessage: function(newTitle, newMessage) {
        this.title.text(newTitle);
        this.message.text(newMessage);
    },

    /**
    Check whether the alert is currently visible.

    Returns:
        boolean

    **/
    isVisible: function() {
        return !this.element.hasClass('is--hidden');
    },

    /**
    Retrieve the title of the alert.

    Returns:
        string

    **/
    getTitle: function() {
        return this.title.text();
    },

    /**
    Retrieve the message of the alert.

    Returns:
        string
    **/
    getMessage: function() {
        return this.message.text();
    }
};
