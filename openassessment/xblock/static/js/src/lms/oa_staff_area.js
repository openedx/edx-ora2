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
         * Load the staff area.
         */
        load: function() {
            var view = this;

            // If we're course staff, the base template should contain a section
            // for us to render the staff area into.  If that doesn't exist,
            // then we're not staff, so we don't need to send the AJAX request.
            if ($('.openassessment__staff-area', view.element).length > 0) {
                this.server.render('staff_area')
                    .done(function(html) {
                        // Load the HTML and install event handlers
                        $('.openassessment__staff-area', view.element).replaceWith(html);
                        view.server.renderLatex($('.openassessment__staff-area', view.element));
                        view.installHandlers();
                    }).fail(function() {
                        view.baseView.showLoadError('staff_area');
                    }
                );
            }
        },

        /**
         * Upon request, loads the student info section of the staff area.
         * This allows viewing all the submissions and assessments associated
         * to the given student's current workflow.
         */
        loadStudentInfo: function() {
            var view = this;
            var $staffTools = $('.openassessment__staff-tools', this.element);
            var student_username = $staffTools.find('.openassessment__student_username').val();
            if (student_username.trim()) {
                this.server.studentInfo(student_username)
                    .done(function(html) {
                        // Load the HTML and install event handlers
                        $('.openassessment__student-info', view.element).replaceWith(html);

                        // Install key handler for cancel submission button.
                        $staffTools.on('click', '.action--submit-cancel-submission', function (eventObject) {
                                eventObject.preventDefault();
                                view.cancelSubmission($(this).data('submission-uuid'));
                            }
                        );

                        // Install change handler for textarea (to enable cancel submission button)
                        var handleChange = function(eventData) { view.handleCommentChanged(eventData); };
                        $staffTools.find('.cancel_submission_comments')
                            .on('change keyup drop paste', handleChange);


                        // Initialize the rubric
                        var $rubric = $('.staff-assessment__assessment', view.element);
                        if ($rubric.size() > 0) {
                            var rubricElement = $rubric.get(0);
                            var rubric = new OpenAssessment.Rubric(rubricElement);

                            // Install a change handler for rubric options to enable/disable the submit button
                            rubric.canSubmitCallback($.proxy(view.staffSubmitEnabled, view));

                            // Install a click handler for the submit button
                            $('.wrapper--staff-assessment .action--submit', view.element).click(
                                function(eventObject) {
                                    eventObject.preventDefault();
                                    view.submitStaffAssessment(rubric);
                                }
                            );
                        }
                    }).fail(function() {
                        view.baseView.showLoadError('student_info');
                    }
                );
            } else {
                view.baseView.showLoadError('student_info', gettext('A student name must be provided.'));
            }
        },

        /**
         * Install event handlers for the view.
         */
        installHandlers: function() {
            var view = this;
            var $staffArea = $('.openassessment__staff-area', this.element);
            var $staffTools = $('.openassessment__staff-tools', $staffArea);
            var $staffInfo =  $('.openassessment__student-info', $staffArea);

            if ($staffArea.length <= 0) {
                return;
            }

            this.baseView.setUpCollapseExpand($staffTools, function() {});
            this.baseView.setUpCollapseExpand($staffInfo, function() {});

            // Install a click handler for the staff button panel
            $staffArea.find('.ui-staff__button').click(
                function(eventObject) {
                    var $button = $(eventObject.currentTarget),
                        panelClass = $button.data('panel'),
                        $panel = $staffArea.find('.' + panelClass).first();
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
            $staffTools.find('.openassessment_student_info_form').submit(
                function(eventObject) {
                    eventObject.preventDefault();
                    view.loadStudentInfo();
                }
            );

            // Install a click handler for requesting student info
            $staffTools.find('.action--submit-username').click(
                function(eventObject) {
                    eventObject.preventDefault();
                    view.loadStudentInfo();
                }
            );

            // Install a click handler for scheduling AI classifier training
            $staffTools.find('.action--submit-training').click(
                function(eventObject) {
                    eventObject.preventDefault();
                    view.scheduleTraining();
                }
            );

            // Install a click handler for rescheduling unfinished AI tasks for this problem
            $staffTools.find('.action--submit-unfinished-tasks').click(
                function(eventObject) {
                    eventObject.preventDefault();
                    view.rescheduleUnfinishedTasks();
                }
            );
        },

        /**
         * Sends a request to the server to schedule the training
         * of classifiers for this problem's Example Based Assessments.
         */
        scheduleTraining: function() {
            var view = this;
            this.server.scheduleTraining()
                .done(function(msg) {
                    $('.schedule_training_message', view.element).text(msg);
                }).fail(function(errMsg) {
                $('.schedule_training_message', view.element).text(errMsg);
            });
        },

        /**
         * Begins the process of rescheduling all unfinished grading tasks.
         * This includes checking if the classifiers have been created,
         * and grading any unfinished student submissions.
         */
        rescheduleUnfinishedTasks: function() {
            var view = this;
            this.server.rescheduleUnfinishedTasks()
                .done(function(msg) {
                    $('.reschedule_unfinished_tasks_message', view.element).text(msg);
                }).fail(function(errMsg) {
                $('.reschedule_unfinished_tasks_message', view.element).text(errMsg);
            });
        },

        /**
         * Upon request, cancel the submission from grading pool.
         */
        cancelSubmission: function(submissionUUID) {
            // Immediately disable the button to prevent multiple requests.
            this.cancelSubmissionEnabled(false);
            var view = this;
            var comments = this.element.find('.cancel_submission_comments').val();
            this.server.cancelSubmission(submissionUUID, comments)
                .done(function(msg) {
                    $('.cancel-submission-error').html('');
                    $('.openassessment__staff-info__cancel__submission', view.element).html(msg);
                })
                .fail(function(errMsg) {
                    $('.cancel-submission-error').html(errMsg);
                });
        },

        /**
         * Enable/disable the cancel submission button.
         *
         * Check whether the cancel submission button is enabled.
         *
         * Args:
         *   enabled (bool): If specified, set the state of the button.
         *
         * Returns:
         *   bool: Whether the button is enabled.
         *
         * Examples:
         * >> view.submitEnabled(true);  // enable the button
         * >> view.submitEnabled();  // check whether the button is enabled
         * >> true
         */
        cancelSubmissionEnabled: function(enabled) {
            var $cancelButton = $('.action--submit-cancel-submission', this.element);
            if (typeof enabled === 'undefined') {
                return !$cancelButton.hasClass('is--disabled');
            } else {
                $cancelButton.toggleClass('is--disabled', !enabled);
            }
        },

        /**
         * Set the comment text.
         *
         * Retrieve the comment text.
         *
         * Args:
         *   text (string): reason to .
         *
         * Returns:
         *   string: The current comment text.
         */
        comment: function(text) {
            var $submissionComments = $('.cancel_submission_comments', this.element);
            if (typeof text === 'undefined') {
                return $submissionComments.val();
            } else {
                $submissionComments.val(text);
            }
        },

        /**
         * Enable/disable the cancel submission based on whether
         * the user has entered a comment.
         */
        handleCommentChanged: function() {
            // Enable the cancel submission button only for non-blank comments
            var isBlank = $.trim(this.comment()) !== '';
            this.cancelSubmissionEnabled(isBlank);
        },


        /**
         * Enable/disable the staff assessment submit button.
         *
         * @param enabled If specified, sets the state of the button.
         * @returns {boolean} Whether the button is enabled
         */
        staffSubmitEnabled: function(enabled) {
            var button = $('.wrapper--staff-assessment .action--submit', this.element);
            if (typeof enabled === 'undefined') {
                return !button.hasClass('is--disabled');
            } else {
                button.toggleClass('is--disabled', !enabled);
            }
        },

        /**
         * Submit the staff assessment.
         *
         * @param rubric The rubric being assessed.
         */
        submitStaffAssessment: function(rubric) {
            // Send the assessment to the server
            var view = this;
            var baseView = this.baseView;
            baseView.toggleActionError('staff', null);
            view.staffSubmitEnabled(false);

            this.server.staffAssess(rubric.optionsSelected(), rubric.criterionFeedback(), rubric.overallFeedback())
                .done(
                    function() {
                        baseView.loadAssessmentModules();
                        baseView.scrollToTop();
                    }
                )
                .fail(function(errorMessage) {
                    baseView.toggleActionError('staff', errorMessage);
                    view.staffSubmitEnabled(true);
                });
        }
    };
})(OpenAssessment);
