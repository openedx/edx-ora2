/**
Encapsulate interactions with OpenAssessment XBlock handlers.
**/

// Since the server is included by both LMS and Studio views,
// skip loading it the second time.
if (typeof OpenAssessment.Server == "undefined" || !OpenAssessment.Server) {

    /**
    Interface for server-side XBlock handlers.

    Args:
        runtime (Runtime): An XBlock runtime instance.
        element (DOM element): The DOM element representing this XBlock.

    Returns:
        OpenAssessment.Server
    **/
    OpenAssessment.Server = function(runtime, element) {
        this.runtime = runtime;
        this.element = element;
    };


    OpenAssessment.Server.prototype = {

        /**
        Construct the URL for the handler, specific to one instance of the XBlock on the page.

        Args:
            handler (string): The name of the XBlock handler.

        Returns:
            URL (string)
        **/
        url: function(handler) {
            return this.runtime.handlerUrl(this.element, handler);
        },

        /**
        Render the XBlock.

        Args:
            component (string): The component to render.

        Returns:
            A JQuery promise, which resolves with the HTML of the rendered XBlock
            and fails with an error message.

        Example:
            server.render('submission').done(
                function(html) { console.log(html); }
            ).fail(
                function(err) { console.log(err); }
            )
        **/
        render: function(component) {
            var that = this;
            var url = this.url('render_' + component);
            return $.Deferred(function(defer) {
                $.ajax({
                    url: url,
                    type: "POST",
                    dataType: "html"
                }).done(function(data) {
                    defer.resolveWith(this, [data]);
                    that.renderLatex(data);
                }).fail(function(data) {
                    defer.rejectWith(this, [gettext('This section could not be loaded.')]);
                });
            }).promise();
        },

        /**
        Render Latex for all new DOM elements with class 'allow--latex'.

        Args:
            element: The element to modify.
        **/
        renderLatex: function(element) {
            $('.allow--latex', element).each(
                function() {
                    MathJax.Hub.Queue(['Typeset', MathJax.Hub, this]);
                }
            );
        },

        /**
         Render the Peer Assessment Section after a complete workflow, in order to
         continue grading peers.

         Returns:
            A JQuery promise, which resolves with the HTML of the rendered peer
            assessment section or fails with an error message.

         Example:
            server.render_continued_peer().done(
                function(html) { console.log(html); }
            ).fail(
                function(err) { console.log(err); }
            )
         **/
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
                        defer.resolveWith(this, [data]);
                        view.renderLatex(data);
                    }).fail(function(data) {
                        defer.rejectWith(this, [gettext('This section could not be loaded.')]);
                    });
            }).promise();
        },

        /**
         Load the Student Info section in Staff Info.
         **/
        studentInfo: function(student_id) {
            var url = this.url('render_student_info');
            return $.Deferred(function(defer) {
                $.ajax({
                    url: url,
                    type: "POST",
                    dataType: "html",
                    data: {student_id: student_id}
                }).done(function(data) {
                        defer.resolveWith(this, [data]);
                    }).fail(function(data) {
                        defer.rejectWith(this, [gettext('This section could not be loaded.')]);
                    });
            }).promise();
        },

        /**
        Send a submission to the XBlock.

        Args:
            submission (string): The text of the student's submission.

        Returns:
            A JQuery promise, which resolves with the student's ID and attempt number
            if the call was successful and fails with an status code and error message otherwise.
        **/
        submit: function(submission) {
            var url = this.url('submit');
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST",
                    url: url,
                    data: JSON.stringify({submission: submission})
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
                }).fail(function(data) {
                    defer.rejectWith(this, ["AJAX", gettext("This response could not be submitted.")]);
                });
            }).promise();
        },

        /**
        Save a response without submitting it.

        Args:
            submission (string): The text of the student's response.

        Returns:
            A JQuery promise, which resolves with no arguments on success and
            fails with an error message.
        **/
        save: function(submission) {
            var url = this.url('save_submission');
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST",
                    url: url,
                    data: JSON.stringify({submission: submission})
                }).done(function(data) {
                    if (data.success) { defer.resolve(); }
                    else { defer.rejectWith(this, [data.msg]); }
                }).fail(function(data) {
                    defer.rejectWith(this, [gettext("This response could not be saved.")]);
                });
            }).promise();
        },

        /**
         * Send feedback on assessments to the XBlock.
         * Args:
         *      text (string): Written feedback from the student.
         *      options (list of strings): One or more options the student selected.
         *
         * Returns:
         *      A JQuery promise, which resolves with no args if successful and
         *          fails with an error message otherwise.
         *
         * Example:
         *      server.submit_feedback(
         *          "Good feedback!", ["I liked the feedback I received"]
         *      ).done(function() {
         *          console.log("Success!");
         *      }).fail(function(errMsg) {
         *          console.log("Error: " + errMsg);
         *      });
         */
         submitFeedbackOnAssessment: function(text, options) {
            var url = this.url('submit_feedback');
            var payload = JSON.stringify({
                'feedback_text': text,
                'feedback_options': options
            });
            return $.Deferred(function(defer) {
                $.ajax({ type: "POST", url: url, data: payload }).done(
                    function(data) {
                        if (data.success) { defer.resolve(); }
                        else { defer.rejectWith(this, [data.msg]); }
                    }
                ).fail(function(data) {
                    defer.rejectWith(this, [gettext('This feedback could not be submitted.')]);
                });
            }).promise();
        },

        /**
        Send a peer assessment to the XBlock.
        Args:
            optionsSelected (object literal): Keys are criteria names,
                values are the option text the user selected for the criterion.
            criterionFeedback (object literal): Written feedback on a particular criterion,
                where keys are criteria names and values are the feedback strings.
            overallFeedback (string): Written feedback on the submission as a whole.

        Returns:
            A JQuery promise, which resolves with no args if successful
            and fails with an error message otherise.

        Example:
            var options = { clarity: "Very clear", precision: "Somewhat precise" };
            var criterionFeedback = { clarity: "The essay was very clear." };
            var overallFeedback = "Good job!";
            server.peerAssess(options, criterionFeedback, overallFeedback).done(
                function() { console.log("Success!"); }
            ).fail(
                function(errorMsg) { console.log(errorMsg); }
            );
        **/
        peerAssess: function(optionsSelected,
                            criterionFeedback,
                            overallFeedback,
                            trackChangesEdits) {
            var url = this.url('peer_assess');
            var payload = JSON.stringify({
                options_selected: optionsSelected,
                criterion_feedback: criterionFeedback,
                overall_feedback: overallFeedback,
                track_changes_edits: trackChangesEdits
            });
            return $.Deferred(function(defer) {
                $.ajax({ type: "POST", url: url, data: payload }).done(
                    function(data) {
                        if (data.success) {
                            defer.resolve();
                        }
                        else {
                            defer.rejectWith(this, [data.msg]);
                        }
                    }
                ).fail(function(data) {
                    defer.rejectWith(this, [gettext('This assessment could not be submitted.')]);
                });
            }).promise();
        },

        /**
        Send a self-assessment to the XBlock.

        Args:
            optionsSelected (object literal): Keys are criteria names,
                values are the option text the user selected for the criterion.
            var criterionFeedback = { clarity: "The essay was very clear." };
            var overallFeedback = "Good job!";

        Returns:
            A JQuery promise, which resolves with no args if successful
            and fails with an error message otherwise.

        Example:
            var options = { clarity: "Very clear", precision: "Somewhat precise" };
            server.selfAssess(options).done(
                function() { console.log("Success!"); }
            ).fail(
                function(errorMsg) { console.log(errorMsg); }
            );
        **/
        selfAssess: function(optionsSelected, criterionFeedback, overallFeedback) {
            var url = this.url('self_assess');
            var payload = JSON.stringify({
                options_selected: optionsSelected,
                criterion_feedback: criterionFeedback,
                overall_feedback: overallFeedback
            });
            return $.Deferred(function(defer) {
                $.ajax({ type: "POST", url: url, data: payload }).done(
                    function(data) {
                        if (data.success) {
                            defer.resolve();
                        }
                        else {
                            defer.rejectWith(this, [data.msg]);
                        }
                    }
                ).fail(function(data) {
                    defer.rejectWith(this, [gettext('This assessment could not be submitted.')]);
                });
            });
        },

        /**
        Assess an instructor-provided training example.

        Args:
            optionsSelected (object literal): Keys are criteria names,
                values are the option text the user selected for the criterion.

        Returns:
            A JQuery promise, which resolves with a list of corrections if
            successful and fails with an error message otherwise.

        Example:
            var options = { clarity: "Very clear", precision: "Somewhat precise" };
            server.trainingAssess(options).done(
                function(corrections) { console.log("Success!"); }
                alert(corrections);
            ).fail(
                function(errorMsg) { console.log(errorMsg); }
            );
        **/
        trainingAssess: function(optionsSelected) {
            var url = this.url('training_assess');
            var payload = JSON.stringify({
                options_selected: optionsSelected
            });
            return $.Deferred(function(defer) {
                $.ajax({ type: "POST", url: url, data: payload }).done(
                    function(data) {
                        if (data.success) {
                            defer.resolveWith(this, [data.corrections]);
                        }
                        else {
                            defer.rejectWith(this, [data.msg]);
                        }
                    }
                ).fail(function(data) {
                    defer.rejectWith(this, [gettext('This assessment could not be submitted.')]);
                });
            });
        },

        /**
        Schedules classifier training for Example Based Assessment for this
        Location.

        Returns:
            A JQuery promise, which resolves with a message indicating the results
            of the scheduling request.

        Example:
            server.scheduleTraining().done(
                function(msg) { console.log("Success!"); }
                alert(msg);
            ).fail(
                function(errorMsg) { console.log(errorMsg); }
            );
        **/
        scheduleTraining: function() {
            var url = this.url('schedule_training');
            return $.Deferred(function(defer) {
                $.ajax({ type: "POST", url: url, data: "\"\""}).done(
                    function(data) {
                        if (data.success) {
                            defer.resolveWith(this, [data.msg]);
                        }
                        else {
                            defer.rejectWith(this, [data.msg]);
                        }
                    }
                ).fail(function(data) {
                        defer.rejectWith(this, [gettext('This assessment could not be submitted.')]);
                    });
            });
        },

        /**
        Reschedules grading tasks for example based assessments

        Returns:
            JQuery Promise which will resolve with a message indicating success or failure of the scheduling
        **/
        rescheduleUnfinishedTasks: function() {
            var url = this.url('reschedule_unfinished_tasks');
            return $.Deferred(function(defer) {
                $.ajax({ type: "POST", url: url, data: "\"\""}).done(
                    function(data) {
                        if (data.success) {
                            defer.resolveWith(this, [data.msg]);
                        }
                        else {
                            defer.rejectWith(this, [data.msg]);
                        }
                    }
                ).fail(function(data) {
                        defer.rejectWith(this, [gettext('One or more rescheduling tasks failed.')]);
                });
            });
        },

        /**
        Update the XBlock's XML definition on the server.

        Kwargs:
            title (string): The title of the problem.
            prompt (string): The question prompt.
            feedbackPrompt (string): The directions to the student for giving overall feedback on a submission.
            feedback_default_text (string): The default feedback text used as the student's feedback response
            submissionStart (ISO-formatted datetime string or null): The start date of the submission.
            submissionDue (ISO-formatted datetime string or null): The date the submission is due.
            criteria (list of object literals): The rubric criteria.
            assessments (list of object literals): The assessments the student will be evaluated on.
            imageSubmissionEnabled (boolean): TRUE if image attachments are allowed.
            latexEnabled: TRUE if latex rendering is enabled.
            leaderboardNum (int): The number of scores to show in the leaderboard.

        Returns:
            A JQuery promise, which resolves with no arguments
            and fails with an error message.

        **/
        updateEditorContext: function(kwargs) {
            var url = this.url('update_editor_context');
            var payload = JSON.stringify({
                prompt: kwargs.prompt,
                feedback_prompt: kwargs.feedbackPrompt,
                feedback_default_text: kwargs.feedback_default_text,
                title: kwargs.title,
                submission_start: kwargs.submissionStart,
                submission_due: kwargs.submissionDue,
                criteria: kwargs.criteria,
                assessments: kwargs.assessments,
                editor_assessments_order: kwargs.editorAssessmentsOrder,
                allow_file_upload: kwargs.imageSubmissionEnabled,
                allow_latex: kwargs.latexEnabled,
                leaderboard_show: kwargs.leaderboardNum
            });
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST", url: url, data: payload
                }).done(function(data) {
                    if (data.success) { defer.resolve(); }
                    else { defer.rejectWith(this, [data.msg]); }
                }).fail(function(data) {
                    defer.rejectWith(this, [gettext('This problem could not be saved.')]);
                });
            }).promise();
        },

        /**
        Check whether the XBlock has been released.

        Returns:
            A JQuery promise, which resolves with a boolean indicating
            whether the XBlock has been released.  On failure, the promise
            provides an error message.

        Example:
            server.checkReleased().done(
                function(isReleased) {}
            ).fail(
                function(errMsg) {}
            )
        **/
        checkReleased: function() {
            var url = this.url('check_released');
            var payload = "\"\"";
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST", url: url, data: payload
                }).done(function(data) {
                    if (data.success) { defer.resolveWith(this, [data.is_released]); }
                    else { defer.rejectWith(this, [data.msg]); }
                }).fail(function(data) {
                    defer.rejectWith(this, [gettext("The server could not be contacted.")]);
                });
            }).promise();
        },

        /**
         Get an upload url used to asynchronously post related files for the
         submission.

         Args:
            contentType (str): The Content Type for the file being uploaded.

         Returns:
            A presigned upload URL from the specified service used for uploading
            files.

         **/
        getUploadUrl: function(contentType) {
            var url = this.url('upload_url');
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST", url: url, data: JSON.stringify({contentType: contentType})
                }).done(function(data) {
                        if (data.success) { defer.resolve(data.url); }
                        else { defer.rejectWith(this, [data.msg]); }
                    }).fail(function(data) {
                        defer.rejectWith(this, [gettext('Could not retrieve upload url.')]);
                    });
            }).promise();
        },

        /**
         Get a download url used to download related files for the submission.

         Returns:
            A temporary download URL for retrieving documents from s3.

         **/
        getDownloadUrl: function() {
            var url = this.url('download_url');
            return $.Deferred(function(defer) {
                $.ajax({
                    type: "POST", url: url, data: JSON.stringify({})
                }).done(function(data) {
                        if (data.success) { defer.resolve(data.url); }
                        else { defer.rejectWith(this, [data.msg]); }
                    }).fail(function(data) {
                        defer.rejectWith(this, [gettext('Could not retrieve download url.')]);
                    });
            }).promise();
        }
    };
}
