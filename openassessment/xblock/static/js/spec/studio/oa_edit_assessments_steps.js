import EditAssessmentsStepsView from 'studio/oa_edit_assessments_steps';

/**
Tests for the edit assessments step view.
**/
describe("OpenAssessment.EditAssessmentsStepsView", function() {

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

        this.element = $('<div>', {id: name});

        this.validate = function() {
            return this.isValid;
        };

        this.setValidationErrors = function(errors) { validationErrors = errors; };
        this.validationErrors = function() { return validationErrors; };
        this.clearValidationErrors = function() { validationErrors = []; };
    };

    var view = null;
    var assessmentViews = null;

    // The Peer and Self Editor ID's
    var PEER = "oa_peer_assessment_editor";
    var SELF = "oa_self_assessment_editor";
    var TRAINING = "oa_student_training_editor";
    var STAFF = "oa_staff_assessment_editor";

    beforeEach(function() {
        // Load the DOM fixture
        loadFixtures('oa_edit.html');

        // Create the stub assessment views
        assessmentViews = {};
        assessmentViews[SELF] = new StubView("self-assessment", "Self assessment description");
        assessmentViews[PEER] = new StubView("peer-assessment", "Peer assessment description");
        assessmentViews[TRAINING] = new StubView("student-training", "Student Training description");
        assessmentViews[STAFF] = new StubView("staff-assessment", "Staff assessment description");

        // Create the view
        var element = $("#oa_basic_settings_editor").get(0);
        view = new EditAssessmentsStepsView(element, assessmentViews);
    });

    it("builds a description of enabled assessments", function() {
        // Depends on the template having an original order
        // of training --> peer --> self --> ai

        // Disable all assessments, and expect an empty description
        assessmentViews[PEER].isEnabled(false);
        assessmentViews[SELF].isEnabled(false);
        assessmentViews[TRAINING].isEnabled(false);
        assessmentViews[STAFF].isEnabled(false);
        expect(view.assessmentsDescription()).toEqual([]);

        // Enable the first assessment only
        assessmentViews[PEER].isEnabled(false);
        assessmentViews[SELF].isEnabled(true);
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

    it('can hide/show elements on the page', function() {
        var selector = $(assessmentViews[PEER].element);

        // element shown by default should return hidden = false
        expect(view.isHidden(selector)).toBe(false);

        // explicitly hiding an element should return hidden = true
        view.setHidden(selector, true);
        expect(view.isHidden(selector)).toBe(true);

        // explicitly showing an element should return hidden = false
        view.setHidden(selector, false);
        expect(view.isHidden(selector)).toBe(false);
    });

    it('treats hidden assessment types as unselected', function() {
        // Select all assessment types
        var allAssessmentTypes = [SELF, TRAINING, PEER, STAFF];
        allAssessmentTypes.forEach(function(type) {
            assessmentViews[type].isEnabled(true);
        });

        expect(view.assessmentsDescription().length).toBe(4);

        // Hide some assessments, but leave them enabled
        view.setHidden($(assessmentViews[SELF].element), true);
        view.setHidden($(assessmentViews[PEER].element), true);

        // "Saved" assessment types should be limited to visible types
        expect(view.assessmentsDescription().length).toBe(2);
    });
});
