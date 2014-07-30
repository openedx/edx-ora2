/**
A class which controls the validation alert which we place at the top of the rubric page after
changes are made which will propagate to the settings section.

Returns:
    Openassessment.ValidationAlert
 */
OpenAssessment.ValidationAlert = function() {
    this.element = $('#openassessment_rubric_validation_alert');
    this.rubricContentElement = $('#openassessment_rubric_content_editor');
    this.title = $(".openassessment_alert_title", this.element);
    this.message = $(".openassessment_alert_message", this.element);
};

OpenAssessment.ValidationAlert.prototype = {

    /**
    TODO
    **/
    installEventHandlers: function() {
        var alert = this;
        $(".openassessment_alert_close", this.element).click(
            function(eventObject) {
                eventObject.preventDefault();
                alert.hide();
            }
        );
    },

    /**
    Hides the alert.

    Returns:
        TODO
    */
    hide: function() {
        this.element.addClass('is--hidden');
        this.rubricContentElement.removeClass('openassessment_alert_shown');
        return this;
    },

    /**
    Displays the alert.

    Returns:
        TODO
    */
    show : function() {
        this.element.removeClass('is--hidden');
        this.rubricContentElement.addClass('openassessment_alert_shown');
        return this;
    },

    /**
    Sets the message of the alert.
    How will this work with internationalization?

    Args:
        newTitle (str): the new title that the message will have
        newMessage (str): the new text that the message's body will contain

    Returns:
        TODO
    */
    setMessage: function(newTitle, newMessage) {
        this.title.text(newTitle);
        this.message.text(newMessage);
        return this;
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
