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

        // Test a valid datetime
        datetimeControl.datetime("2014-04-05", "00:00");
        expect(view.validate()).toBe(true);
        expect(view.validationErrors()).toEqual([]);
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
                due: "2014-03-04T00:00"
            });
        });

        it("handles default dates", function() {
            view.startDatetime("");
            view.dueDatetime("");
            expect(view.description().start).toBe(null);
            expect(view.description().due).toBe(null);
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
    });

    describe("OpenAssessment.EditSelfAssessmentView", function() {
        var view = null;

        beforeEach(function() {
            var element = $("#oa_self_assessment_editor").get(0);
            view = new OpenAssessment.EditSelfAssessmentView(element);
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

        it("handles default dates", function() {
            view.startDatetime("", "");
            view.dueDatetime("", "");
            expect(view.description().start).toBe(null);
            expect(view.description().due).toBe(null);
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
    });

    describe("OpenAssessment.EditStudentTrainingView", function() {
        var view = null;

        beforeEach(function() {
            var element = $("#oa_student_training_editor").get(0);
            view = new OpenAssessment.EditStudentTrainingView(element);
        });

        it("enables and disables", function() { testEnableAndDisable(view); });
        it("loads a description", function () {
            // This assumes a particular structure of the DOM,
            // which is set by the HTML fixture.
            var examples = view.exampleContainer.getItemValues();
            expect(examples.length).toEqual(0);
        });
        it("modifies a description", function () {
            view.exampleContainer.add();
            var examples = view.exampleContainer.getItemValues();
            expect(examples.length).toEqual(1);
        });
        it("returns the correct format", function () {
            view.exampleContainer.add();
            var examples = view.exampleContainer.getItemValues();
            expect(examples).toEqual(
                [
                    {
                        answer: "",
                        options_selected: []
                    }
                ]
            );
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
    });
});
