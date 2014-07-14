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
            name: "Criterion with two options",
            prompt: "Prompt for criterion with two options",
            order_num: 0,
            feedback: "disabled",
            options: [
                {
                    order_num: 0,
                    points: 1,
                    name: "Fair",
                    explanation: "Fair explanation"
                },
                {
                    order_num: 1,
                    points: 2,
                    name: "Good",
                    explanation: "Good explanation"
                }
            ],
        });

        // Criterion with no options, feedback required
        expect(criteria[1]).toEqual({
            name: "Criterion with no options",
            prompt: "Prompt for criterion with no options",
            order_num: 1,
            feedback: "required",
            options: []
        });

        // Criterion with one option, feeback optional
        expect(criteria[2]).toEqual({
            name: "Criterion with optional feedback",
            prompt: "Prompt for criterion with optional feedback",
            order_num: 2,
            feedback: "optional",
            options: [
                {
                    order_num: 0,
                    points: 2,
                    name: "Good",
                    explanation: "Good explanation"
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