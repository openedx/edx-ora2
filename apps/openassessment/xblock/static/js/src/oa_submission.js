/* START Javascript for OpenassessmentComposeXBlock. */
function OpenAssessmentBlock(runtime, element) {

    var handlerUrl = runtime.handlerUrl(element, 'submit');
    var success_msg = '<p class="success">Your submission has been received, thank you!</p>';
    var failure_msg = '<p class="failure">An error occurred with your submission</p>';
    var click_msg = '<p class="clickhere">(click here to dismiss this message)</p>';
    /* Sample Debug Console: http://localhost:8000/submissions/Joe_Bloggs/TestCourse/u_3 */

    function displayStatus(result) {
        status = result[0];
        error_msg = result[2];
        if (status === 'true') {
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
            data: JSON.stringify({"submission": $('.openassessment_submission', element).val()}),
            success: displayStatus
        });
    });

    $(function ($) {
        /* Here's where you'd do things on page load. */
        $(element).css('background-color', 'LightBlue')
    });
}
/* END Javascript for OpenassessmentComposeXBlock. */
