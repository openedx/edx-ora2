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

    var testLoadXMLExamples = function(view) {
        var xml = "XML DEFINITIONS WOULD BE HERE";
        view.exampleDefinitions(xml);
        expect(view.description()).toEqual({ examples: xml });
    };

    beforeEach(function() {
        jasmine.getFixtures().fixturesPath = 'base/fixtures';
        loadFixtures('oa_edit.html');
    });


    describe("OpenAssessment.EditPeerAssessmentView", function() {
        var view = null;

        beforeEach(function() {
            var element = $("#oa_peer_assessment_editor").get(0);
            view = new OpenAssessment.EditPeerAssessmentView(element);
        });

        it("Enables and disables", function() { testEnableAndDisable(view); });

        it("Loads a description", function() {
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

        it("Handles default dates", function() {
            view.startDatetime("");
            view.dueDatetime("");
            expect(view.description().start).toBe(null);
            expect(view.description().due).toBe(null);
        });
    });

    describe("OpenAssessment.EditSelfAssessmentView", function() {
        var view = null;

        beforeEach(function() {
            var element = $("#oa_self_assessment_editor").get(0);
            view = new OpenAssessment.EditSelfAssessmentView(element);
        });

        it("Enables and disables", function() { testEnableAndDisable(view); });

        it("Loads a description", function() {
            view.startDatetime("2014-01-01", "00:00");
            view.dueDatetime("2014-03-04", "00:00");
            expect(view.description()).toEqual({
                start: "2014-01-01T00:00",
                due: "2014-03-04T00:00"
            });
        });

        it("Handles default dates", function() {
            view.startDatetime("", "");
            view.dueDatetime("", "");
            expect(view.description().start).toBe(null);
            expect(view.description().due).toBe(null);
        });
    });

    describe("OpenAssessment.EditStudentTrainingView", function() {
        var view = null;

        beforeEach(function() {
            var element = $("#oa_student_training_editor").get(0);
            view = new OpenAssessment.EditStudentTrainingView(element);
        });

        it("Enables and disables", function() { testEnableAndDisable(view); });
        it("Loads a description", function() { testLoadXMLExamples(view); });
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