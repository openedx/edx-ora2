/**
Tests for OpenAssessment prompt editing view.
**/

describe("OpenAssessment.EditPromptView", function() {

    var view = null;

    beforeEach(function() {
        // Load the DOM fixture
        loadFixtures('oa_edit.html');

        // Create the view
        var element = $("#oa_prompt_editor_wrapper").get(0);
        view = new OpenAssessment.EditPromptView(element);
    });

    it("sets and loads prompt text", function() {
        view.promptText("");
        expect(view.promptText()).toEqual("");
        view.promptText("This is a test prompt!");
        expect(view.promptText()).toEqual("This is a test prompt!");
    });
});
