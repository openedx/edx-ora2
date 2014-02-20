/* START Javascript for OpenassessmentComposeXBlock. */
function OpenAssessmentBlock(runtime, element) {

    var handlerUrl = runtime.handlerUrl(element, 'submit');
    var success_msg = '<p class="success">Your submission has been received, thank you!</p>';
    var failure_msg = '<p class="failure">An error occurred with your submission</p>';
    var click_msg = '<p class="clickhere">(click here to dismiss this message)</p>';
    /* Sample Debug Console: http://localhost:8000/submissions/Joe_Bloggs/TestCourse/u_3 */

    $('.action action--submit step--response__submit', element).click(function(eventObject) {
        $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify({"submission": $('.openassessment_submission', element).val()}),
            success: displayStatus
        });
    });
}
/* END Javascript for OpenassessmentComposeXBlock. */
