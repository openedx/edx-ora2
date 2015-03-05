/**
Tests for OpenAssessment prompt editing view.
**/

describe("OpenAssessment.EditPromptViews", function() {

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
        // Load the DOM fixture
        loadFixtures('oa_edit.html');

        // Create the view
        var element = $("#oa_prompts_editor_wrapper").get(0);
        notifier = new StubNotifier();
        view = new OpenAssessment.EditPromptsView(element, notifier);
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

describe("OpenAssessment.EditPromptViews after release", function() {

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
        // Load the DOM fixture
        loadFixtures('oa_edit.html');
        $("#openassessment-editor").attr('data-is-released', 'true');

        // Create the view
        var element = $("#oa_prompts_editor_wrapper").get(0);
        notifier = new StubNotifier();
        view = new OpenAssessment.EditPromptsView(element, notifier);
    });

    it("does not allow adding prompts", function() {
        view.addPrompt(); // call method
        $(view.promptsContainer.addButtonElement).click(); // click on button

        var prompts = view.promptsDefinition();
        expect(prompts.length).toEqual(2);
    });

    it("does not allow removing prompts", function() {
        view.removePrompt(view.getAllPrompts()[0]); // call method
        $("." + view.promptsContainer.removeButtonClass, view.element).click(); // click on buttons

        var prompts = view.promptsDefinition();
        expect(prompts.length).toEqual(2);
    });
});
