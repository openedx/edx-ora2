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

    var PROMPT = "Hello this is the prompt yes.";

    var RUBRIC = '<rubric>'+
        '<criterion>'+
            '<name>𝓒𝓸𝓷𝓬𝓲𝓼𝓮</name>'+
            '<prompt>How concise is it?</prompt>'+
            '<option points="3">'+
                '<name>ﻉซƈﻉɭɭﻉกՇ</name>'+
                '<explanation>Extremely concise</explanation>'+
            '</option>'+
            '<option points="2">'+
                '<name>Ġööḋ</name>'+
                '<explanation>Concise</explanation>'+
            '</option>'+
            '<option points="1">'+
                '<name>ק๏๏г</name>'+
                '<explanation>Wordy</explanation>'+
            '</option>'+
        '</criterion>'+
    '</rubric>';

    var assessments = '<assessments>' +
        '<assessment name="peer-assessment" must_grade="1" must_be_graded_by="1" due="2000-01-02"/>' +
        '<assessment name="self-assessment" due="2000-01-8"/>' +
        '</assessments>';

    var SETTINGS = {
        title: 'This is the title.',
        submission_start: '2012-10-09T00:00:00',
        submission_due: '2015-10-10T00:00:00',
        assessments: assessments
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

    it("sends a peer-assessment to the XBlock", function() {
        stubAjax(true, {success: true, msg: ''});

        var success = false;
        var options = {clarity: "Very clear", precision: "Somewhat precise"};
        var criterionFeedback = {clarity: "This essay was very clear."};
        server.peerAssess(options, criterionFeedback, "Excellent job!").done(
            function() { success = true; }
        );

        expect(success).toBe(true);
        expect($.ajax).toHaveBeenCalledWith({
            url: '/peer_assess',
            type: "POST",
            data: JSON.stringify({
                options_selected: options,
                criterion_feedback: criterionFeedback,
                overall_feedback: "Excellent job!"
            })
        });
    });

    it("sends a training assessment to the XBlock", function() {
        stubAjax(true, {success: true, msg: '', correct: true});
        var success = false;
        var corrections = null;
        var options = {clarity: "Very clear", precision: "Somewhat precise"};
        server.trainingAssess(options).done(
            function(result) {
                success = true;
                corrections = result;
            }
        );

        expect(success).toBe(true);
        expect(corrections).toBeUndefined();
        expect($.ajax).toHaveBeenCalledWith({
            url: '/training_assess',
            type: "POST",
            data: JSON.stringify({
                options_selected: options
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

    it("loads the XBlock's Context definition", function() {
        stubAjax(true, { success: true, prompt: PROMPT, rubric: RUBRIC, settings: SETTINGS});

        var loadedPrompt = "";
        var loadedRubric = "";
        var loadedSettings = "";
        server.loadEditorContext().done(function(prompt, rubric, settings) {
            loadedPrompt = prompt;
            loadedRubric = rubric;
            loadedSettings = settings;
        });

        expect(loadedPrompt).toEqual(PROMPT);
        expect(loadedRubric).toEqual(RUBRIC);
        expect(loadedSettings).toEqual(SETTINGS);
        expect($.ajax).toHaveBeenCalledWith({
            url: '/editor_context', type: "POST", data: '""'
        });
    });

    it("updates the XBlock's Context definition", function() {
        stubAjax(true, { success: true });

        server.updateEditorContext(
            PROMPT, RUBRIC, SETTINGS.title, SETTINGS.submission_start, SETTINGS.submission_due, SETTINGS.assessments
        );
        expect($.ajax).toHaveBeenCalledWith({
            type: "POST", url: '/update_editor_context',
            data: JSON.stringify({prompt: PROMPT, rubric: RUBRIC, settings: SETTINGS})
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

        expect(receivedMsg).toContain("This section could not be loaded");
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
        expect(receivedErrorMsg).toContain("This response could not be submitted");
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

    it("informs the caller of an AJAX error when saving a submission", function() {
        stubAjax(false, null);
        var receivedMsg = null;
        server.save("Test").fail(function(errorMsg) { receivedMsg = errorMsg; });
        expect(receivedMsg).toContain('This response could not be saved');
    });

    it("informs the caller of an AJAX error when sending a self assessment", function() {
        stubAjax(false, null);
        var receivedMsg = null;
        server.selfAssess("Test").fail(function(errorMsg) { receivedMsg = errorMsg; });
        expect(receivedMsg).toContain('This assessment could not be submitted');
    });

    it("informs the caller of a server error when sending a submission", function() {
        stubAjax(true, {'success': false, 'msg': 'test error'});
        var receivedMsg = null;
        server.save("Test").fail(function(errorMsg) { receivedMsg = errorMsg; });
        expect(receivedMsg).toEqual('test error');
    });


    it("informs the caller of an Ajax error when loading the editor context", function() {
        stubAjax(false, null);

        var receivedMsg = null;
        server.loadEditorContext().fail(function(msg) {
            receivedMsg = msg;
        });

        expect(receivedMsg).toContain("This problem could not be loaded");
    });

    it("informs the caller of an Ajax error when updating the editor context", function() {
        stubAjax(false, null);

        var receivedMsg = null;
        server.updateEditorContext('prompt', 'rubric', 'title', 'start', 'due', 'assessments').fail(function(msg) {
            receivedMsg = msg;
        });

        expect(receivedMsg).toContain("This problem could not be saved");
    });

    it("informs the caller of a server error when loading the editor context", function() {
        stubAjax(true, { success: false, msg: "Test error" });

        var receivedMsg = null;
        server.updateEditorContext('prompt', 'rubric', 'title', 'start', 'due', 'assessments').fail(function(msg) {
            receivedMsg = msg;
        });

        expect(receivedMsg).toEqual("Test error");
    });

    it("informs the caller of a server error when updating the editor context", function() {
        stubAjax(true, { success: false, msg: "Test error" });

        var receivedMsg = null;
        server.loadEditorContext().fail(function(msg) {
            receivedMsg = msg;
        });

        expect(receivedMsg).toEqual("Test error");
    });

    it("informs the caller of a server error when sending a peer assessment", function() {
        stubAjax(true, {success:false, msg:'Test error!'});

        var receivedMsg = null;
        var options = {clarity: "Very clear", precision: "Somewhat precise"};
        server.peerAssess(options, {}, "Excellent job!").fail(function(msg) {
            receivedMsg = msg;
        });

        expect(receivedMsg).toEqual("Test error!");
    });

    it("informs the caller of an AJAX error when sending a peer assessment", function() {
        stubAjax(false, null);

        var receivedMsg = null;
        var options = {clarity: "Very clear", precision: "Somewhat precise"};
        server.peerAssess(options, {}, "Excellent job!").fail(function(msg) {
            receivedMsg = msg;
        });

        expect(receivedMsg).toContain("This assessment could not be submitted");
    });

    it("informs the caller of a server error when sending a training example assessment", function() {
        stubAjax(true, {success: false, msg: "Test error!"});
        var receivedMsg = null;
        var options = {clarity: "Very clear", precision: "Somewhat precise"};
        server.trainingAssess(options).fail(function(msg) {
            receivedMsg = msg;
        });
        expect(receivedMsg).toEqual("Test error!");
    });

    it("informs the caller of an AJAX error when sending a training example assessment", function() {
        stubAjax(false, null);

        var receivedMsg = null;
        var options = {clarity: "Very clear", precision: "Somewhat precise"};
        server.trainingAssess(options).fail(function(msg) {
            receivedMsg = msg;
        });

        expect(receivedMsg).toContain("This assessment could not be submitted");
    });

    it("informs the caller of an AJAX error when checking whether the XBlock has been released", function() {
        stubAjax(false, null);

        var receivedMsg = null;
        server.checkReleased().fail(function(errMsg) {
            receivedMsg = errMsg;
        });

        expect(receivedMsg).toContain("The server could not be contacted");

    });

    it("informs the caller of a server error when checking whether the XBlock has been released", function() {
        stubAjax(true, { success: false, msg: "Test error" });

        var receivedMsg = null;
        server.checkReleased().fail(function(errMsg) {
            receivedMsg = errMsg;
        });

        expect(receivedMsg).toEqual("Test error");
    });

    it("informs the caller of an AJAX error when sending feedback on submission", function() {
        stubAjax(false, null);

        var receivedMsg = null;
        var options = ["Option 1", "Option 2"];
        server.submitFeedbackOnAssessment("test feedback", options).fail(
            function(errMsg) { receivedMsg = errMsg; }
        );
        expect(receivedMsg).toContain("This feedback could not be submitted");
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
