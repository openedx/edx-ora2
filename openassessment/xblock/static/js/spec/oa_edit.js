/**
Tests for OA XBlock editing.
**/

describe("OpenAssessment.StudioView", function() {

    var runtime = {
        notify: function(type, data) {}
    };

    // Stub server that returns dummy data or reports errors.
    var StubServer = function() {
        this.loadError = false;
        this.updateError = false;
        this.promptBox = "";
        this.rubricXmlBox = "";
        this.titleField = "";
        this.submissionStartField = "";
        this.submissionDueField = "";
        this.assessmentsXmlBox = "";

        this.isReleased = false;

        this.errorPromise = $.Deferred(function(defer) {
            defer.rejectWith(this, ['Test error']);
        }).promise();

        this.loadEditorContext = function() {
            var prompt = this.promptBox;
            var rubric = this.rubricXmlBox;
            var settings = {
                title: this.titleField,
                submission_start: this.submissionStartField,
                submission_due: this.submissionDueField,
                assessments: this.assessmentsXmlBox
            };

            if (!this.loadError) {
                return $.Deferred(function(defer) {
                    defer.resolveWith(this, [prompt, rubric, settings]);
                }).promise();
            }
            else {
                return this.errorPromise;
            }
        };

        this.updateEditorContext = function(prompt, rubricXml, title, sub_start, sub_due, assessmentsXml) {
            if (!this.updateError) {
                this.promptBox = prompt;
                this.rubricXmlBox = rubricXml;
                this.titleField = title;
                this.submissionStartField = sub_start;
                this.submissionDueField = sub_due;
                this.assessmentsXmlBox = assessmentsXml;
                return $.Deferred(function(defer) {
                    defer.resolve();
                }).promise();
            }
            else {
                return this.errorPromise;
            }
        };

        this.checkReleased = function() {
            var server = this;
            return $.Deferred(function(defer) {
                defer.resolveWith(this, [server.isReleased]);
            }).promise();
        };
    };

    var server = null;
    var view = null;

    beforeEach(function() {

        // Load the DOM fixture
        jasmine.getFixtures().fixturesPath = 'base/fixtures';
        loadFixtures('oa_edit.html');

        // Create the stub server
        server = new StubServer();

        // Mock the runtime
        spyOn(runtime, 'notify');

        // Create the object under test
        var el = $('#openassessment-editor').get(0);
        view = new OpenAssessment.StudioView(runtime, el, server);
    });

    it("loads the editor context definition", function() {
        // Initialize the view
        view.load();

        // Expect that the XML definition(s) were loaded
        var rubric = view.rubricXmlBox.getValue();
        var prompt = view.promptBox.value;
        var assessments = view.assessmentsXmlBox.getValue()

        expect(prompt).toEqual('');
        expect(rubric).toEqual('');
        expect(assessments).toEqual('');
    });

    it("saves the Editor Context definition", function() {
        // Update the Context
        view.titleField.value = 'THIS IS THE NEW TITLE';

        // Save the updated editor definition
        view.save();

        // Expect the saving notification to start/end
        expect(runtime.notify).toHaveBeenCalledWith('save', {state: 'start'});
        expect(runtime.notify).toHaveBeenCalledWith('save', {state: 'end'});

        // Expect the server's context to have been updated
        expect(server.titleField).toEqual('THIS IS THE NEW TITLE');
    });

    it("confirms changes for a released problem", function() {
        // Simulate an XBlock that has been released
        server.isReleased = true;

        // Stub the confirmation step (avoid showing the dialog)
        spyOn(view, 'confirmPostReleaseUpdate').andCallFake(
            function(onConfirm) { onConfirm(); }
        );

        // Save the updated context
        view.save();

        // Verify that the user was asked to confirm the changes
        expect(view.confirmPostReleaseUpdate).toHaveBeenCalled();
    });

    it("cancels editing", function() {
        view.cancel();
        expect(runtime.notify).toHaveBeenCalledWith('cancel', {});
    });

    it("displays an error when server reports a load XML error", function() {
        server.loadError = true;
        view.load();
        expect(runtime.notify).toHaveBeenCalledWith('error', {msg: 'Test error'});
    });

    it("displays an error when server reports an update XML error", function() {
        server.updateError = true;
        view.save();
        expect(runtime.notify).toHaveBeenCalledWith('error', {msg: 'Test error'});
    });
});
