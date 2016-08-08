/**
Tests for an Open Assessment rubric.
**/

describe("OpenAssessment.Rubric", function() {

    var rubric = null;

    beforeEach(function() {
        loadFixtures('oa_rubric.html');

        var el = $(".peer-assessment--001__assessment").get(0);
        rubric = new OpenAssessment.Rubric(el);
    });

    it("enables the submit button only when all options and required feedback have been provided", function() {
        // Initially, the submit button should be disabled
        expect(rubric.canSubmit()).toBe(false);

        // Select some, but not all, options
        rubric.optionsSelected({vocabulary: 'Good'});
        expect(rubric.canSubmit()).toBe(false);

        // Select all options, but do not provide required feedback
        rubric.optionsSelected({
            vocabulary: 'Good',
            grammar: 'Bad'
        });
        expect(rubric.canSubmit()).toBe(false);

        // Provide required feedback, but do not provide all options
        rubric.optionsSelected({vocabulary: 'Good'});
        rubric.criterionFeedback({
            feedback_only: 'This is some feedback.'
        });
        expect(rubric.canSubmit()).toBe(false);

        // Provide all options AND required feedback
        rubric.optionsSelected({
            vocabulary: 'Good',
            grammar: 'Bad'
        });
        rubric.criterionFeedback({
            feedback_only: 'This is some feedback.'
        });
        expect(rubric.canSubmit()).toBe(true);
    });
});
