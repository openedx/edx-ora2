/**
Tests for the rubric editing view.
**/
describe("OpenAssessment.EditRubricView", function() {

    var view = null;
    beforeEach(function() {
        jasmine.getFixtures().fixturesPath = 'base/fixtures';
        loadFixtures('oa_edit.html');

        var el = $("#oa_rubric_editor_wrapper").get(0);
        view = new OpenAssessment.EditRubricView(el);
    });

    it("reads a criteria definition from the editor", function() {
        // This assumes a particular structure of the DOM,
        // which is set by the HTML fixture.
        var criteria = view.criteriaDefinition();
        expect(criteria.length).toEqual(3);

        // Criterion with two options, feedback disabled
        expect(criteria[0]).toEqual({
            name: "52bfbd0eb3044212b809564866e77079",
            label: "Criterion with two options",
            prompt: "Prompt for criterion with two options",
            order_num: 0,
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
            ],
        });

        // Criterion with no options, feedback required
        expect(criteria[1]).toEqual({
            name: "d96bb68a69ee4ccb8f86c753b6924f75",
            label: "Criterion with no options",
            prompt: "Prompt for criterion with no options",
            order_num: 1,
            feedback: "required",
            options: []
        });

        // Criterion with one option, feeback optional
        expect(criteria[2]).toEqual({
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
            ]
        });
    });

    it("creates new criteria and options", function() {
        // Delete all existing criteria from the rubric
        // Then add new criteria (created from a client-side template)
        view.removeAllCriteria();
        view.addCriterion();
        view.addCriterion();

        // Add an option to the second criterion
        view.getCriterionItem(1).addOption();

        // Check the definition
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

});