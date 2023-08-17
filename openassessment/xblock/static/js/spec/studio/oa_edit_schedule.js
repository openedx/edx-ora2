import EditScheduleView from 'studio/oa_edit_schedule';
import {
  EditPeerAssessmentView,
  EditSelfAssessmentView
} from 'studio/oa_edit_assessment';


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
    var assessmentViews = null;

    var setupAssessmentViews = function() {
        const peerAssessmentElement = $("#oa_peer_assessment_editor").get(0);
        const peerAssessmentView = new EditPeerAssessmentView(peerAssessmentElement);
        peerAssessmentView.startDatetime("2014-01-01", "00:00");
        peerAssessmentView.dueDatetime("2014-01-01", "00:00");

        const selfAssessmentElement = $("#oa_self_assessment_editor").get(0);
        const selfAssessmentView = new EditSelfAssessmentView(selfAssessmentElement);
        selfAssessmentView.startDatetime("2014-01-01", "00:00");
        selfAssessmentView.dueDatetime("2014-01-01", "00:00");

        return {
            oa_peer_assessment_editor: peerAssessmentView,
            oa_self_assessment_editor: selfAssessmentView
        }
    };

    beforeEach(function() {
        // Load the DOM fixture
        loadFixtures('oa_edit.html');

        // Create the view
        var element = $('#oa_schedule_editor_wrapper', this.element).get(0);
        assessmentViews = setupAssessmentViews();
        view = new EditScheduleView(element, assessmentViews);

        view.submissionStart('2014-01-01', '00:00');
        view.submissionDue('2014-03-04', '00:00');
    });

    it('sets and loads the submission start/due dates', function() {
        view.submissionStart('2014-04-01', '12:34');
        expect(view.submissionStart()).toEqual('2014-04-01T12:34');

        view.submissionDue('2014-05-02', '12:34');
        expect(view.submissionDue()).toEqual('2014-05-02T12:34');
    });

    it('has working date config type', function() {
        const expectedValue = $('input[name="date_config_type"][type="radio"]:checked', this.element).val();
        expect(view.dateConfigType()).toEqual(expectedValue);

        // if subsection_end_date is not defined, disable subsection option
        const subsectionEl = $('input[name="date_config_type"][type="radio"][value="subsection"]', this.element);
        expect(subsectionEl.prop('disabled')).toBe(true);

        // if course_end_date is not defined, disable course end option
        const courseEndEl = $('input[name="date_config_type"][type="radio"][value="course_end"]', this.element);
        expect(courseEndEl.prop('disabled')).toBe(true);
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

    describe('assessment step schedules', function() {
        it("validates the peer start date and time", function() {
            testValidateDate(
                assessmentViews.oa_peer_assessment_editor.startDatetimeControl,
                "Peer assessment start is invalid"
            );
        });
    
        it("validates the peer due date and time", function() {
            testValidateDate(
                assessmentViews.oa_peer_assessment_editor.dueDatetimeControl,
                "Peer assessment due is invalid"
            );
        });

        it("validates the self start date and time", function() {
            testValidateDate(
                assessmentViews.oa_self_assessment_editor.startDatetimeControl,
                "Self assessment start is invalid"
            );
        });

        it("validates the self due date and time", function() {
            testValidateDate(
                assessmentViews.oa_self_assessment_editor.dueDatetimeControl,
                "Self assessment due is invalid"
            );
        });
    })
});
