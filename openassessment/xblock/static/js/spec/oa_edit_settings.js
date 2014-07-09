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
        jasmine.getFixtures().fixturesPath = 'base/fixtures';
        loadFixtures('oa_edit.html');

        // Create the stub assessment views
        assessmentViews = [
            new StubView("self-assessment", "Self assessment description"),
            new StubView("peer-assessment", "Peer assessment description")
        ];

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
        view.submissionStart("");
        expect(view.submissionStart()).toBe(null);

        view.submissionStart("2014-04-01T00:00.0000Z");
        expect(view.submissionStart()).toEqual("2014-04-01T00:00.0000Z");

        view.submissionDue("");
        expect(view.submissionDue()).toBe(null);

        view.submissionDue("2014-05-02T00:00.0000Z");
        expect(view.submissionDue()).toEqual("2014-05-02T00:00.0000Z");
    });

    it("sets and loads the image enabled state", function() {
        view.imageSubmissionEnabled(true);
        expect(view.imageSubmissionEnabled()).toBe(true);
        view.imageSubmissionEnabled(false);
        expect(view.imageSubmissionEnabled()).toBe(false);
    });

    it("builds a description of enabled assessments", function() {
        // Disable all assessments, and expect an empty description
        assessmentViews[0].isEnabled(false);
        assessmentViews[1].isEnabled(false);
        expect(view.assessmentsDescription()).toEqual([]);

        // Enable the first assessment only
        assessmentViews[0].isEnabled(true);
        assessmentViews[1].isEnabled(false);
        expect(view.assessmentsDescription()).toEqual([
            {
                name: "self-assessment",
                dummy: "Self assessment description"
            }
        ]);

        // Enable the second assessment only
        assessmentViews[0].isEnabled(false);
        assessmentViews[1].isEnabled(true);
        expect(view.assessmentsDescription()).toEqual([
            {
                name: "peer-assessment",
                dummy: "Peer assessment description"
            }
        ]);

        // Enable both assessments
        assessmentViews[0].isEnabled(true);
        assessmentViews[1].isEnabled(true);
        expect(view.assessmentsDescription()).toEqual([
            {
                name: "self-assessment",
                dummy: "Self assessment description"
            },
            {
                name: "peer-assessment",
                dummy: "Peer assessment description"
            }
        ]);
    });
});
