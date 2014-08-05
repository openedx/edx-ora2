/**
 * Encapsulate interactions with OpenAssessment XBlock handlers.
 */

// Since the server is included by both LMS and Studio views,
// skip loading it the second time.
if (typeof OpenAssessment.Server === "undefined" || !OpenAssessment.Server) {

    /**
     * Interface for server-side XBlock handlers.
     *
     * @param {runtime} runtime - An XBlock runtime instance.
     * @param {element} element - The DOM element representing this XBlock.
     * @constructor
     */
    OpenAssessment.Server = function(runtime, element) {
        this.runtime = runtime;
        this.element = element;
    };

    var jsonContentType = "application/json; charset=utf-8";

    OpenAssessment.Server.prototype = {

        /**
         * Returns the URL for the handler, specific to one instance of the XBlock on the page.
         *
         * @param {string} handler The name of the XBlock handler.
         * @returns {*} The URL for the handler.
         */
        url: function(handler) {
            return this.runtime.handlerUrl(this.element, handler);
        },

        /**
         * Render the XBlock.
         *
         * @param {string} component The component to render.
         * @returns {*} A JQuery promise, which resolves with the HTML of the rendered XBlock
         *     and fails with an error message.
         */
        render: function(component) {
            var view = this;
            var url = this.url('render_' + component);
            return $.Deferred(function(defer) {
                $.ajax({
                    url: url,
                    type: "POST",
                    dataType: "html"
                }).done(function(data) {
                    defer.resolveWith(view, [data]);
                }).fail(function() {
                    defer.rejectWith(view, [gettext('This section could not be loaded.')]);
                });
            }).promise();
        },

        /**
         * Render Latex for all new DOM elements with class 'allow--latex'.
         *
         * @param {element} element - The element to modify.
         */
        renderLatex: function(element) {
            element.filter(".allow--latex").each(function() {
                MathJax.Hub.Queue(['Typeset', MathJax.Hub, this]);
            });
        },

        /**
         * Render the Peer Assessment Section after a complete workflow, in order to
         * continue grading peers.
         *
         * @returns {promise} A JQuery promise, which resolves with the HTML of the rendered peer
         *     assessment section or fails with an error message.
         */
        renderContinuedPeer: function() {
            var view = this;
            var url = this.url('render_peer_assessment');

            return $.Deferred(function(defer) {
                $.ajax({
                    url: url,
                    type: "POST",
                    dataType: "html",
                    data: {continue_grading: true}
                }).done(function(data) {
                    defer.resolveWith(view, [data]);
                }).fail(function() {
                    defer.rejectWith(view, [gettext('This section could not be loaded.')]);
                });
            }).promise();
        },

        /**
         * Load the student information section inside the Staff Info section.
         *
         * @param {string} studentUsername - The username for the student.
         * @param {object} options - An optional set of configuration options.
         * @returns {promise} A JQuery promise, which resolves with the HTML of the rendered section
         *     fails with an error message.
         */
        studentInfo: function(studentUsername, options) {
            var url = this.url('render_student_info');
            return $.Deferred(function(defer) {
                $.ajax({
                    url: url,
                    type: "POST",
                    dataType: "html",
                    data: _.extend({student_username: studentUsername}, options)
                }).done(function(data) {
                    defer.resolveWith(this, [data]);
                }).fail(function() {
                    defer.rejectWith(this, [gettext('This section could not be loaded.')]);
                });
            }).promise();
        },

        /**
         * Renders the next submission for staff grading.
         *
         * @returns {promise} A JQuery promise, which resolves with the HTML of the rendered section
         *     fails with an error message.
         */
        staffGradeForm: function() {
            var url = this.url('render_staff_grade_form');
            return $.Deferred(function(defer) {
                $.ajax({
                    url: url,
                    type: "POST",
                    dataType: "html"
                }).done(function(data) {
                    defer.resolveWith(this, [data]);
                }).fail(function() {
                    defer.rejectWith(this, [gettext('The staff assessment form could not be loaded.')]);
                });
            }).promise();
        },

        /**
         * Renders the count of ungraded and checked out assessemtns.
         *
         * @returns {promise} A JQuery promise, which resolves with the HTML of the rendered section
         *     fails with an error message.
         */
        staffGradeCounts: function() {
            var url = this.url('render_staff_grade_counts');
            return $.Deferred(function(defer) {
                $.ajax({
                    url: url,
                    type: "POST",
                    dataType: "html"
                }).done(function(data) {
                    defer.resolveWith(this, [data]);
                }).fail(function() {
                    defer.rejectWith(
                        this, [gettext('The display of ungraded and checked out responses could not be loaded.')]
                    );
                });
            }).promise();
        },

        /**
         * Send a submission to the XBlock.
         *
         * @param {string} submission The text of the student's submission.
         * @returns {promise} A JQuery promise, which resolves with the student's ID
         * and attempt number if the call was successful and fails with a status code
         * and error message otherwise.
         */
        submit: function(submission) {
            var url = this.url('submit');
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST",
                    url: url,
                    data: JSON.stringify({submission: submission}),
                    contentType: jsonContentType
                }).done(function(data) {
                    var success = data[0];
                    if (success) {
                        var studentId = data[1];
                        var attemptNum = data[2];
                        defer.resolveWith(this, [studentId, attemptNum]);
                    }
                    else {
                        var errorNum = data[1];
                        var errorMsg = data[2];
                        defer.rejectWith(this, [errorNum, errorMsg]);
                    }
                }).fail(function() {
                    defer.rejectWith(this, ["AJAX", gettext("This response could not be submitted.")]);
                });
            }).promise();
        },

        /**
         * Save a response without submitting it.
         *
         * @param {string} submission The text of the student's response.
         * @returns {promise} A JQuery promise, which resolves with no arguments on success and
         *      fails with an error message.
         */
        save: function(submission) {
            var url = this.url('save_submission');
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST",
                    url: url,
                    data: JSON.stringify({submission: submission}),
                    contentType: jsonContentType
                }).done(function(data) {
                    if (data.success) { defer.resolve(); }
                    else { defer.rejectWith(this, [data.msg]); }
                }).fail(function() {
                    defer.rejectWith(this, [gettext("This response could not be saved.")]);
                });
            }).promise();
        },

        /**
         * Submit feedback on assessments to the XBlock.
         *
         * @param {string} text written feedback from the student.
         * @param {Array.string} options one or more options the student selected.
         * @returns {promise} A JQuery promise, which resolves with no args if successful and
         *     fails with an error message otherwise.
         */
        submitFeedbackOnAssessment: function(text, options) {
            var url = this.url('submit_feedback');
            var payload = JSON.stringify({
                'feedback_text': text,
                'feedback_options': options
            });
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST", url: url, data: payload, contentType: jsonContentType
                }).done(function(data) {
                    if (data.success) { defer.resolve(); }
                    else { defer.rejectWith(this, [data.msg]); }
                }).fail(function() {
                    defer.rejectWith(this, [gettext('This feedback could not be submitted.')]);
                });
            }).promise();
        },

        /**
         * Submits an assessment.
         *
         * @param {string} assessmentType - The type of assessment.
         * @param {object} payload - The assessment payload
         * @returns {promise} A promise which resolves with no arguments if successful,
         *     and which fails with an error message otherwise.
         */
        submitAssessment: function(assessmentType, payload) {
            var url = this.url(assessmentType);
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST", url: url, data: JSON.stringify(payload), contentType: jsonContentType
                }).done(function(data) {
                    if (data.success) {
                        defer.resolve();
                    }
                    else {
                        defer.rejectWith(this, [data.msg]);
                    }
                }).fail(function() {
                    defer.rejectWith(this, [gettext('This assessment could not be submitted.')]);
                });
            }).promise();
        },

        /**
         * Send a peer assessment to the XBlock.
         *
         * @param {object} optionsSelected - The options selected as a dict,
         *     e.g. { clarity: "Very clear", precision: "Somewhat precise" }
         * @param {object} criterionFeedback - Feedback on the criterion,
         *     e.g. { clarity: "The essay was very clear." }
         * @param {string} overallFeedback - A string with the staff member's overall feedback.
         * @param {string} submissionID - The ID of the submission being assessed.
         * @returns {promise} A promise which resolves with no arguments if successful,
         *     and which fails with an error message otherwise.
         */
        peerAssess: function(optionsSelected, criterionFeedback, overallFeedback, submissionID, trackChangesEdits) {
            return this.submitAssessment("peer_assess", {
                options_selected: optionsSelected,
                criterion_feedback: criterionFeedback,
                overall_feedback: overallFeedback,
                submission_uuid: submissionID,
                track_changes_edits: trackChangesEdits
            });
        },

        /**
         * Send a self assessment to the XBlock.
         *
         * @param {object} optionsSelected - The options selected as a dict,
         *     e.g. { clarity: "Very clear", precision: "Somewhat precise" }
         * @param {object} criterionFeedback - Feedback on the criterion,
         *     e.g. { clarity: "The essay was very clear." }
         * @param {string} overallFeedback - A string with the staff member's overall feedback.
         * @returns {promise} A promise which resolves with no arguments if successful,
         *     and which fails with an error message otherwise.
         */
        selfAssess: function(optionsSelected, criterionFeedback, overallFeedback) {
            return this.submitAssessment("self_assess", {
                options_selected: optionsSelected,
                criterion_feedback: criterionFeedback,
                overall_feedback: overallFeedback
            });
        },

        /**
         * Send a staff assessment to the XBlock.
         *
         * @param {object} optionsSelected - The options selected as a dict,
         *     e.g. { clarity: "Very clear", precision: "Somewhat precise" }
         * @param {object} criterionFeedback - Feedback on the criterion,
         *     e.g. { clarity: "The essay was very clear." }
         * @param {string} overallFeedback - A string with the staff member's overall feedback.
         * @param {string} submissionID - The ID of the submission being assessed.
         * @param {string} assessType a string indicating whether this was a 'full-grade' or 'regrade'
         * @returns {promise} A promise which resolves with no arguments if successful,
         *     and which fails with an error message otherwise.
         */
        staffAssess: function(optionsSelected, criterionFeedback, overallFeedback, submissionID, assessType) {
            return this.submitAssessment("staff_assess", {
                options_selected: optionsSelected,
                criterion_feedback: criterionFeedback,
                overall_feedback: overallFeedback,
                submission_uuid: submissionID,
                assess_type: assessType
            });
        },

        /**
         * Submit an instructor-provided training example.
         *
         * @param {object} optionsSelected - The options selected as a dict,
         *     e.g. { clarity: "Very clear", precision: "Somewhat precise" }
         * @returns {promise} A promise which resolves with a list of corrections if successful,
         *     and which fails with an error message otherwise.
         */
        trainingAssess: function(optionsSelected) {
            var url = this.url('training_assess');
            var payload = JSON.stringify({
                options_selected: optionsSelected
            });
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST", url: url, data: payload, contentType: jsonContentType
                }).done(function(data) {
                    if (data.success) {
                        defer.resolveWith(this, [data.corrections]);
                    }
                    else {
                        defer.rejectWith(this, [data.msg]);
                    }
                }).fail(function() {
                    defer.rejectWith(this, [gettext('This assessment could not be submitted.')]);
                });
            });
        },

        /**
         * Schedules classifier training for Example Based Assessments.
         *
         * @returns {promise} A JQuery promise, which resolves with a
         * message indicating the results of the scheduling request.
         */
        scheduleTraining: function() {
            var url = this.url('schedule_training');
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST", url: url, data: "\"\"", contentType: jsonContentType
                }).done(function(data) {
                    if (data.success) {
                        defer.resolveWith(this, [data.msg]);
                    }
                    else {
                        defer.rejectWith(this, [data.msg]);
                    }
                }).fail(function() {
                    defer.rejectWith(this, [gettext('This assessment could not be submitted.')]);
                });
            });
        },

        /**
         * Reschedules grading tasks for example based assessments
         *
         * @returns {promise} a JQuery Promise which will resolve with a message indicating
         *     success or failure of the scheduling.
         */
        rescheduleUnfinishedTasks: function() {
            var url = this.url('reschedule_unfinished_tasks');
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST", url: url, data: "\"\"", contentType: jsonContentType
                }).done(function(data) {
                    if (data.success) {
                        defer.resolveWith(this, [data.msg]);
                    }
                    else {
                        defer.rejectWith(this, [data.msg]);
                    }
                }).fail(function() {
                    defer.rejectWith(this, [gettext('One or more rescheduling tasks failed.')]);
                });
            });
        },

        /**
         * Update the XBlock's XML definition on the server.
         *
         * @param {object} options - An object with the following options:
         *     title (string): The title of the problem.
         *     prompt (string): The question prompt.
         *     feedbackPrompt (string): The directions to the student for giving overall feedback on a submission.
         *     feedback_default_text (string): The default feedback text used as the student's feedback response
         *     submissionStart (ISO-formatted datetime string or null): The start date of the submission.
         *     submissionDue (ISO-formatted datetime string or null): The date the submission is due.
         *     criteria (list of object literals): The rubric criteria.
         *     assessments (list of object literals): The assessments the student will be evaluated on.
         *     fileUploadType (string): 'image' if image attachments are allowed, 'pdf-and-image' if pdf and
         *     image attachments are allowed, 'custom' if file type is restricted by a white list.
         *     fileTypeWhiteList (string): Comma separated file type white list
         *     latexEnabled: TRUE if latex rendering is enabled.
         *     leaderboardNum (int): The number of scores to show in the leaderboard.
         *
         * @returns {promise} A JQuery promise, which resolves with no arguments
         *     and fails with an error message.
         */
        updateEditorContext: function(options) {
            var url = this.url('update_editor_context');
            var payload = JSON.stringify({
                prompts: options.prompts,
                prompts_type: options.prompts_type,
                feedback_prompt: options.feedbackPrompt,
                feedback_default_text: options.feedback_default_text,
                title: options.title,
                submission_start: options.submissionStart,
                submission_due: options.submissionDue,
                criteria: options.criteria,
                assessments: options.assessments,
                editor_assessments_order: options.editorAssessmentsOrder,
                text_response: options.textResponse,
                file_upload_response: options.fileUploadResponse,
                file_upload_type: options.fileUploadType,
                white_listed_file_types: options.fileTypeWhiteList,
                allow_latex: options.latexEnabled,
                leaderboard_show: options.leaderboardNum
            });
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST", url: url, data: payload, contentType: jsonContentType
                }).done(function(data) {
                    if (data.success) { defer.resolve(); }
                    else { defer.rejectWith(this, [data.msg]); }
                }).fail(function() {
                    defer.rejectWith(this, [gettext('This problem could not be saved.')]);
                });
            }).promise();
        },

        /**
         * Check whether the XBlock has been released.
         *
         * @returns {promise} A JQuery promise, which resolves with a boolean indicating
         *     whether the XBlock has been released.  On failure, the promise provides
         *     an error message.
         */
        checkReleased: function() {
            var url = this.url('check_released');
            var payload = "\"\"";
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST", url: url, data: payload, contentType: jsonContentType
                }).done(function(data) {
                    if (data.success) { defer.resolveWith(this, [data.is_released]); }
                    else { defer.rejectWith(this, [data.msg]); }
                }).fail(function() {
                    defer.rejectWith(this, [gettext("The server could not be contacted.")]);
                });
            }).promise();
        },

        /**
         * Get an upload URL used to asynchronously post related files for the submission.
         *
         * @param {string} contentType The Content Type for the file being uploaded.
         * @param {string} filename The name of the file to be uploaded.
         * @param {string} filenum The number of the file to be uploaded.
         * @returns {promise} A promise which resolves with a presigned upload URL from the
         * specified service used for uploading files on success, or with an error message
         * upon failure.
         */
        getUploadUrl: function(contentType, filename, filenum) {
            var url = this.url('upload_url');
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST",
                    url: url,
                    data: JSON.stringify({contentType: contentType, filename: filename, filenum: filenum}),
                    contentType: jsonContentType
                }).done(function(data) {
                    if (data.success) { defer.resolve(data.url); }
                    else { defer.rejectWith(this, [data.msg]); }
                }).fail(function() {
                    defer.rejectWith(this, [gettext('Could not retrieve upload url.')]);
                });
            }).promise();
        },

        /**
         * Sends request to server to remove all uploaded files.
         */
        removeUploadedFiles: function() {
            var url = this.url('remove_all_uploaded_files');
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST",
                    url: url,
                    data: JSON.stringify({}),
                    contentType: jsonContentType
                }).done(function(data) {
                    if (data.success) { defer.resolve(); }
                    else { defer.rejectWith(this, [data.msg]); }
                }).fail(function() {
                    defer.rejectWith(this, [gettext('Server error.')]);
                });
            }).promise();
        },

        /**
         * Sends request to server to save descriptions for each uploaded file.
         */
        saveFilesDescriptions: function(descriptions) {
            var url = this.url('save_files_descriptions');
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST",
                    url: url,
                    data: JSON.stringify({descriptions: descriptions}),
                    contentType: jsonContentType
                }).done(function(data) {
                    if (data.success) { defer.resolve(); }
                    else { defer.rejectWith(this, [data.msg]); }
                }).fail(function() {
                    defer.rejectWith(this, [gettext('Server error.')]);
                });
            }).promise();
        },

        /**
         * Get a download url used to download related files for the submission.
         *
         * @param {string} filenum The number of the file to be downloaded.
         * @returns {promise} A promise which resolves with a temporary download URL for
         * retrieving documents from s3 on success, or with an error message upon failure.
         */
        getDownloadUrl: function(filenum) {
            var url = this.url('download_url');
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST", url: url, data: JSON.stringify({filenum: filenum}), contentType: jsonContentType
                }).done(function(data) {
                    if (data.success) { defer.resolve(data.url); }
                    else { defer.rejectWith(this, [data.msg]); }
                }).fail(function() {
                    defer.rejectWith(this, [gettext('Could not retrieve download url.')]);
                });
            }).promise();
        },

        /**
         * Cancel a submission from the peer grading pool.
         *
         * @param {object} submissionID - The id of the submission to be canceled.
         * @param {object} comments - The reason for canceling the submission.
         * @returns {*}
         */
        cancelSubmission: function(submissionID, comments) {
            var url = this.url('cancel_submission');
            var payload = JSON.stringify({
                submission_uuid: submissionID,
                comments: comments
            });
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST", url: url, data: payload, contentType: jsonContentType
                }).done(function(data) {
                    if (data.success) {
                        defer.resolveWith(this, [data.msg]);
                    }
                }).fail(function() {
                    defer.rejectWith(this, [gettext('The submission could not be removed from the grading pool.')]);
                });
            }).promise();
        },

        /**
         * Submit an event to the runtime for publishing.
         *
         * @param {object} eventName - the name of the event
         * @param {object} eventData - additional context data for the event
         */
        publishEvent: function(eventName, eventData) {
            eventData.event_name = eventName;
            var url = this.url('publish_event');
            var payload = JSON.stringify(eventData);
            $.ajax({
                type: "POST", url: url, data: payload, contentType: jsonContentType
            });
        }
    };
}
