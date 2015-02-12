/**
 Interface for staff info view.

 Args:
 element (DOM element): The DOM element representing the XBlock.
 server (OpenAssessment.Server): The interface to the XBlock server.
 baseView (OpenAssessment.BaseView): Container view.

 Returns:
 OpenAssessment.StaffInfoView
 **/
OpenAssessment.StaffInfoView = function(element, server, baseView) {
    this.element = element;
    this.server = server;
    this.baseView = baseView;
};


OpenAssessment.StaffInfoView.prototype = {

    /**
     Load the Student Info section in Staff Info.
     **/
    load: function() {
        var view = this;

        // If we're course staff, the base template should contain a section
        // for us to render the staff info to.  If that doesn't exist,
        // then we're not staff, so we don't need to send the AJAX request.
        if ($('#openassessment__staff-info', view.element).length > 0) {
            this.server.render('staff_info').done(
                function(html) {
                    // Load the HTML and install event handlers
                    $('#openassessment__staff-info', view.element).replaceWith(html);
                    view.server.renderLatex($('#openassessment__staff-info', view.element));
                    view.installHandlers();
                }
            ).fail(function(errMsg) {
                    view.baseView.showLoadError('staff_info');
                });
        }
    },

    /**
     Upon request, loads the student info section of the staff info view. This
     allows viewing all the submissions and assessments associated to the given
     student's current workflow.
     **/
    loadStudentInfo: function() {
        var view = this;
        var sel = $('#openassessment__staff-info', this.element);
        var student_username = sel.find('#openassessment__student_username').val();
        this.server.studentInfo(student_username).done(
            function(html) {
                // Load the HTML and install event handlers
                $('#openassessment__student-info', view.element).replaceWith(html);

                // Install key handler for new staff grade Save button.
                var selCancelSub = $('#openassessment__staff-info__cancel__submission', this.element);
                selCancelSub.on('click', '#submit_cancel_submission', function (eventObject) {
                        eventObject.preventDefault();
                        view.cancelSubmission($(this).data('submission-uuid'));
                    }
                );

                // Install change handler for textarea (to enable cancel submission button)
                var handleChange = function(eventData) { view.handleCommentChanged(); };
                selCancelSub.find('#staff-info__cancel-submission__comments').on('change keyup drop paste', handleChange);

            }
        ).fail(function(errMsg) {
                view.showLoadError('student_info');
        });
    },

    /**
     Install event handlers for the view.
     **/
    installHandlers: function() {
        var sel = $('#openassessment__staff-info', this.element);
        var selStudentInfo = $('#openassessment__student-info', this.element);
        var view = this;

        if (sel.length <= 0) {
            return;
        }

        this.baseView.setUpCollapseExpand(sel, function() {});
        this.baseView.setUpCollapseExpand(selStudentInfo, function() {});

        // Install key handler for student id field
        sel.find('#openassessment_student_info_form').submit(
            function(eventObject) {
                eventObject.preventDefault();
                view.loadStudentInfo();
            }
        );

        // Install a click handler for requesting student info
        sel.find('#submit_student_username').click(
            function(eventObject) {
                eventObject.preventDefault();
                view.loadStudentInfo();
            }
        );

        // Install a click handler for scheduling AI classifier training
        sel.find('#schedule_training').click(
            function(eventObject) {
                eventObject.preventDefault();
                view.scheduleTraining();
            }
        );

        // Install a click handler for rescheduling unfinished AI tasks for this problem
        sel.find('#reschedule_unfinished_tasks').click(
            function(eventObject) {
                eventObject.preventDefault();
                view.rescheduleUnfinishedTasks();
            }
        );
    },

    /**
     Sends a request to the server to schedule the training of classifiers for
     this problem's Example Based Assessments.

     **/
    scheduleTraining: function() {
        var view = this;
        this.server.scheduleTraining().done(
                function(msg) {
                    $('#schedule_training_message', this.element).text(msg)
                }
            ).fail(function(errMsg) {
                $('#schedule_training_message', this.element).text(errMsg)
            });
    },

    /**
     Begins the process of rescheduling all unfinished grading tasks. This incdludes
     checking if the classifiers have been created, and grading any unfinished
     student submissions.

     **/
    rescheduleUnfinishedTasks: function() {
        var view = this;
        this.server.rescheduleUnfinishedTasks().done(
                function(msg) {
                    $('#reschedule_unfinished_tasks_message', this.element).text(msg)
                }
            ).fail(function(errMsg) {
                $('#reschedule_unfinished_tasks_message', this.element).text(errMsg)
            });
    },

    /**
     Upon request, cancel the submission from grading pool.
     **/
    cancelSubmission: function(submissionUUID) {
        // Immediately disable the button to prevent multiple requests.
        this.cancelSubmissionEnabled(false);
        var view = this;
        var sel = $('#openassessment__student-info', this.element);
        var comments = sel.find('#staff-info__cancel-submission__comments').val();
        this.server.cancelSubmission(submissionUUID, comments).done(
            function(msg) {
                $('.cancel-submission-error').html('');
                $('#openassessment__staff-info__cancel__submission', view.element).html(msg);
            }
        ).fail(function(errMsg) {
                $('.cancel-submission-error').html(errMsg);
        });
    },

    /**
    Enable/disable the cancel submission button.
    Check whether the cancel submission button is enabled.

    Args:
        enabled (bool): If specified, set the state of the button.

    Returns:
        bool: Whether the button is enabled.

    Examples:
        >> view.submitEnabled(true);  // enable the button
        >> view.submitEnabled();  // check whether the button is enabled
        >> true
    **/
    cancelSubmissionEnabled: function(enabled) {
        var sel = $('#submit_cancel_submission', this.element);
        if (typeof enabled === 'undefined') {
            return !sel.hasClass('is--disabled');
        } else {
            sel.toggleClass('is--disabled', !enabled);
        }
    },

    /**
    Set the comment text.
    Retrieve the comment text.

    Args:
        text (string): reason to .

    Returns:
        string: The current comment text.
    **/
    comment: function(text) {
        var sel = $('#staff-info__cancel-submission__comments', this.element);
        if (typeof text === 'undefined') {
            return sel.val();
        } else {
            sel.val(text);
        }
    },

    /**
    Enable/disable the cancel submission based on whether
    the user has entered a comment.
    **/
    handleCommentChanged: function() {
        // Enable the cancel submission button only for non-blank comments
        var isBlank = ($.trim(this.comment()) !== '');
        this.cancelSubmissionEnabled(isBlank);
    }

};
