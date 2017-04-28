/**
Tests for the edit settings view.
**/
describe("OpenAssessment.EditSettingsView", function() {

    var StubView = function(name, descriptionText) {
        this.name = name;
        this.isValid = true;

        var validationErrors = [];

        this.description = function() {
            return { dummy: descriptionText };
        };

        var _enabled = true;
        this.isEnabled = function(isEnabled) {
            if (typeof(isEnabled) !== "undefined") { this._enabled = isEnabled; }
            return this._enabled;
        };

        this.validate = function() {
            return this.isValid;
        };

        this.setValidationErrors = function(errors) { validationErrors = errors; };
        this.validationErrors = function() { return validationErrors; };
        this.clearValidationErrors = function() { validationErrors = []; };
    };

    var testValidateDate = function(datetimeControl, expectedError) {
        // Test an invalid datetime
        datetimeControl.datetime("invalid", "invalid");
        expect(view.validate()).toBe(false);
        expect(view.validationErrors()).toContain(expectedError);

        view.clearValidationErrors();

        // Test a valid datetime
        datetimeControl.datetime("2014-04-05", "00:00");
        expect(view.validate()).toBe(true);
        expect(view.validationErrors()).toEqual([]);
    };

    var view = null;
    var assessmentViews = null;
    var data = null;

    // The Peer and Self Editor ID's
    var PEER = "oa_peer_assessment_editor";
    var SELF = "oa_self_assessment_editor";
    var AI = "oa_ai_assessment_editor";
    var TRAINING = "oa_student_training_editor";
    var STAFF = "oa_staff_assessment_editor";

    beforeEach(function() {
        // Load the DOM fixture
        loadFixtures('oa_edit.html');

        // Create the stub assessment views
        assessmentViews = {};
        assessmentViews[SELF] = new StubView("self-assessment", "Self assessment description");
        assessmentViews[PEER] = new StubView("peer-assessment", "Peer assessment description");
        assessmentViews[AI] = new StubView("ai-assessment", "Example Based assessment description");
        assessmentViews[TRAINING] = new StubView("student-training", "Student Training description");
        assessmentViews[STAFF] = new StubView("staff-assessment", "Staff assessment description");

        // mock data from backend
        data = {
            FILE_EXT_BLACK_LIST: ['exe','app']
        };

        // Create the view
        var element = $("#oa_basic_settings_editor").get(0);
        view = new OpenAssessment.EditSettingsView(element, assessmentViews, data);
        view.submissionStart("2014-01-01", "00:00");
        view.submissionDue("2014-03-04", "00:00");
    });

    it("sets and loads display name", function() {
        view.displayName("");
        expect(view.displayName()).toEqual("");
        view.displayName("This is the name of the problem!");
        expect(view.displayName()).toEqual("This is the name of the problem!");
    });

    it("sets and loads the submission start/due dates", function() {
        view.submissionStart("2014-04-01", "12:34");
        expect(view.submissionStart()).toEqual("2014-04-01T12:34");

        view.submissionDue("2014-05-02", "12:34");
        expect(view.submissionDue()).toEqual("2014-05-02T12:34");
    });

    it("sets and loads the file upload state", function() {
        view.fileUploadResponseNecessity('optional', true);
        view.fileUploadType('image');
        expect(view.fileUploadType()).toBe('image');
        view.fileUploadType('pdf-and-image');
        expect(view.fileUploadType()).toBe('pdf-and-image');
        view.fileUploadType('custom');
        expect(view.fileUploadType()).toBe('custom');

        view.fileUploadResponseNecessity('', true);
        expect(view.fileUploadType()).toBe('');

        view.fileUploadResponseNecessity('required', true);
        expect(view.fileUploadType()).toBe('custom');
    });

    it("sets and loads the file type white list", function() {
        view.fileTypeWhiteList('pdf,gif,png,doc');
        expect(view.fileTypeWhiteList()).toBe('pdf,gif,png,doc');

        view.fileTypeWhiteList('');
        expect(view.fileTypeWhiteList()).toBe('');
    });

    it("sets and loads the leaderboard number", function() {
        view.leaderboardNum(18);
        expect(view.leaderboardNum()).toEqual(18);

        view.leaderboardNum(0);
        expect(view.leaderboardNum()).toEqual(0);
    });

    it("builds a description of enabled assessments", function() {
        // Depends on the template having an original order
        // of training --> peer --> self --> ai

        // Disable all assessments, and expect an empty description
        assessmentViews[PEER].isEnabled(false);
        assessmentViews[SELF].isEnabled(false);
        assessmentViews[AI].isEnabled(false);
        assessmentViews[TRAINING].isEnabled(false);
        assessmentViews[STAFF].isEnabled(false);
        expect(view.assessmentsDescription()).toEqual([]);

        // Enable the first assessment only
        assessmentViews[PEER].isEnabled(false);
        assessmentViews[SELF].isEnabled(true);
        assessmentViews[AI].isEnabled(false);
        assessmentViews[TRAINING].isEnabled(false);
        expect(view.assessmentsDescription()).toEqual([
            {
                name: "self-assessment",
                dummy: "Self assessment description"
            }
        ]);

        // Enable the second assessment only
        assessmentViews[PEER].isEnabled(true);
        assessmentViews[SELF].isEnabled(false);
        assessmentViews[AI].isEnabled(false);
        assessmentViews[TRAINING].isEnabled(false);
        expect(view.assessmentsDescription()).toEqual([
            {
                name: "peer-assessment",
                dummy: "Peer assessment description"
            }
        ]);

        // Enable both assessments
        assessmentViews[PEER].isEnabled(true);
        assessmentViews[SELF].isEnabled(true);
        assessmentViews[AI].isEnabled(false);
        assessmentViews[TRAINING].isEnabled(false);
        expect(view.assessmentsDescription()).toEqual([
            {
                name: "peer-assessment",
                dummy: "Peer assessment description"
            },
            {
                name: "self-assessment",
                dummy: "Self assessment description"
            }
        ]);
    });

    it("validates submission start datetime fields", function() {
        testValidateDate(
            view.startDatetimeControl,
            "Submission start is invalid"
        );
    });

    it("validates submission due datetime fields", function() {
        testValidateDate(
            view.dueDatetimeControl,
            "Submission due is invalid"
        );
    });

    it("validates the leaderboard number field", function() {
        // Valid value for the leaderboard number
        view.leaderboardNum(0);
        expect(view.validate()).toBe(true);
        expect(view.validationErrors()).toEqual([]);

        // Below the minimum
        view.leaderboardNum(-1);
        expect(view.validate()).toBe(false);
        expect(view.validationErrors()).toContain(
            "Leaderboard number is invalid"
        );

        // Clear validation errors
        view.clearValidationErrors();
        expect(view.validationErrors()).toEqual([]);

        // Valid, near the maximum
        view.leaderboardNum(100);
        expect(view.validate()).toBe(true);

        // Above the maximum
        view.leaderboardNum(101);
        expect(view.validate()).toBe(false);
    });

    it("validates assessment views", function() {
        // Simulate one of the assessment views being invalid
        assessmentViews[PEER].isValid = false;
        assessmentViews[PEER].setValidationErrors(["test error"]);
        assessmentViews[PEER].isEnabled(true);

        // Expect that the parent view is also invalid
        expect(view.validate()).toBe(false);
        expect(view.validationErrors()).toContain("test error");
    });

    it("validates only assessments that are enabled", function() {
        // Simulate one of the assessment views being invalid but disabled
        assessmentViews[PEER].isValid = false;
        assessmentViews[PEER].setValidationErrors(["test error"]);
        assessmentViews[PEER].isEnabled(false);

        // Spy on the assessment view's validate() method so we can
        // verify that it doesn't get called (thus marking the DOM)
        spyOn(assessmentViews[PEER], 'validate').and.callThrough();

        // Expect that the parent view is still valid
        expect(view.validate()).toBe(true);

        // Check that the assessment view didn't get a chance
        // to mark anything as invalid
        expect(assessmentViews[PEER].validate).not.toHaveBeenCalled();
    });

    it("validates file upload type and white list fields", function() {
        view.fileUploadResponseNecessity('optional', true);

        view.fileUploadType("image");
        expect(view.validate()).toBe(true);
        expect(view.validationErrors().length).toBe(0);

        // expect white list field is not empty when upload type is custom
        view.fileUploadType("custom");
        expect(view.validate()).toBe(false);
        expect(view.validationErrors()).toContain('File types can not be empty.');

        // expect white list field doesn't contain black listed exts
        view.fileUploadType("custom");
        view.fileTypeWhiteList("pdf, EXE, .app");
        expect(view.validate()).toBe(false);
        expect(view.validationErrors()).toContain('The following file types are not allowed: exe,app');
    })
});
