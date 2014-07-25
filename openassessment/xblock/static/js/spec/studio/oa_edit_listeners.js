/**
Tests for the student training listener,
which dynamically updates student training examples
based on rubric changes.
**/
describe("OpenAssessment.StudentTrainingListener", function() {

    var listener = null;

    /**
    Check that all student training examples have the expected
    criteria or option labels.

    Args:
        actual (array): A list of example criteria or option labels
            (object literals) retrieved from the DOM.

        expected (object literal): The expected value for each example.

        numExamples (int, optional): The number of student training examples
            (defaults to 1).

    **/
    var assertExampleLabels = function(actual, expected, numExamples) {
        // The most common case is one example, so use that as a default.
        if (typeof(numExamples) == "undefined") {
            numExamples = 1;
        }

        // Add one to the number of examples to include the client-side template.
        expect(actual.length).toEqual(numExamples + 1);

        // Verify that each example matches what we expect.
        // Since there is only one rubric for the problem,
        // the training examples should always match that rubric.
        for (var index in actual) {
            for (var criterionName in expected) {
                expect(actual[index][criterionName]).toEqual(expected[criterionName]);
            }
        }
    };

    beforeEach(function() {
        loadFixtures('oa_edit_student_training.html');
        listener = new OpenAssessment.StudentTrainingListener();
    });

    it("updates the label of an option", function() {
        // Initial state, set by the fixture
        assertExampleLabels(
            listener.examplesOptionsLabels(),
            {
                criterion_with_two_options: {
                    "": "Not Scored",
                    option_1: "Fair - 1 points",
                    option_2: "Good - 2 points"
                }
            }
        );

        // Update the option label and points,
        listener.optionUpdated({
             criterionName: "criterion_with_two_options",
             name: "option_1",
             label: "This is a new label!",
             points: 42
        });

        // Verify the new state
        assertExampleLabels(
            listener.examplesOptionsLabels(),
            {
                criterion_with_two_options: {
                    "": "Not Scored",
                    option_1: "This is a new label! - 42 points",
                    option_2: "Good - 2 points"
                }
            }
        );
    });

    it("removes an option and displays an alert", function() {
        // Initial state, set by the fixture
        assertExampleLabels(
            listener.examplesOptionsLabels(),
            {
                criterion_with_two_options: {
                    "": "Not Scored",
                    option_1: "Fair - 1 points",
                    option_2: "Good - 2 points"
                }
            }
        );
        expect(listener.alert.isVisible()).toBe(false);

        // Remove an option
        listener.optionRemove({
            criterionName: "criterion_with_two_options",
            name: "option_1"
        });

        // Verify the new state
        assertExampleLabels(
            listener.examplesOptionsLabels(),
            {
                criterion_with_two_options: {
                    "": "Not Scored",
                    option_2: "Good - 2 points"
                }
            }
        );

        // The alert should be displayed
        expect(listener.alert.isVisible()).toBe(true);
    });

    it("removes a criterion if the criterion has no options", function() {
        // Initial state, set by the fixture
        assertExampleLabels(
            listener.examplesCriteriaLabels(),
            { criterion_with_two_options: "Criterion with two options" }
        );
        expect(listener.alert.isVisible()).toBe(false);

        // Remove all options for the criterion
        listener.removeAllOptions({
            criterionName: "criterion_with_two_options"
        });

        // Since the criterion has no options, it should no longer
        // be available in student training
        assertExampleLabels(listener.examplesCriteriaLabels(), {}, 1);

        // The alert should be displayed
        expect(listener.alert.isVisible()).toBe(true);
    });

    it("updates the label of a criterion", function() {
        // Initial state, set by the fixture
        assertExampleLabels(
            listener.examplesCriteriaLabels(),
            { criterion_with_two_options: "Criterion with two options" }
        );

        // Update a label
        listener.criterionUpdated({
             criterionName: "criterion_with_two_options",
             criterionLabel: "This is a new label!",
        });

        // Verify the new state
        assertExampleLabels(
            listener.examplesCriteriaLabels(),
            { criterion_with_two_options: "This is a new label!" }
        );
    });

    it("adds a criterion and options", function() {

        // Initial state, set by the fixture
        assertExampleLabels(
            listener.examplesCriteriaLabels(),
            { criterion_with_two_options: "Criterion with two options" }
        );

        // Add the criterion, which has no options
        listener.criterionAdd({
            criterionName: "new_criterion",
            label: "This is a new criterion!"
        });

        // Since the criterion has no options, it should not
        // be displayed.
        assertExampleLabels(
            listener.examplesCriteriaLabels(),
            { criterion_with_two_options: "Criterion with two options" }
        );

        // Add an option to the criterion
        listener.optionAdd({
            criterionName: "new_criterion",
            name: "new_option",
            label: "This is a new option!",
            points: 56
        });

        // Now the criterion should be visible in student training
        assertExampleLabels(
            listener.examplesCriteriaLabels(),
            {
                criterion_with_two_options: "Criterion with two options",
                new_criterion: "This is a new criterion!"
            }
        );
        assertExampleLabels(
            listener.examplesOptionsLabels(),
            {
                criterion_with_two_options: {
                    "": "Not Scored",
                    option_1: "Fair - 1 points",
                    option_2: "Good - 2 points",
                },
                new_criterion: {
                    "": "Not Scored",
                    new_option: "This is a new option! - 56 points"
                }
            }
        );

        // Add another option to the criterion
        listener.optionAdd({
            criterionName: "new_criterion",
            name: "yet_another_option",
            label: "This is yet another option!",
            points: 27
        });
        assertExampleLabels(
            listener.examplesOptionsLabels(),
            {
                criterion_with_two_options: {
                    "": "Not Scored",
                    option_1: "Fair - 1 points",
                    option_2: "Good - 2 points",
                },
                new_criterion: {
                    "": "Not Scored",
                    new_option: "This is a new option! - 56 points",
                    yet_another_option: "This is yet another option! - 27 points"
                }
            }
        );
    });

    it("removes a criterion and displays an alert", function() {
        // Initial state, set by the fixture
        assertExampleLabels(
            listener.examplesCriteriaLabels(),
            { criterion_with_two_options: "Criterion with two options" }
        );
        expect(listener.alert.isVisible()).toBe(false);

        // Remove the criterion
        listener.criterionRemove({
            criterionName: "criterion_with_two_options"
        });

        // The criterion should no longer be displayed
        assertExampleLabels(listener.examplesCriteriaLabels(), {}, 1);

        // The alert should be displayed
        expect(listener.alert.isVisible()).toBe(true);
    });
});
