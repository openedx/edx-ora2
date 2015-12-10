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
        load: function(onSuccessCallback) {
            var view = this;

            // If we're course staff, the base template should contain a section
            // for us to render the staff area into.  If that doesn't exist,
            // then we're not staff, so we don't need to send the AJAX request.
            if ($('.openassessment__staff-area', view.element).length > 0) {
                this.server.render('staff_area').done(function(html) {
                    // Load the HTML and install event handlers
                    $('.openassessment__staff-area', view.element).replaceWith(html);
                    view.server.renderLatex($('.openassessment__staff-area', view.element));
                    view.installHandlers();
                    if (onSuccessCallback) {
                        onSuccessCallback();
                    }
                }).fail(function() {
                    view.baseView.showLoadError('staff_area');
                });
            }
        },

        /**
         * Upon request, loads the student info section of the staff area.
         * This allows viewing all the submissions and assessments associated
         * to the given student's current workflow.
         *
         * @param {object} options An optional set of options to render the section.
         * @returns {promise} A promise representing the successful oading
         * of the student info section.
         */
        loadStudentInfo: function(options) {
            var view = this;
            var $staffTools = $('.openassessment__staff-tools', this.element);
            var $form = $staffTools.find('.openassessment_student_info_form');
            var studentUsername = $staffTools.find('.openassessment__student_username').val();
            var showFormError = function(errorMessage) {
                $form.find('.form--error').text(errorMessage);
            };
            var deferred = $.Deferred();

            // Clear any previous student information
            $('.openassessment__student-info', view.element).text('');

            if (studentUsername.trim()) {
                this.server.studentInfo(studentUsername, options).done(function(html) {
                    // Clear any error message
                    showFormError('');

                    // Load the HTML and install event handlers
                    $('.openassessment__student-info', view.element).replaceWith(html);

                    // Install key handler for cancel submission button.
                    $staffTools.on('click', '.action--submit-cancel-submission', function(eventObject) {
                        eventObject.preventDefault();
                        view.cancelSubmission($(this).data('submission-uuid'));
                    });

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
                                var target = $(eventObject.currentTarget),
                                    rootElement = target.closest('.openassessment__student-info'),
                                    submissionID = rootElement.data('submission-uuid');

                                eventObject.preventDefault();
                                view.submitStaffAssessment(submissionID, rubric);
                            }
                        );
                    }
                    deferred.resolve();
                }).fail(function() {
                    showFormError(gettext('Unexpected server error.'));
                    deferred.reject();
                });
            } else {
                showFormError(gettext('You must provide a learner name.'));
                deferred.reject();
            }
            return deferred.promise();
        },

        loadStaffGradeForm: function(eventObject) {
            var view = this;
            var staff_form_element = $(eventObject.currentTarget);
            var isCollapsed = staff_form_element.hasClass("is--collapsed");
            var deferred = $.Deferred();

            if (isCollapsed && !this.staffGradeFormLoaded) {
                eventObject.preventDefault();
                this.staffGradeFormLoaded = true;
                this.server.staffGradeForm().done(function(html) {
                    // TODO: need to create a div to show an error message if this server call fails.
                    //showFormError('');

                    // Load the HTML and install event handlers
                    $('.staff__grade__form', view.element).replaceWith(html);

                    // Initialize the rubric : TODO SHARE CODE!
                    var $rubric = $('.staff-assessment__assessment', view.element);
                    if ($rubric.size() > 0) {
                        var rubricElement = $rubric.get(0);
                        var rubric = new OpenAssessment.Rubric(rubricElement);

                        // Install a change handler for rubric options to enable/disable the submit button
                        rubric.canSubmitCallback($.proxy(view.staffSubmitEnabled, view));

                        // Install a click handler for the submit buttons
                        $('.wrapper--staff-assessment .action--submit', view.element).click(
                            function(eventObject) {
                                var submissionID = staff_form_element.find('.staff__grade__form').data('submission-uuid');  // This was a change

                                eventObject.preventDefault();
                                view.submitStaffGradeForm(submissionID, rubric,
                                    $(eventObject.currentTarget).hasClass('continue_grading--action')
                                );  // This was a change
                            }
                        );
                    }
                    deferred.resolve();
                }).fail(function() {
                    // showFormError(gettext('Unexpected server error.'));
                    this.staffGradeFormLoaded = false;
                    deferred.reject();
                });

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
            var $staffGradeTool = $('.openassessment__staff-grading', $staffArea);

            if ($staffArea.length <= 0) {
                return;
            }

            this.baseView.setUpCollapseExpand($staffTools, function() {});
            this.baseView.setUpCollapseExpand($staffInfo, function() {});
            this.baseView.setUpCollapseExpand($staffGradeTool, function() {});

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

            // Install a click handler for showing the staff grading form.
            $staffGradeTool.find('.staff__grade__control').click(
                function(eventObject) {
                    // Don't call preventDefault because this click handler will be triggerred by
                    // things like the radio buttons within the form-- we want them to be able to
                    // handle the click events (and loadStaffGradeForm will be a no-op).
                    view.loadStaffGradeForm(eventObject);
                }
            );
        },

        /**
         * Sends a request to the server to schedule the training
         * of classifiers for this problem's Example Based Assessments.
         */
        scheduleTraining: function() {
            var view = this;
            this.server.scheduleTraining().done(function(msg) {
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
            this.server.rescheduleUnfinishedTasks().done(function(msg) {
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
            var comments = $('.cancel_submission_comments', this.element).val();
            this.server.cancelSubmission(submissionUUID, comments).done(function() {
                // Note: we ignore any message returned from the server and instead
                // re-render the student info with the "Learner's Final Grade"
                // section expanded. This section will show that the learner's
                // submission was cancelled.
                view.loadStudentInfo({expanded_view: 'final-grade'});
            }).fail(function(errorMessage) {
                $('.cancel-submission-error').html(_.escape(errorMessage));
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
         * @param {boolean} enabled If specified, sets the state of the button.
         * @returns {boolean} Whether the button is enabled
         */
        staffSubmitEnabled: function(enabled) {
            var button = $('.wrapper--staff-assessment .action--submit', this.element);
            if (typeof enabled === 'undefined') {
                return !button.hasClass('is--disabled');
            } else {
                button.toggleClass('is--disabled', !enabled);
                return enabled;
            }
        },

        /**
         * Submit the staff assessment.
         *
         * @param {string} submissionID The ID of the submission to be submitted.
         * @param {element} rubric The rubric element to be assessed.
         */
        submitStaffAssessment: function(submissionID, rubric) {
            // Send the assessment to the server
            var view = this;
            view.staffSubmitEnabled(false);

            this.server.staffAssess(
                rubric.optionsSelected(), rubric.criterionFeedback(), rubric.overallFeedback(), submissionID
            ).done(function() {
                // Note: we ignore any message returned from the server and instead
                // re-render the student info with the "Learner's Final Grade"
                // section expanded. This section will show the learner's
                // final grade and in the future should include details of
                // the staff override itself.
                view.loadStudentInfo({expanded_view: 'final-grade'});
            }).fail(function(errorMessage) {
                // TODO: check how this renders Andy!
                $('.staff-override-error', this.element).html(_.escape(errorMessage));
                view.staffSubmitEnabled(true);
            });
        },

        // Can some version of this method be shared with submitStaffAssessment?
        submitStaffGradeForm: function(submissionID, rubric, continueGrading) {
            // Send the assessment to the server
            var view = this;
            view.staffSubmitEnabled(false);

            this.server.staffAssess(
                rubric.optionsSelected(), rubric.criterionFeedback(), rubric.overallFeedback(), submissionID
            ).done(function() {
                view.staffGradeFormLoaded = false;
                var onSuccessCallback = function () {
                    $('.button-staff-grading').click();
                    if (continueGrading) {
                        $('.staff__grade__title').click();
                    }
                };
                view.load(onSuccessCallback);
            }).fail(function(errorMessage) {
                // TODO: this needs styling help Andy!
                $('.staff-grade-error', this.element).html(_.escape(errorMessage));
                view.staffSubmitEnabled(true);
            });
        }
    };
})(OpenAssessment);
