/* JavaScript interface for interacting with server-side OpenAssessment XBlock */

/* Namespace for open assessment */
if (typeof OpenAssessment == "undefined" || !OpenAssessment) {
    OpenAssessment = {};
}


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

    /* 
     * Get maximum size of input
     */
    maxInputSize: 1024 * 64,    /* 64KB should be enough for anybody, right? ;^P */

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
                defer.rejectWith(this, ['This section could not be loaded.']);
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
                    defer.rejectWith(this, ['This section could not be loaded.']);
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
        if (submission.length > this.maxInputSize) {
            return $.Deferred(function(defer) {
                defer.rejectWith(this, ["submit", "This response is too long. Please shorten the response and try to submit it again."]);
            }).promise();
        }
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
                defer.rejectWith(this, ["AJAX", "This response could not be submitted."]);
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
        if (submission.length > this.maxInputSize) {
            return $.Deferred(function(defer) {
                defer.rejectWith(this, ["This response is too long. Please shorten the response and try to save it again."]);
            }).promise();
        }
        return $.Deferred(function(defer) {
            $.ajax({
                type: "POST",
                url: url,
                data: JSON.stringify({submission: submission})
            }).done(function(data) {
                if (data.success) { defer.resolve(); }
                else { defer.rejectWith(this, [data.msg]); }
            }).fail(function(data) {
                defer.rejectWith(this, ["This response could not be saved."]);
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
        if (text.length > this.maxInputSize) {
            return $.Deferred(function(defer) {
                defer.rejectWith(this, ["This feedback is too long. Please shorten your feedback and try to submit it again."]);
            }).promise();
        }
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
                defer.rejectWith(this, ['This feedback could not be submitted.']);
            });
        }).promise();
    },

    /**
    Send a peer assessment to the XBlock.
    Args:
        optionsSelected (object literal): Keys are criteria names,
            values are the option text the user selected for the criterion.
        feedback (string): Written feedback on the submission.

    Returns:
        A JQuery promise, which resolves with no args if successful
        and fails with an error message otherise.

    Example:
        var options = { clarity: "Very clear", precision: "Somewhat precise" };
        var feedback = "Good job!";
        server.peerAssess(options, feedback).done(
            function() { console.log("Success!"); }
        ).fail(
            function(errorMsg) { console.log(errorMsg); }
        );
    **/
    peerAssess: function(optionsSelected, feedback) {
        var url = this.url('peer_assess');
        if (feedback.length > this.maxInputSize) {
            return $.Deferred(function(defer) {
                defer.rejectWith(this, ["The comments on this assessment are too long. Please shorten your comments and try to submit them again."]);
            }).promise();
        }
        var payload = JSON.stringify({
            options_selected: optionsSelected,
            feedback: feedback
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
                defer.rejectWith(this, ['This assessment could not be submitted.']);
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
                defer.rejectWith(this, ['This assessment could not be submitted.']);
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
    loadXml: function() {
        var url = this.url('xml');
        return $.Deferred(function(defer) {
            $.ajax({
                type: "POST", url: url, data: "\"\""
            }).done(function(data) {
                if (data.success) { defer.resolveWith(this, [data.xml]); }
                else { defer.rejectWith(this, [data.msg]); }
            }).fail(function(data) {
                defer.rejectWith(this, ['This problem could not be loaded.']);
            });
        }).promise();
    },

    /**
    Update the XBlock's XML definition on the server.

    Returns:
        A JQuery promise, which resolves with no arguments
        and fails with an error message.

    Example usage:
        server.updateXml(xml).done(
            function() {}
        ).fail(
            function(err) { console.log(err); }
        );
    **/
    updateXml: function(xml) {
        var url = this.url('update_xml');
        var payload = JSON.stringify({xml: xml});
        return $.Deferred(function(defer) {
            $.ajax({
                type: "POST", url: url, data: payload
            }).done(function(data) {
                if (data.success) { defer.resolve(); }
                else { defer.rejectWith(this, [data.msg]); }
            }).fail(function(data) {
                defer.rejectWith(this, ['This problem could not be saved.']);
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
                defer.rejectWith(this, ["The server could not be contacted."]);
            });
        }).promise();
    }
};
