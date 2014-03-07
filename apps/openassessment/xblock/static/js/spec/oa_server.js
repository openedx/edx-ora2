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

    it("informs the caller of an AJAX error when sending a submission", function() {
        stubAjax(false, null);
        var receivedMsg = null;
        server.save("Test").fail(function(errorMsg) { receivedMsg = errorMsg; });
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

    it("informs the caller of a server error when sending a peer assessment", function() {
        stubAjax(true, {success:false, msg:'Test error!'});

        var receivedMsg = null;
        var options = {clarity: "Very clear", precision: "Somewhat precise"}
        server.peerAssess("abc1234", options, "Excellent job!").fail(function(msg) {
            receivedMsg = msg;
        });

        expect(receivedMsg).toEqual("Test error!");
    });

    it("informs the caller of an AJAX error when sending a peer assessment", function() {
        stubAjax(false, null);

        var receivedMsg = null;
        var options = {clarity: "Very clear", precision: "Somewhat precise"}
        server.peerAssess("abc1234", options, "Excellent job!").fail(function(msg) {
            receivedMsg = msg;
        });

        expect(receivedMsg).toEqual("Could not contact server.");
    });
});
