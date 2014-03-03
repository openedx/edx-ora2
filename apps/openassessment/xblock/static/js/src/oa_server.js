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
                defer.rejectWith(this, ['Could not contact server.']);
            })
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
                data: {submission: submission}
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
                defer.rejectWith(this, ["AJAX", "Could not contact server."]);
            })
        }).promise();
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
                defer.rejectWith(this, ['Could not contact server.']);
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
                if (data.success) { defer.resolve() }
                else { defer.rejectWith(this, [data.msg]); }
            }).fail(function(data) {
                defer.rejectWith(this, ['Could not contact server.']);
            });
        }).promise();
    }
};
