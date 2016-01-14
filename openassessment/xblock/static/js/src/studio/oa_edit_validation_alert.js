/**
A class which controls the validation alert which we place at the top of the rubric page after
changes are made which will propagate to the settings section.

Returns:
    Openassessment.ValidationAlert
 */
OpenAssessment.ValidationAlert = function() {
    this.element = $('#openassessment_validation_alert');
    this.editorElement = $(this.element).parent();
    this.title = $(".openassessment_alert_title", this.element);
    this.message = $(".openassessment_alert_message", this.element);
    this.closeButton = $(".openassessment_alert_close", this.element);
    this.ALERT_YELLOW = 'rgb(192, 172, 0)';
    this.DARK_GREY = '#323232';
};

OpenAssessment.ValidationAlert.prototype = {

    /**
    Install the event handlers for the alert.
    **/
    install: function() {
        var alert = this;
        this.closeButton.click(
            function(eventObject) {
                eventObject.preventDefault();
                alert.hide();
            }
        );
        return this;
    },

    /**
    Hides the alert.

    Returns:
        OpenAssessment.ValidationAlert
    */
    hide: function() {
        // Finds the height of all other elements in the editor_and_tabs (the Header) and sets the height
        // of the editing area to be 100% of that element minus those constraints.
        var headerHeight = $('#openassessment_editor_header', this.editorElement).outerHeight();
        this.element.addClass('covered');
        var styles = {
            'height': 'Calc(100% - ' + headerHeight + 'px)',
            'border-top-right-radius': '3px',
            'border-top-left-radius': '3px'
        };

        $('.oa_editor_content_wrapper', this.editorElement).each(function() {
            $(this).css(styles);
        });

        return this;
    },

    /**
    Displays the alert.

    Returns:
        OpenAssessment.ValidationAlert
    */
    show: function() {
        var view = this;

        if (this.isVisible()) {
            $(this.element).animate(
                {'background-color': view.ALERT_YELLOW}, 300, 'swing', function() {
                    $(this).animate({'background-color': view.DARK_GREY}, 700, 'swing');
                }
            );
        }
        else {
            // Finds the height of all other elements in the editor_and_tabs (the Header and Alert) and sets
            // the height of the editing area to be 100% of that element minus those constraints.
            this.element.removeClass('covered');
            var alertHeight = this.element.outerHeight();
            var headerHeight = $('#openassessment_editor_header', this.editorElement).outerHeight();
            var heightString = 'Calc(100% - ' + (alertHeight + headerHeight) + 'px)';
            var styles = {
                'height': heightString,
                'border-top-right-radius': '0px',
                'border-top-left-radius': '0px'
            };

            $('.oa_editor_content_wrapper', this.editorElement).each(function() {
                $(this).css(styles);
                $(this).scrollTop($(this).scrollTop() + alertHeight); //keep our relative scroll position the same
            });

        }

        return this;
    },

    /**
    Sets the message of the alert.
    How will this work with internationalization?

    Args:
        newTitle (string): the new title that the message will have
        newMessage (string): the new text that the message's body will contain

    Returns:
        OpenAssessment.ValidationAlert
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
        return !this.element.hasClass('covered');
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
    },
};
