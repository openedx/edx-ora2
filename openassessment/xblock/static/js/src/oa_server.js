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
        var url = this.url('render_' + component);
        return $.Deferred(function(defer) {
            $.ajax({
                url: url,
                type: "POST",
                dataType: "html"
            }).done(function(data) {
                defer.resolveWith(this, [data]);
            }).fail(function(data) {
                defer.rejectWith(this, [gettext('This section could not be loaded.')]);
            });
        }).promise();
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
        var url = this.url('render_peer_assessment');
        return $.Deferred(function(defer) {
            $.ajax({
                url: url,
                type: "POST",
                dataType: "html",
                data: {continue_grading: true}
            }).done(function(data) {
                    defer.resolveWith(this, [data]);
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
    peerAssess: function(optionsSelected, criterionFeedback, overallFeedback) {
        var url = this.url('peer_assess');
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
        }).promise();
    },

    /**
    Send a self-assessment to the XBlock.

    Args:
        optionsSelected (object literal): Keys are criteria names,
            values are the option text the user selected for the criterion.

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
    selfAssess: function(optionsSelected) {
        var url = this.url('self_assess');
        var payload = JSON.stringify({
            options_selected: optionsSelected
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
    Load the XBlock's XML definition from the server.

    Returns:
        A JQuery promise, which resolves with the XML definition
        and fails with an error message.

    Example:
        server.loadXml().done(
            function(xml) { console.log(xml); }
        ).fail(
            function(err) { console.log(err); }
        );
    **/
    loadEditorContext: function() {
        var url = this.url('editor_context');
        return $.Deferred(function(defer) {
            $.ajax({
                type: "POST", url: url, data: "\"\""
            }).done(function(data) {
                if (data.success) { defer.resolveWith(this, [
                    data.prompt, data.rubric, data.title, data.submission_start, data.submission_due, data.assessments
                ]); }
                else { defer.rejectWith(this, [data.msg]); }
            }).fail(function(data) {
                defer.rejectWith(this, [gettext('This problem could not be loaded.')]);
            });
        }).promise();
    },

    /**
    Update the XBlock's XML definition on the server.

    Return
        A JQuery promise, which resolves with no arguments
        and fails with an error message.

    Example usage:
        server.updateXml(xml).done(
            function() {}
        ).fail(
            function(err) { console.log(err); }
        );
    **/
    updateEditorContext: function(prompt, rubricXml, title, sub_start, sub_due, assessments) {
        var url = this.url('update_editor_context');
        var payload = JSON.stringify({
            'prompt': prompt,
            'rubric': rubricXml,
            'title': title,
            'submission_start': sub_start,
            'submission_due': sub_due,
            'assessments': assessments
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
    }
};
