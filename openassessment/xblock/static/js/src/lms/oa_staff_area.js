(function(OpenAssessment) {
    'use strict';
    /**
     * Interface for staff area view.
     *
     * Args:
     *   element (DOM element): The DOM element representing the XBlock.
     *   server (OpenAssessment.Server): The interface to the XBlock server.
     *   baseView (OpenAssessment.BaseView): Container view.
     *
     * Returns:
     *   OpenAssessment.StaffAreaView
     */
    OpenAssessment.StaffAreaView = function(element, server, baseView) {
        this.element = element;
        this.server = server;
        this.baseView = baseView;
    };

    OpenAssessment.StaffAreaView.prototype = {

        /**
         Load the staff area.
         **/
        load: function() {
            var view = this;

            // If we're course staff, the base template should contain a section
            // for us to render the staff area into.  If that doesn't exist,
            // then we're not staff, so we don't need to send the AJAX request.
            if ($('#openassessment__staff-area', view.element).length > 0) {
                this.server.render('staff_area').done(
                    function(html) {
                        // Load the HTML and install event handlers
                        $('#openassessment__staff-area', view.element).replaceWith(html);
                        view.server.renderLatex($('#openassessment__staff-area', view.element));
                        view.installHandlers();
                    }
                ).fail(
                    function() {
                        view.baseView.showLoadError('staff_area');
                    }
                );
            }
        },

        /**
         Upon request, loads the student info section of the staff info view. This
         allows viewing all the submissions and assessments associated to the given
         student's current workflow.
         **/
        loadStudentInfo: function() {
            var view = this;
            var sel = $('#openassessment__staff-tools', this.element);
            var studentUsername = sel.find('#openassessment__student_username').val();
            this.server.studentInfo(studentUsername).done(
                function(html) {
                    // Load the HTML and install event handlers
                    $('#openassessment__student-info', view.element).replaceWith(html);

                    // Install key handler for new staff grade Save button.
                    var selCancelSub = $('#openassessment__staff-info__cancel__submission', view.element);
                    selCancelSub.on('click', '#submit_cancel_submission', function(eventObject) {
                            eventObject.preventDefault();
                            view.cancelSubmission($(this).data('submission-uuid'));
                        }
                    );

                    // Install change handler for textarea (to enable cancel submission button)
                    var handleChange = function(eventData) { view.handleCommentChanged(eventData); };
                    selCancelSub.find('#staff-info__cancel-submission__comments')
                        .on('change keyup drop paste', handleChange);

                }
            ).fail(
                function() {
                    view.showLoadError('student_info');
                }
            );
        },

        /**
         Install event handlers for the view.
         **/
        installHandlers: function() {
            var $staffArea = $('#openassessment__staff-area', this.element);
            var toolsElement = $('#openassessment__staff-tools', $staffArea);
            var infoElement = $('#openassessment__student-info', $staffArea);
            var view = this;

            if (toolsElement.length <= 0) {
                return;
            }

            this.baseView.setUpCollapseExpand(toolsElement, function() {});
            this.baseView.setUpCollapseExpand(infoElement, function() {});

            // Install a click handler for the staff button panel
            $staffArea.find('.ui-staff__button').click(
                function(eventObject) {
                    var $button = $(eventObject.currentTarget),
                        panelID = $button.data('panel'),
                        $panel = $staffArea.find('#' + panelID).first();
                    if ($button.hasClass('is--active')) {
                        $button.removeClass('is--active');
                        $panel.addClass('is--hidden');
                    } else {
                        $staffArea.find('.ui-staff__button').removeClass('is--active');
                        $button.addClass('is--active');
                        $staffArea.find('.wrapper--ui-staff').addClass('is--hidden');
                        $panel.removeClass('is--hidden');
                    }
                }
            );

            // Install a click handler for the close button for staff panels
            $staffArea.find('.ui-staff_close_button').click(
                function(eventObject) {
                    var $button = $(eventObject.currentTarget),
                        $panel = $button.closest('.wrapper--ui-staff');
                    $staffArea.find('.ui-staff__button').removeClass('is--active');
                    $panel.addClass('is--hidden');
                }
            );

            // Install key handler for student id field
            toolsElement.find('#openassessment_student_info_form').submit(
                function(eventObject) {
                    eventObject.preventDefault();
                    view.loadStudentInfo();
                }
            );

            // Install a click handler for requesting student info
            toolsElement.find('#submit_student_username').click(
                function(eventObject) {
                    eventObject.preventDefault();
                    view.loadStudentInfo();
                }
            );

            // Install a click handler for scheduling AI classifier training
            toolsElement.find('#schedule_training').click(
                function(eventObject) {
                    eventObject.preventDefault();
                    view.scheduleTraining();
                }
            );

            // Install a click handler for rescheduling unfinished AI tasks for this problem
            toolsElement.find('#reschedule_unfinished_tasks').click(
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
                    $('#schedule_training_message', view.element).text(msg);
                }
            ).fail(function(errMsg) {
                    $('#schedule_training_message', view.element).text(errMsg);
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
                    $('#reschedule_unfinished_tasks_message', view.element).text(msg);
                }
            ).fail(function(errMsg) {
                    $('#reschedule_unfinished_tasks_message', view.element).text(errMsg);
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
})(OpenAssessment);
