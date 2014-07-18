/**
Tests for OA XBlock editing.
**/

describe("OpenAssessment.StudioView", function() {

    var runtime = {
        notify: function(type, data) {}
    };

    // Stub server that returns dummy data or reports errors.
    var StubServer = function() {
        this.updateError = false;
        this.isReleased = false;
        this.receivedData = null;
        this.successPromise = $.Deferred(function(defer) {
            defer.resolve();
        });
        this.errorPromise = $.Deferred(function(defer) {
            defer.rejectWith(this, ['Test error']);
        }).promise();

        this.updateEditorContext = function(kwargs) {
            if (this.updateError) {
                return this.errorPromise;
            }
            else {
                this.receivedData = kwargs;
                return this.successPromise;
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

    var EXPECTED_SERVER_DATA = {
        title: "The most important of all questions.",
        prompt: "How much do you like waffles?",
        feedbackPrompt: "",
        submissionStart: null,
        submissionDue: null,
        imageSubmissionEnabled: false,
        criteria: [
            {
                order_num: 0,
                label: "Criterion with two options",
                name: "52bfbd0eb3044212b809564866e77079",
                prompt: "Prompt for criterion with two options",
                feedback: "disabled",
                options: [
                    {
                        order_num: 0,
                        points: 1,
                        name: "85bbbecbb6a343f8a2146cde0e609ad0",
                        label: "Fair",
                        explanation: "Fair explanation"
                    },
                    {
                        order_num: 1,
                        points: 2,
                        name: "5936d5b9e281403ca123964055d4719a",
                        label: "Good",
                        explanation: "Good explanation"
                    }
                ]
            },
            {
                name: "d96bb68a69ee4ccb8f86c753b6924f75",
                label: "Criterion with no options",
                prompt: "Prompt for criterion with no options",
                order_num: 1,
                options: [],
                feedback: "required",
            },
            {
                name: "2ca052403b06424da714f7a80dfb954d",
                label: "Criterion with optional feedback",
                prompt: "Prompt for criterion with optional feedback",
                order_num: 2,
                feedback: "optional",
                options: [
                    {
                        order_num: 0,
                        points: 2,
                        name: "d7445661a89b4b339b9788cb7225a603",
                        label: "Good",
                        explanation: "Good explanation"
                    }
                ],
            }
        ],
        assessments: [
            {
                name: "peer-assessment",
                start: null,
                due: null,
                must_grade: 5,
                must_be_graded_by: 3
            },
            {
                name: "self-assessment",
                start: null,
                due: null
            }
        ],
        editorAssessmentsOrder: [
            "student-training",
            "peer-assessment",
            "self-assessment",
            "example-based-assessment"
        ]
    };

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

    it("sends the editor context to the server", function() {
        // Save the current state of the problem
        // (defined by the current state of the DOM),
        // and verify that the correct information was sent
        // to the server.  This depends on the HTML fixture
        // used for this test.
        view.save();

        // Top-level attributes
        expect(server.receivedData.title).toEqual(EXPECTED_SERVER_DATA.title);
        expect(server.receivedData.prompt).toEqual(EXPECTED_SERVER_DATA.prompt);
        expect(server.receivedData.feedbackPrompt).toEqual(EXPECTED_SERVER_DATA.feedbackPrompt);
        expect(server.receivedData.submissionStart).toEqual(EXPECTED_SERVER_DATA.submissionStart);
        expect(server.receivedData.submissionDue).toEqual(EXPECTED_SERVER_DATA.submissionDue);
        expect(server.receivedData.imageSubmissionEnabled).toEqual(EXPECTED_SERVER_DATA.imageSubmissionEnabled);

        // Criteria
        for (var criterion_idx = 0; criterion_idx < EXPECTED_SERVER_DATA.criteria.length; criterion_idx++) {
            var actual_criterion = server.receivedData.criteria[criterion_idx];
            var expected_criterion = EXPECTED_SERVER_DATA.criteria[criterion_idx];
            expect(actual_criterion).toEqual(expected_criterion);
        }

        // Assessments
        for (var asmnt_idx = 0; asmnt_idx < EXPECTED_SERVER_DATA.assessments.length; asmnt_idx++) {
            var actual_asmnt = server.receivedData.assessments[asmnt_idx];
            var expected_asmnt = EXPECTED_SERVER_DATA.assessments[asmnt_idx];
            expect(actual_asmnt).toEqual(expected_asmnt);
        }

        // Editor assessment order
        expect(server.receivedData.editorAssessmentsOrder).toEqual(EXPECTED_SERVER_DATA.editorAssessmentsOrder);
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

    it("displays an error when server reports an update XML error", function() {
        server.updateError = true;
        view.save();
        expect(runtime.notify).toHaveBeenCalledWith('error', {msg: 'Test error'});
    });

    it("displays the correct tab on initialization", function() {
        $(".oa_editor_tab", view.element).each(function(){
            if ($(this).attr('aria-controls') == "oa_prompt_editor_wrapper"){
                expect($(this).hasClass('ui-state-active')).toBe(true);
            } else {
                expect($(this).hasClass('ui-state-active')).toBe(false);
            }
        });
    });

    it("installs checkbox listeners with callback", function () {
        this.funct = function(){};

        spyOn(this, 'funct');

        var toggler = new OpenAssessment.ToggleControl(
            view.element,
            "#ai_assessment_description_closed",
            "#ai_assessment_settings_editor"
        );

        toggler.show();
        toggler.hide();
        expect(this.funct.calls.length).toEqual(0);

        toggler = new OpenAssessment.ToggleControl(
            view.element,
            "#ai_assessment_description_closed",
            "#ai_assessment_settings_editor",
            this.funct
        );

        toggler.show();
        toggler.hide();
        expect(this.funct.calls.length).toEqual(2);

    });
});
