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

    var view = null;
    beforeEach(function() {
        loadFixtures('oa_edit.html');
        var el = $("#oa_rubric_editor_wrapper").get(0);
        notifier = new StubNotifier();
        view = new OpenAssessment.EditRubricView(el, notifier);
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
});
