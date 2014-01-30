/* START Javascript for OpenassessmentComposeXBlock. */
function OpenassessmentComposeXBlock(runtime, element) {

    function itWorked(result) {
        alert(result);
    }

    var handlerUrl = runtime.handlerUrl(element, 'submit');

    $('.openassessment_submit', element).click(function(eventObject) {
        $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify({"submission": $('.openassessment_submission', element).val()}),
            success: itWorked
        });
    });

    $(function ($) {
        /* Here's where you'd do things on page load. */
        $(element).css('background-color', 'DarkOrchid')
    });
}
/* END Javascript for OpenassessmentComposeXBlock. */
