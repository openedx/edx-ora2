/*
Tests for OA XBlock server interactions.
*/

describe("OpenAssessment.Server", function() {

    // Stub runtime implementation that returns the handler as the URL
    var runtime = {
        handlerUrl: function(element, handler) { return "/" + handler; }
    };

    var server = null;

    /**
    Stub AJAX requests.

    Args:
        success (bool): If true, return a promise that resolves;
            otherwise, return a promise that fails.

        responseData(object): Data to pass to the caller if the AJAX
            call completes successfully.
    **/
    var stubAjax = function(success, responseData) {
        spyOn($, 'ajax').andReturn(
            $.Deferred(function(defer) {
                if (success) { defer.resolveWith(this, [responseData]); }
                else { defer.reject(); }
           }).promise()
        );
    };

    var getHugeTestString = function() {
        var testStringSize = server.maxInputSize + 1;
        var testString = '';
        for (i = 0; i < (testStringSize); i++) { testString += 'x'; }
        return testString;
    }
    
    var getHugeStringError = function() {
        // return a string that can be used with .toContain()
        // "Response text is too large. Please reduce the size of your response and try to submit again.";
        return "text is too large"
    }

    beforeEach(function() {
        // Create the server
        // Since the runtime is a stub implementation that ignores the element passed to it,
        // we can set the element parameter to null.
        server = new OpenAssessment.Server(runtime, null);
    });

    it("renders the XBlock as HTML", function() {
        stubAjax(true, "<div>Open Assessment</div>");

        var loadedHtml = "";
        server.render('submission').done(function(html) {
            loadedHtml = html;
        });

        expect(loadedHtml).toEqual("<div>Open Assessment</div>");
        expect($.ajax).toHaveBeenCalledWith({
            url: '/render_submission', type: "POST", dataType: "html"
        });
    });

    it("sends a submission to the XBlock", function() {
        // Status, student ID, attempt number
        stubAjax(true, [true, 1, 2]);

        var receivedStudentId = null;
        var receivedAttemptNum = null;
        server.submit("This is only a test").done(
            function(studentId, attemptNum) {
                receivedStudentId = studentId;
                receivedAttemptNum = attemptNum;
            }
        );

        expect(receivedStudentId).toEqual(1);
        expect(receivedAttemptNum).toEqual(2);
        expect($.ajax).toHaveBeenCalledWith({
            url: '/submit',
            type: "POST",
            data: JSON.stringify({submission: "This is only a test"})
        });
    });

    it("saves a response submission", function() {
        stubAjax(true, {'success': true, 'msg': ''});
        var success = false;
        server.save("Test").done(function() { success = true; });
        expect(success).toBe(true);
        expect($.ajax).toHaveBeenCalledWith({
            url: "/save_submission",
            type: "POST",
            data: JSON.stringify({submission: "Test"})
        });
    });

    it("sends an assessment to the XBlock", function() {
        stubAjax(true, {success: true, msg: ''});

        var success = false;
        var options = {clarity: "Very clear", precision: "Somewhat precise"};
        server.peerAssess("abc1234", options, "Excellent job!").done(function() {
            success = true;
        });

        expect(success).toBe(true);
        expect($.ajax).toHaveBeenCalledWith({
            url: '/peer_assess',
            type: "POST",
            data: JSON.stringify({
                submission_uuid: "abc1234",
                options_selected: options,
                feedback: "Excellent job!"
            })
        });
    });

    it("Sends feedback on an assessment to the XBlock", function() {
        stubAjax(true, {success: true, msg: ''});

        var success = false;
        var options = ["Option 1", "Option 2"];
        server.submitFeedbackOnAssessment("test feedback", options).done(function() {
            success = true;
        });

        expect(success).toBe(true);
        expect($.ajax).toHaveBeenCalledWith({
            url: '/submit_feedback',
            type: "POST",
            data: JSON.stringify({
                feedback_text: "test feedback",
                feedback_options: options,
            })
        });
    });

    it("loads the XBlock's XML definition", function() {
        stubAjax(true, { success: true, xml: "<openassessment />" });

        var loadedXml = "";
        server.loadXml().done(function(xml) {
            loadedXml = xml;
        });

        expect(loadedXml).toEqual('<openassessment />');
        expect($.ajax).toHaveBeenCalledWith({
            url: '/xml', type: "POST", data: '""'
        });
    });

    it("updates the XBlock's XML definition", function() {
        stubAjax(true, { success: true });

        server.updateXml('<openassessment />');
        expect($.ajax).toHaveBeenCalledWith({
            url: '/update_xml', type: "POST",
            data: JSON.stringify({xml: '<openassessment />'})
        });
    });

    it("Checks whether the XBlock has been released", function() {
        stubAjax(true, { success: true, is_released: true });

        var receivedIsReleased = null;
        server.checkReleased().done(function(isReleased) {
            receivedIsReleased = isReleased;
        });

        expect(receivedIsReleased).toBe(true);
        expect($.ajax).toHaveBeenCalledWith({
            url: '/check_released', type: "POST", data: "\"\""
        });
    });

    it("informs the caller of an Ajax error when rendering as HTML", function() {
        stubAjax(false, null);

        var receivedMsg = "";
        server.render('submission').fail(function(msg) {
            receivedMsg = msg;
        });

        expect(receivedMsg).toEqual("Could not contact server.");
    });

    it("informs the caller of an Ajax error when sending a submission", function() {
        stubAjax(false, null);

        var receivedErrorCode = "";
        var receivedErrorMsg = "";
        server.submit('This is only a test.').fail(
            function(errorCode, errorMsg) {
                receivedErrorCode = errorCode;
                receivedErrorMsg = errorMsg;
            }
        );

        expect(receivedErrorCode).toEqual("AJAX");
        expect(receivedErrorMsg).toEqual("Could not contact server.");
    });

    it("confirms that very long submissions fail with an error without ajax", function() {
        var receivedErrorCode = "";
        var receivedErrorMsg = "";
        var testString = getHugeTestString();
        server.submit(testString).fail(
            function(errorCode, errorMsg) {
                receivedErrorCode = errorCode;
                receivedErrorMsg = errorMsg;
            }
        );
        expect(receivedErrorCode).toEqual("submit");
        expect(receivedErrorMsg).toContain(getHugeStringError());
    });

    it("informs the caller of an server error when sending a submission", function() {
        stubAjax(true, [false, "ENODATA", "Error occurred!"]);

        var receivedErrorCode = "";
        var receivedErrorMsg = "";
        server.submit('This is only a test.').fail(
            function(errorCode, errorMsg) {
                receivedErrorCode = errorCode;
                receivedErrorMsg = errorMsg;
            }
        );

        expect(receivedErrorCode).toEqual("ENODATA");
        expect(receivedErrorMsg).toEqual("Error occurred!");
    });

    it("confirms that very long saves fail with an error without ajax", function() {
        var receivedErrorMsg = "";
        var testString = getHugeTestString();
        server.save(testString).fail(
            function(errorMsg) { receivedErrorMsg = errorMsg; }
        );
        expect(receivedErrorMsg).toContain(getHugeStringError());
    });

    it("informs the caller of an AJAX error when sending a submission", function() {
        stubAjax(false, null);
        var receivedMsg = null;
        server.save("Test").fail(function(errorMsg) { receivedMsg = errorMsg; });
        expect(receivedMsg).toEqual('Could not contact server.');
    });

    it("informs the caller of an AJAX error when sending a self assessment", function() {
        stubAjax(false, null);
        var receivedMsg = null;
        server.selfAssess("Test").fail(function(errorMsg) { receivedMsg = errorMsg; });
        expect(receivedMsg).toEqual('Could not contact server.');
    });

    it("informs the caller of a server error when sending a submission", function() {
        stubAjax(true, {'success': false, 'msg': 'test error'});
        var receivedMsg = null;
        server.save("Test").fail(function(errorMsg) { receivedMsg = errorMsg; });
        expect(receivedMsg).toEqual('test error');
    });

    it("informs the caller of an Ajax error when loading XML", function() {
        stubAjax(false, null);

        var receivedMsg = null;
        server.loadXml().fail(function(msg) {
            receivedMsg = msg;
        });

        expect(receivedMsg).toEqual("Could not contact server.");
    });

    it("informs the caller of an Ajax error when updating XML", function() {
        stubAjax(false, null);

        var receivedMsg = null;
        server.updateXml('test').fail(function(msg) {
            receivedMsg = msg;
        });

        expect(receivedMsg).toEqual("Could not contact server.");
    });

    it("informs the caller of a server error when loading XML", function() {
        stubAjax(true, { success: false, msg: "Test error" });

        var receivedMsg = null;
        server.updateXml('test').fail(function(msg) {
            receivedMsg = msg;
        });

        expect(receivedMsg).toEqual("Test error");
    });

    it("informs the caller of a server error when updating XML", function() {
        stubAjax(true, { success: false, msg: "Test error" });

        var receivedMsg = null;
        server.loadXml().fail(function(msg) {
            receivedMsg = msg;
        });

        expect(receivedMsg).toEqual("Test error");
    });

    it("confirms that very long peer assessments fail with an error without ajax", function() {
        var options = {clarity: "Very clear", precision: "Somewhat precise"};
        var receivedErrorMsg = "";
        var testString = getHugeTestString();
        server.peerAssess("abc1234", options, testString).fail(
            function(errorMsg) {
                receivedErrorMsg = errorMsg;
            }
        );
        expect(receivedErrorMsg).toContain(getHugeStringError());
    });

    it("informs the caller of a server error when sending a peer assessment", function() {
        stubAjax(true, {success:false, msg:'Test error!'});

        var receivedMsg = null;
        var options = {clarity: "Very clear", precision: "Somewhat precise"};
        server.peerAssess("abc1234", options, "Excellent job!").fail(function(msg) {
            receivedMsg = msg;
        });

        expect(receivedMsg).toEqual("Test error!");
    });

    it("informs the caller of an AJAX error when sending a peer assessment", function() {
        stubAjax(false, null);

        var receivedMsg = null;
        var options = {clarity: "Very clear", precision: "Somewhat precise"};
        server.peerAssess("abc1234", options, "Excellent job!").fail(function(msg) {
            receivedMsg = msg;
        });

        expect(receivedMsg).toEqual("Could not contact server.");
    });

    it("informs the caller of an AJAX error when checking whether the XBlock has been released", function() {
        stubAjax(false, null);

        var receivedMsg = null;
        server.checkReleased().fail(function(errMsg) {
            receivedMsg = errMsg;
        });

        expect(receivedMsg).toEqual("Could not contact server.");

    });

    it("informs the caller of a server error when checking whether the XBlock has been released", function() {
        stubAjax(true, { success: false, msg: "Test error" });

        var receivedMsg = null;
        server.checkReleased().fail(function(errMsg) {
            receivedMsg = errMsg;
        });

        expect(receivedMsg).toEqual("Test error");
    });

    it("confirms that very long assessment feedback fails with an error without ajax", function() {
        var options = ["Option 1", "Option 2"];
        var receivedErrorMsg = "";
        var testString = getHugeTestString();
        server.submitFeedbackOnAssessment(testString, options).fail(
            function(errorMsg) {
                receivedErrorMsg = errorMsg;
            }
        );
        expect(receivedErrorMsg).toContain(getHugeStringError());
    });

    it("informs the caller of an AJAX error when sending feedback on submission", function() {
        stubAjax(false, null);

        var receivedMsg = null;
        var options = ["Option 1", "Option 2"];
        server.submitFeedbackOnAssessment("test feedback", options).fail(
            function(errMsg) { receivedMsg = errMsg; }
        );
        expect(receivedMsg).toEqual("Could not contact server.");
    });

    it("informs the caller of a server error when sending feedback on submission", function() {
        stubAjax(true, { success: false, msg: "Test error" });

        var receivedMsg = null;
        var options = ["Option 1", "Option 2"];
        server.submitFeedbackOnAssessment("test feedback", options).fail(
            function(errMsg) { receivedMsg = errMsg; }
        );
        expect(receivedMsg).toEqual("Test error");
    });
});
