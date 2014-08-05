/**
Tests for assessment editing views.
**/

describe("OpenAssessment edit assessment views", function() {

    var testEnableAndDisable = function(view) {
        view.isEnabled(false);
        expect(view.isEnabled()).toBe(false);
        view.isEnabled(true);
        expect(view.isEnabled()).toBe(true);
    };

    var testValidateDate = function(view, datetimeControl, expectedError) {
        // Test an invalid datetime
        datetimeControl.datetime("invalid", "invalid");
        expect(view.validate()).toBe(false);
        expect(view.validationErrors()).toContain(expectedError);

        // Clear validation errors (simulate re-saving)
        view.clearValidationErrors();

        // Test a valid datetime
        datetimeControl.datetime("2014-04-05", "00:00");
        expect(view.validate()).toBe(true);
        expect(view.validationErrors()).toEqual([]);
    };

    var testAlertOnDisable = function(view) {
        var alert = new OpenAssessment.ValidationAlert();
        expect(alert.isVisible()).toBe(false);

        // Set the assessment to enabled initially
        view.isEnabled(true);

        // Disable an assessment, which should display an alert
        view.toggleEnabled();
        expect(alert.isVisible()).toBe(true);

        // Enable an assessment, which dismisses the alert
        view.toggleEnabled();
        expect(alert.isVisible()).toBe(false);
    };

    var testLoadXMLExamples = function(view) {
        var xml = "XML DEFINITIONS WOULD BE HERE";
        view.exampleDefinitions(xml);
        expect(view.description()).toEqual({ examples_xml: xml });
    };

    beforeEach(function() {
        loadFixtures('oa_edit.html');
    });


    describe("OpenAssessment.EditPeerAssessmentView", function() {
        var view = null;

        beforeEach(function() {
            var element = $("#oa_peer_assessment_editor").get(0);
            view = new OpenAssessment.EditPeerAssessmentView(element);
            view.startDatetime("2014-01-01", "00:00");
            view.dueDatetime("2014-01-01", "00:00");
        });

        it("enables and disables", function() { testEnableAndDisable(view); });

        it("loads a description", function() {
            view.mustGradeNum(1);
            view.mustBeGradedByNum(2);
            view.startDatetime("2014-01-01", "00:00");
            view.dueDatetime("2014-03-04", "00:00");
            expect(view.description()).toEqual({
                must_grade: 1,
                must_be_graded_by: 2,
                start: "2014-01-01T00:00",
                due: "2014-03-04T00:00",
                track_changes: ""
            });
        });

        it("validates the start date and time", function() {
            testValidateDate(
                view, view.startDatetimeControl,
                "Peer assessment start is invalid"
            );
        });

        it("validates the due date and time", function() {
            testValidateDate(
                view, view.dueDatetimeControl,
                "Peer assessment due is invalid"
            );
        });

        it("validates the must grade field", function() {
            // Invalid value (not a number)
            view.mustGradeNum("123abc");
            expect(view.validate()).toBe(false);
            expect(view.validationErrors()).toContain("Peer assessment must grade is invalid");

            view.clearValidationErrors();

            // Valid value
            view.mustGradeNum("34");
            expect(view.validate()).toBe(true);
            expect(view.validationErrors()).toEqual([]);
        });

        it("validates the must be graded by field", function() {
            // Invalid value (not a number)
            view.mustBeGradedByNum("123abc");
            expect(view.validate()).toBe(false);
            expect(view.validationErrors()).toContain("Peer assessment must be graded by is invalid");

            view.clearValidationErrors();

            // Valid value
            view.mustBeGradedByNum("34");
            expect(view.validate()).toBe(true);
            expect(view.validationErrors()).toEqual([]);
        });

        it("shows an alert when disabled", function() { testAlertOnDisable(view); });
    });

    describe("OpenAssessment.EditSelfAssessmentView", function() {
        var view = null;

        beforeEach(function() {
            var element = $("#oa_self_assessment_editor").get(0);
            view = new OpenAssessment.EditSelfAssessmentView(element);
            view.startDatetime("2014-01-01", "00:00");
            view.dueDatetime("2014-01-01", "00:00");
        });

        it("enables and disables", function() { testEnableAndDisable(view); });

        it("loads a description", function() {
            view.startDatetime("2014-01-01", "00:00");
            view.dueDatetime("2014-03-04", "00:00");
            expect(view.description()).toEqual({
                start: "2014-01-01T00:00",
                due: "2014-03-04T00:00"
            });
        });

        it("validates the start date and time", function() {
            testValidateDate(
                view, view.startDatetimeControl,
                "Self assessment start is invalid"
            );
        });

        it("validates the due date and time", function() {
            testValidateDate(
                view, view.dueDatetimeControl,
                "Self assessment due is invalid"
            );
        });

        it("shows an alert when disabled", function() { testAlertOnDisable(view); });
    });

    describe("OpenAssessment.EditStudentTrainingView", function() {
        var view = null;

        beforeEach(function() {
            // We need to load the student-training specific editing view
            // so that the student training example template is properly initialized.
            loadFixtures('oa_edit_student_training.html');

            var element = $("#oa_student_training_editor").get(0);
            view = new OpenAssessment.EditStudentTrainingView(element);
        });

        it("enables and disables", function() { testEnableAndDisable(view); });
        it("loads a description", function () {
            // This assumes a particular structure of the DOM,
            // which is set by the HTML fixture.
            expect(view.description()).toEqual({
                examples: [
                    {
                        answer: 'Test answer',
                        options_selected: [
                            {
                                criterion: 'criterion_with_two_options',
                                option: 'option_1'
                            }
                        ]
                    }
                ]
            });
        });

        it("modifies a description", function () {
            view.exampleContainer.add();
            expect(view.description()).toEqual({
                examples: [
                    {
                        answer: 'Test answer',
                        options_selected: [
                            {
                                criterion: 'criterion_with_two_options',
                                option: 'option_1'
                            }
                        ]
                    },
                    {
                        answer: '',
                        options_selected: [
                            {
                                criterion: 'criterion_with_two_options',
                                option: ''
                            }
                        ]
                    }
                ]
            });
        });

        it("shows an alert when disabled", function() { testAlertOnDisable(view); });

        it("validates selected options", function() {
            // On page load, the examples should be valid
            expect(view.validate()).toBe(true);
            expect(view.validationErrors()).toEqual([]);

            // Add a new training example (default no option selected)
            view.exampleContainer.add();

            // Now there should be a validation error
            expect(view.validate()).toBe(false);
            expect(view.validationErrors()).toContain("Student training example is invalid.");

            // Clear validation errors
            view.clearValidationErrors();
            expect(view.validationErrors()).toEqual([]);
        });
    });

    describe("OpenAssessment.EditExampleBasedAssessmentView", function() {
        var view = null;

        beforeEach(function() {
            var element = $("#oa_ai_assessment_editor").get(0);
            view = new OpenAssessment.EditExampleBasedAssessmentView(element);
        });

        it("Enables and disables", function() { testEnableAndDisable(view); });
        it("Loads a description", function() { testLoadXMLExamples(view); });
        it("shows an alert when disabled", function() { testAlertOnDisable(view); });
    });
});
