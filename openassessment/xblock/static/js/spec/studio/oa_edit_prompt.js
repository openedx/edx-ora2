/**
Tests for OpenAssessment prompt editing view.
**/

describe("OpenAssessment.EditPromptViews", function() {

    var view = null;

    beforeEach(function() {
        // Load the DOM fixture
        loadFixtures('oa_edit.html');

        // Create the view
        var element = $("#oa_prompt_editor_wrapper").get(0);
        view = new OpenAssessment.EditPromptsView(element);
    });

    it("reads prompts from the editor", function() {
        // This assumes a particular structure of the DOM,
        // which is set by the HTML fixture.
        var prompts = view.promptsDefinition();
        expect(prompts.length).toEqual(2);

        expect(prompts[0]).toEqual({
            "description": "How much do you like waffles?"
        });
    });

    it("creates new prompts", function() {
        // Delete all existing prompts
        // Then add new prompts (created from a client-side template)
        $.each(view.getAllPrompts(), function() { view.removePrompt(this); });
        view.addPrompt();
        view.addPrompt();
        view.addPrompt();

        var prompts = view.promptsDefinition();
        expect(prompts.length).toEqual(3);

        expect(prompts[0]).toEqual({
            description: ""
        });

        expect(prompts[1]).toEqual({
            description: ""
        });
    });

});
