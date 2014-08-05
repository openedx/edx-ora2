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
        submissionStart: "2014-01-02T12:15",
        submissionDue: "2014-10-01T04:53",
        imageSubmissionEnabled: false,
        leaderboardNum: 12,
        criteria: [
            {
                order_num: 0,
                label: "Criterion with two options",
                name: "criterion_1",
                prompt: "Prompt for criterion with two options",
                feedback: "disabled",
                options: [
                    {
                        order_num: 0,
                        points: 1,
                        name: "option_1",
                        label: "Fair",
                        explanation: "Fair explanation"
                    },
                    {
                        order_num: 1,
                        points: 2,
                        name: "option_2",
                        label: "Good",
                        explanation: "Good explanation"
                    }
                ]
            },
            {
                name: "criterion_2",
                label: "Criterion with no options",
                prompt: "Prompt for criterion with no options",
                order_num: 1,
                options: [],
                feedback: "required",
            },
            {
                name: "criterion_3",
                label: "Criterion with optional feedback",
                prompt: "Prompt for criterion with optional feedback",
                order_num: 2,
                feedback: "optional",
                options: [
                    {
                        order_num: 0,
                        points: 2,
                        name: "option_1",
                        label: "Good",
                        explanation: "Good explanation"
                    }
                ],
            }
        ],
        assessments: [
            {
                name: "peer-assessment",
                start: "2014-01-02T00:00",
                due: "2014-01-03T00:00",
                must_grade: 5,
                must_be_graded_by: 3,
                track_changes: ""
            },
            {
                name: "self-assessment",
                start: "2014-01-04T00:00",
                due: "2014-01-05T00:00"
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
        expect(server.receivedData.leaderboardNum).toEqual(EXPECTED_SERVER_DATA.leaderboardNum);

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

    it("displays an error when server reports an error", function() {
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

    it("validates fields before saving", function() {
        // Initially, there should not be a validation alert
        expect(view.alert.isVisible()).toBe(false);

        // Introduce a validation error (date field does format invalid)
        view.settingsView.submissionStart("Not a valid date!", "00:00");

        // Try to save the view
        view.save();

        // Since there was an invalid field, expect that data was NOT sent to the server.
        // Also expect that an error is displayed
        expect(server.receivedData).toBe(null);
        expect(view.alert.isVisible()).toBe(true);

        // Expect that individual fields were highlighted
        expect(view.validationErrors()).toContain(
            "Submission start is invalid"
        );

        // Fix the error and try to save again
        view.settingsView.submissionStart("2014-04-01", "00:00");
        view.save();

        // Expect that the validation errors were cleared
        // and that data was successfully sent to the server.
        expect(view.validationErrors()).toEqual([]);
        expect(view.alert.isVisible()).toBe(false);
        expect(server.receivedData).not.toBe(null);
    });
});
