/* START Javascript for OpenassessmentComposeXBlock. */
function OpenAssessmentBlock(runtime, element) {

    var handlerUrl = runtime.handlerUrl(element, 'assess');
    var success_msg = '<p class="success">Thanks for your feedback!</p>';
    var failure_msg = '<p class="failure">An error occurred with your feedback</p>';
    var click_msg = '<p class="clickhere">(click here to dismiss this message)</p>';
    /* Sample Debug Console: http://localhost:8000/submissions/Joe_Bloggs/TestCourse/u_3 */

    function prepare_assessment_post(element) {
        var selector = $("input[type=radio]:checked", element);
        var values = [];
        for (i=0; i<selector.length; i++) {
            values[i] = selector[i].value;
        }
        return {"submission_uuid":$("div#peer_submission_uuid")[0].innerText, "points_earned":values};
    }

    function displayStatus(result) {
        var status = result[0];
        var error_msg = result[1];
        if (status) {
            $('.openassessment_response_status_block', element).html(success_msg.concat(click_msg)); 
        } else {
            $('.openassessment_response_status_block', element).html(failure_msg.concat(error_msg).concat(click_msg));
        }
        $('.openassessment_response_status_block', element).css('display', 'block');
    }
    $('.openassessment_response_status_block', element).click(function(eventObject) {
        $('.openassessment_response_status_block', element).css('display', 'none');
    });

    $('.openassessment_submit', element).click(function(eventObject) {
        $.ajax({
            type: "POST",
            url: handlerUrl,
            /* data: JSON.stringify({"submission": $('.openassessment_submission', element).val()}), */
            data: JSON.stringify(prepare_assessment_post(element)),
            success: displayStatus
        });
    });

    $(function ($) {
        /* Here's where you'd do things on page load. */
        $(element).css('background-color', 'LightBlue')
    });
}
/* END Javascript for OpenassessmentComposeXBlock. */
