/**
Tests for the edit settings view.
**/
describe("OpenAssessment.EditSettingsView", function() {

    var StubView = function(name, descriptionText) {
        this.name = name;

        this.description = function() {
            return { dummy: descriptionText };
        };

        var _enabled = true;
        this.isEnabled = function(isEnabled) {
            if (typeof(isEnabled) !== "undefined") { this._enabled = isEnabled; }
            return this._enabled;
        };
    };

    var view = null;
    var assessmentViews = null;

    beforeEach(function() {
        // Load the DOM fixture
        loadFixtures('oa_edit.html');

        // Create the stub assessment views
        assessmentViews = {
            "oa_self_assessment_editor": new StubView("self-assessment", "Self assessment description"),
            "oa_peer_assessment_editor": new StubView("peer-assessment", "Peer assessment description"),
            "oa_ai_assessment_editor": new StubView("ai-assessment", "Example Based assessment description"),
            "oa_student_training_editor": new StubView("student-training", "Student Training description")
        };

        // Create the view
        var element = $("#oa_basic_settings_editor").get(0);
        view = new OpenAssessment.EditSettingsView(element, assessmentViews);

    });

    it("sets and loads display name", function() {
        view.displayName("");
        expect(view.displayName()).toEqual("");
        view.displayName("This is the name of the problem!");
        expect(view.displayName()).toEqual("This is the name of the problem!");
    });

    it("sets and loads the submission start/due dates", function() {
        view.submissionStart("", "");
        expect(view.submissionStart()).toBe(null);

        view.submissionStart("2014-04-01", "00:00");
        expect(view.submissionStart()).toEqual("2014-04-01T00:00");

        view.submissionDue("", "");
        expect(view.submissionDue()).toBe(null);

        view.submissionDue("2014-05-02", "00:00");
        expect(view.submissionDue()).toEqual("2014-05-02T00:00");
    });

    it("sets and loads the image enabled state", function() {
        view.imageSubmissionEnabled(true);
        expect(view.imageSubmissionEnabled()).toBe(true);
        view.imageSubmissionEnabled(false);
        expect(view.imageSubmissionEnabled()).toBe(false);
    });

    it("builds a description of enabled assessments", function() {
        // In this test we also verify that the mechansim that reads off of the DOM is correct, in that it gets
        // the right order of assessments, in addition to performing the correct calls.  Note that this test's
        // success depends on our Template having the original order (as it does in an unconfigured ORA problem)
        // of TRAINING -> PEER -> SELF -> AI

        // The Peer and Self Editor ID's
        var peerID = "oa_peer_assessment_editor";
        var selfID = "oa_self_assessment_editor";
        var aiID = "oa_ai_assessment_editor";
        var studentID = "oa_student_training_editor";

        // Disable all assessments, and expect an empty description
        assessmentViews[peerID].isEnabled(false);
        assessmentViews[selfID].isEnabled(false);
        assessmentViews[aiID].isEnabled(false);
        assessmentViews[studentID].isEnabled(false);
        expect(view.assessmentsDescription()).toEqual([]);

        // Enable the first assessment only
        assessmentViews[peerID].isEnabled(false);
        assessmentViews[selfID].isEnabled(true);
        assessmentViews[aiID].isEnabled(false);
        assessmentViews[studentID].isEnabled(false);
        expect(view.assessmentsDescription()).toEqual([
            {
                name: "self-assessment",
                dummy: "Self assessment description"
            }
        ]);

        // Enable the second assessment only
        assessmentViews[peerID].isEnabled(true);
        assessmentViews[selfID].isEnabled(false);
        assessmentViews[aiID].isEnabled(false);
        assessmentViews[studentID].isEnabled(false);
        expect(view.assessmentsDescription()).toEqual([
            {
                name: "peer-assessment",
                dummy: "Peer assessment description"
            }
        ]);

        // Enable both assessments
        assessmentViews[peerID].isEnabled(true);
        assessmentViews[selfID].isEnabled(true);
        assessmentViews[aiID].isEnabled(false);
        assessmentViews[studentID].isEnabled(false);
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
});
