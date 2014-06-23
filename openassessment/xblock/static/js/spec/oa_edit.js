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

        this.hasPeer = true;
        this.hasSelf = true;
        this.hasTraining = false;
        this.hasAI = false;

        this.peerMustGrade = 2;
        this.peerGradedBy = 3;
        this.peerStart = '';
        this.peerDue = '';

        this.selfStart = '';
        this.selfDue = '';

        this.aiTrainingExamplesCodeBox = "";
        this.studentTrainingExamplesCodeBox = "";

        this.isReleased = false;

        this.errorPromise = $.Deferred(function(defer) {
            defer.rejectWith(this, ['Test error']);
        }).promise();

        this.loadEditorContext = function() {
            var prompt = this.promptBox;
            var rubric = this.rubricXmlBox;
            var title = this.titleField;
            var submission_start = this.submissionStartField;
            var submission_due = this.submissionDueField;
            var assessments = [];
            if (this.hasTraining){
                assessments = assessments.concat({
                    "name": "student-training",
                    "examples": this.studentTrainingExamplesCodeBox
                });
            }
            if (this.hasPeer){
                assessments = assessments.concat({
                    "name": "peer-assessment",
                    "start": this.peerStart,
                    "due": this.peerDue,
                    "must_grade": this.peerMustGrade,
                    "must_be_graded_by": this.peerGradedBy
                });
            }
            if (this.hasSelf){
                assessments = assessments.concat({
                    "name": "self-assessment",
                    "start": this.selfStart,
                    "due": this.selfDue
                });
            }
            if (this.hasAI){
                assessments = assessments.concat({
                    "name": "example-based-assessment",
                    "examples": this.aiTrainingExamplesCodeBox
                });
            }

            if (!this.loadError) {
                return $.Deferred(function(defer) {
                    defer.resolveWith(this, [prompt, rubric, title, submission_start, submission_due, assessments]);
                }).promise();
            }
            else {
                return this.errorPromise;
            }
        };

        this.updateEditorContext = function(prompt, rubricXml, title, sub_start, sub_due, assessments) {
            if (!this.updateError) {
                this.promptBox = prompt;
                this.rubricXmlBox = rubricXml;
                this.titleField = title;
                this.submissionStartField = sub_start;
                this.submissionDueField = sub_due;

                this.hasPeer = false;
                this.hasSelf = false;
                this.hasAI = false;
                this.hasTraining = false;

                for (var i = 0; i < assessments.length; i++) {
                    var assessment = assessments[i];
                    if (assessment.name == 'peer-assessment') {
                        this.hasPeer = true;
                        this.peerMustGrade = assessment.must_grade;
                        this.peerGradedBy = assessment.must_be_graded_by;
                        this.peerStart = assessment.start;
                        this.peerDue = assessment.due;
                    } else if (assessment.name == 'self-assessment') {
                        this.hasSelf = true;
                        this.selfStart = assessment.start;
                        this.selfDue = assessment.due;
                    } else if (assessment.name == 'example-based-assessment') {
                        this.hasAI = true;
                        this.aiTrainingExamplesCodeBox = assessment.examples;
                    } else if (assessment.name == 'student-training') {
                        this.hasTraining = true;
                        this.studentTrainingExamplesCodeBox = assessment.examples;
                    }
                }
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

    var prompt = "How much do you like waffles?";
    var rubric =
        "<rubric>" +
        "<criterion>"+
        "<name>Proper Appreciation of Gravity</name>"+
        "<prompt>How much respect did the person give waffles?</prompt>"+
        "<option points=\"0\"><name>No</name><explanation>Not enough</explanation></option>"+
        "<option points=\"2\"><name>Yes</name><explanation>An appropriate Amount</explanation></option>"+
        "</criterion>"+
        "</rubric>";
    var title = "The most important of all questions.";
    var subStart = "";
    var subDue = "2014-10-1T10:00:00";
    var assessments = [
        {
            "name": "student-training",
            "examples":
                "<examples>"+
                "<example>" +
                "<answer>ẗëṡẗ äṅṡẅëṛ</answer>" +
                "<select criterion=\"Test criterion\" option=\"Yes\" />" +
                "<select criterion=\"Another test criterion\" option=\"No\" />" +
                "</example>" +
                "<example>" +
                "<answer>äṅöẗḧëṛ ẗëṡẗ äṅṡẅëṛ</answer>" +
                "<select criterion=\"Another test criterion\" option=\"Yes\" />" +
                "<select criterion=\"Test criterion\" option=\"No\" />" +
                "</example>"+
                "</examples>",
            "start": "",
            "due": ""
        },
        {
            "name": "peer-assessment",
            "must_grade": 5,
            "must_be_graded_by": 3,
            "start": "2014-10-04T00:00:00",
            "due": ""
        },
        {
            "name": "self-assessment",
            "start": "",
            "due": ""
        }
    ];

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

        expect(prompt).toEqual('');
        expect(rubric).toEqual('');
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

    it("full integration test for load and update_editor_context", function() {
        server.updateEditorContext(prompt, rubric, title, subStart, subDue, assessments);
        view.load();

        expect(view.promptBox.value).toEqual(prompt);
        expect(view.rubricXmlBox.getValue()).toEqual(rubric);
        expect(view.titleField.value).toEqual(title);
        expect(view.submissionStartField.value).toEqual(subStart);
        expect(view.submissionDueField.value).toEqual(subDue);
        expect(view.hasPeer.prop('checked')).toEqual(true);
        expect(view.hasSelf.prop('checked')).toEqual(true);
        expect(view.hasAI.prop('checked')).toEqual(false);
        expect(view.hasTraining.prop('checked')).toEqual(true);
        expect(view.peerMustGrade.prop('value')).toEqual('5');
        expect(view.peerGradedBy.prop('value')).toEqual('3');
        expect(view.peerDue.prop('value')).toEqual("");
        expect(view.selfStart.prop('value')).toEqual("");
        expect(view.selfDue.prop('value')).toEqual("");
        expect(view.aiTrainingExamplesCodeBox.getValue()).toEqual("");
        expect(view.studentTrainingExamplesCodeBox.getValue()).toEqual(assessments[0].examples);
        expect(view.peerStart.prop('value')).toEqual("2014-10-04T00:00:00");

        view.titleField.value = "This is the new title.";
        view.updateEditorContext();

        expect(server.titleField).toEqual("This is the new title.");
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
