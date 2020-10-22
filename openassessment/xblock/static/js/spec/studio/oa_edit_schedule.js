import EditScheduleView from 'studio/oa_edit_schedule';

/**
Tests for the edit schedule view.
**/
describe('OpenAssessment.EditScheduleView', function() {
    var testValidateDate = function(datetimeControl, expectedError) {
        // Test an invalid datetime
        datetimeControl.datetime('invalid', 'invalid');
        expect(view.validate()).toBe(false);
        expect(view.validationErrors()).toContain(expectedError);

        view.clearValidationErrors();

        // Test a valid datetime
        datetimeControl.datetime('2014-04-05', '00:00');
        expect(view.validate()).toBe(true);
        expect(view.validationErrors()).toEqual([]);
    };

    var view = null;

    beforeEach(function() {
        // Load the DOM fixture
        loadFixtures('oa_edit.html');

        // Create the view
        var element = $('#oa_schedule_editor_wrapper', this.element).get(0);
        view = new EditScheduleView(element);

        view.submissionStart('2014-01-01', '00:00');
        view.submissionDue('2014-03-04', '00:00');
    });


    it('sets and loads the submission start/due dates', function() {
        view.submissionStart('2014-04-01', '12:34');
        expect(view.submissionStart()).toEqual('2014-04-01T12:34');

        view.submissionDue('2014-05-02', '12:34');
        expect(view.submissionDue()).toEqual('2014-05-02T12:34');
    });

    it('validates submission start datetime fields', function() {
        testValidateDate(
            view.startDatetimeControl,
            'Submission start is invalid'
        );
    });

    it('validates submission due datetime fields', function() {
        testValidateDate(
            view.dueDatetimeControl,
            'Submission due is invalid'
        );
    });
});
