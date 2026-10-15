import EditRubricView from 'studio/oa_edit_rubric';

/**
Tests for the rubric editing view.
**/
describe("OpenAssessment.EditRubricView", function() {

    // Use a stub notifier implementation that simply stores
    // the notifications it receives.
    var notifier = null;
    var StubNotifier = function() {
        this.notifications = [];
        this.notificationFired = function(name, data) {
            this.notifications.push({
                name: name,
                data: data
            });
        };
    };

    // Default fields provided by the test template
    const defaultFeedbackFields = {
        feedback_prompt: 'Feedback default prompt',
        feedback_default_text: 'Feedback default text',
    };

    const newRubricData = {
        "criteria": [
            {
                "label": "𝓒𝓸𝓷𝓬𝓲𝓼𝓮",
                "prompt": "How concise is it?",
                "feedback": "disabled",
                "options": [
                    {
                        "label": "ﻉซƈﻉɭɭﻉกՇ",
                        "points": 3,
                        "explanation": "Extremely concise",
                        "name": "0",  // Note that name isn't actually set, but used for compare
                        "order_num": 0
                    },
                    {
                        "label": "Ġööḋ",
                        "points": 2,
                        "explanation": "Concise",
                        "name": "1",
                        "order_num": 1
                    },
                    {
                        "label": "ק๏๏г",
                        "points": 1,
                        "explanation": "Wordy",
                        "name": "2",
                        "order_num": 2
                    }
                ],
                "name": "0",
                "order_num": 0
            },
        ],
        "feedback_prompt": "Feedback instruction ...",
        "feedback_default_text": "Feedback default text\n"
    }

    // Stub server that returns dummy data or reports errors.
    let server;
    const validRubricLocation = 'valid-rubric-location';
    const StubServer = function() {
        this.cloneRubric = (rubricLocation) => {
            return $.Deferred((defer) => {
                if(rubricLocation === validRubricLocation) {
                    defer.resolveWith(this, [newRubricData]);
                } else {
                    defer.rejectWith(this, ['error-msg'])
                }
            }).promise();
        };
    };

    var view = null;
    beforeEach(function() {
        loadFixtures('oa_edit.html');
        var el = $("#oa_rubric_editor_wrapper").get(0);
        notifier = new StubNotifier();
        server = new StubServer();
        view = new EditRubricView(el, notifier, server);
    });

    it("reads a criteria definition from the editor", function() {
        // This assumes a particular structure of the DOM,
        // which is set by the HTML fixture.
        var criteria = view.criteriaDefinition();
        expect(criteria.length).toEqual(3);

        // Criterion with two options, feedback disabled
        expect(criteria[0]).toEqual({
            name: "criterion_1",
            label: "Criterion with two options",
            prompt: "Prompt for criterion with two options",
            order_num: 0,
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
            ],
        });

        // Criterion with no options, feedback required
        expect(criteria[1]).toEqual({
            name: "criterion_2",
            label: "Criterion with no options",
            prompt: "Prompt for criterion with no options",
            order_num: 1,
            feedback: "required",
            options: []
        });

        // Criterion with one option, feeback optional
        expect(criteria[2]).toEqual({
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
            ]
        });
    });

    it("creates new criteria and options", function() {
        // Delete all existing criteria from the rubric
        // Then add new criteria (created from a client-side template)
        $.each(view.getAllCriteria(), function() { view.removeCriterion(this); });
        view.addCriterion();
        view.addCriterion();

        // Add an option to the second criterion
        view.addOption(1);

        // Since no criteria/option names are set, leave them out of the description.
        // This will cause the server to assign them unique names.
        var criteria = view.criteriaDefinition();
        expect(criteria.length).toEqual(2);

        expect(criteria[0]).toEqual({
            order_num: 0,
            name: "0",
            label: "",
            prompt: "",
            feedback: "disabled",
            options: []
        });

        expect(criteria[1]).toEqual({
            name: "1",
            order_num: 1,
            label: "",
            prompt: "",
            feedback: "disabled",
            options: [
                {
                    label: "",
                    points: 1,
                    explanation: "",
                    name: "0",
                    order_num: 0
                }
            ]
        });
    });

    it("reads the feedback prompt from the editor", function() {
        view.feedbackPrompt("");
        expect(view.feedbackPrompt()).toEqual("");

        var prompt = "How do you think the student did overall?";
        view.feedbackPrompt(prompt);
        expect(view.feedbackPrompt()).toEqual(prompt);
    });

    it("fires a notification when an option is added", function() {
        view.addOption();
        expect(notifier.notifications).toContain({
            name: "optionAdd",
            data: {
                criterionName: 'criterion_1',
                criterionLabel: 'Criterion with two options',
                name:'0',
                label: '',
                points : 1
            }
        });

        // Add a second option and ensure that it is given a unique name
        view.addOption();
        expect(notifier.notifications).toContain({
            name: "optionAdd",
            data: {
                criterionName: 'criterion_1',
                criterionLabel: 'Criterion with two options',
                name:'1',
                label: '',
                points : 1
            }
        });
    });

    it("fires a notification when an option is removed", function() {
        view.removeOption(0, view.getOptionItem(0, 0));
        expect(notifier.notifications).toContain({
            name: "optionRemove",
            data: {
                criterionName: 'criterion_1',
                name: 'option_1'
            }
        });
    });

    it("fires a notification when an option's label or points are updated", function() {
        // Simulate what happens when the options label or points are updated
        view.getOptionItem(0, 0).updateHandler();
        expect(notifier.notifications).toContain({
            name: "optionUpdated",
            data: {
                criterionName: 'criterion_1',
                name: 'option_1',
                label: 'Fair',
                points: 1
            }
        });
    });

    it("fires a notification when a criterion's label is updated", function() {
        // Simulate what happens when a criterion label is updated
        view.getCriterionItem(0).updateHandler();
        expect(notifier.notifications).toContain({
            name: "criterionUpdated",
            data: {
                criterionName: 'criterion_1',
                criterionLabel: 'Criterion with two options'
            }
        });

    });

    it("fires a notification when a criterion is removed", function() {
        view.criteriaContainer.remove(view.getCriterionItem(0));
        expect(notifier.notifications).toContain({
            name: "criterionRemove",
            data: {criterionName : 'criterion_1'}
        });
    });

    it("validates option points", function() {
        // Test that a particular value is marked as valid/invalid
        var testValidateOptionPoints = function(value, isValid) {
            var option = view.getOptionItem(0, 0);
            option.points(value);
            expect(view.validate()).toBe(isValid);
        };

        // Invalid option point values
        testValidateOptionPoints("", false);
        testValidateOptionPoints("123abcd", false);
        testValidateOptionPoints("-1", false);
        testValidateOptionPoints("1000", false);
        testValidateOptionPoints("0.5", false);

        // Valid option point values
        testValidateOptionPoints("0", true);
        testValidateOptionPoints("1", true);
        testValidateOptionPoints("2", true);
        testValidateOptionPoints("998", true);
        testValidateOptionPoints("999", true);
    });

    it("validates the criterion prompt field", function() {
        // Filled in prompt should be valid
        $.each(view.getAllCriteria(), function() {
            this.prompt("This is a prompt.");
        });
        expect(view.validate()).toBe(true);

        // Change one of the prompts to an empty string
        view.getCriterionItem(0).prompt("");

        // Now the view should be invalid
        expect(view.validate()).toBe(false);
        expect(view.validationErrors()).toContain("Criterion prompt is invalid.");

        // Clear validation errors
        view.clearValidationErrors();
        expect(view.validationErrors()).toEqual([]);
    });

    it("validates the number of criteria in the rubric", function() {
        // Starting with three criteria, we should be valid.
        expect(view.validate()).toBe(true);

        // Removes the rubric criteria
        $.each(view.getAllCriteria(), function() {
            view.removeCriterion(this);
        });

        // Now we should be invalid (# Criteria == 0)
        expect(view.validate()).toBe(false);
        expect(view.validationErrors()).toContain("The rubric must contain at least one criterion");

        view.clearValidationErrors();
        expect(view.validationErrors()).toEqual([]);

    });

    describe("clearRubric", () => {
        it('removes all rubric criteria', () => {
            // Given some existing criteria
            var criteria = view.criteriaDefinition();
            expect(criteria.length).toEqual(3);

            // When I call clearRubric
            view.clearRubric();

            // Then it removes all criteria
            criteria = view.criteriaDefinition();
            expect(criteria.length).toEqual(0);
        });

        it('clears the feedback prompt and default text', () => {
            // Given existing feedback prompt and default text
            expect(view.feedbackPrompt()).toEqual(defaultFeedbackFields['feedback_prompt']);
            expect(view.feedback_default_text()).toEqual(defaultFeedbackFields['feedback_default_text'])

            // When I clear the rubric
            view.clearRubric()

            // Then it clears feedback prompt/default text
            expect(view.feedbackPrompt()).toEqual('');
            expect(view.feedback_default_text()).toEqual('');
        });
    });

    describe("cloneRubric", () => {
        // stub setRubric
        beforeEach(() => {
            spyOn(view, 'setRubric').and.callFake(() => {});
            spyOn(view, 'displayRubricClonedMessage').and.callFake(() => {});
        });

        it('replaces the rubric when the request is successful', () => {
            // Given we try to clone a rubric
            // When the server request completes successfully
            view.cloneRubric(validRubricLocation);

            // Then we call the setRubric function with returned data
            expect(view.setRubric).toHaveBeenCalledWith(newRubricData);
            expect(view.displayRubricClonedMessage).toHaveBeenCalledWith(validRubricLocation);
        });

        it('alerts when the clone rubric request fails', () => {
            // Given we try to clone a rubric
            expect(view.alert.isVisible()).toBeFalsy();

            // When the server request fails
            view.cloneRubric('bad-rubric-location');

            // Then we do not attempt to clone the rubric
            expect(view.setRubric).not.toHaveBeenCalled();
            expect(view.displayRubricClonedMessage).not.toHaveBeenCalled();
            // and we surface error alert to Studio
            expect(view.alert.isVisible()).toBeTruthy();
        });
    })

    describe("setRubric", () => {
        it('updates feedback prompt and text', () => {
            // Given existing feedback prompt and default text
            expect(view.feedbackPrompt()).toEqual(defaultFeedbackFields['feedback_prompt']);
            expect(view.feedback_default_text()).toEqual(defaultFeedbackFields['feedback_default_text'])

            // When I clone data from another rubric
            view.setRubric(newRubricData);

            // Then it updates the feedback data
            expect(view.feedbackPrompt()).toEqual(newRubricData['feedback_prompt']);
            expect(view.feedback_default_text()).toEqual(newRubricData['feedback_default_text'])
        });

        it('updates criteria definitions', () => {
            // When I clone data from another rubric
            view.setRubric(newRubricData);

            // Then it updates the criteria (and options)
            expect(view.criteriaDefinition()).toEqual(newRubricData.criteria);
        })

        it('fires the \'rubricReplaced\' notification', () => {
            // When I successfully clone a rubric
            view.setRubric(newRubricData);

            // Then I should raise the 'rubricReplaced' notification
            // to alert student training examples to update
            expect(notifier.notifications).toContain({
                name: "rubricReplaced",
                data: {},
            });
        });
    });
});
