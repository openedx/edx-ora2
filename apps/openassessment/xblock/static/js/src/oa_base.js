/* START Javascript for OpenassessmentXBlock. */
function OpenAssessmentBlock(runtime, element) {

    var handlerUrl = runtime.handlerUrl(element, 'submit');
    var renderSubmissionUrl = runtime.handlerUrl(element, 'render_submission');
    var renderPeerUrl = runtime.handlerUrl(element, 'render_peer_assessment');
    var renderSelfUrl = runtime.handlerUrl(element, 'render_self_assessment');
    /* Sample Debug Console: http://localhost:8000/submissions/Joe_Bloggs/TestCourse/u_3 */

    /*
        Submission Functions
     */
    function render_submissions(data) {
        $('#submission', element).replaceWith(data);
        $('#step--response__submit', element).click(function(eventObject) {
            $.ajax({
                type: "POST",
                url: handlerUrl,
                data: JSON.stringify({"submission": $('#submission__answer__value', element).val()}),
                success: function(data) {
                    $.ajax({
                        type: "POST",
                        url: renderPeerUrl,
                        success:  function(data) {
                            render_peer_assessment(data);
                        }
                    });
                    $.ajax({
                        type: "POST",
                        url: renderSubmissionUrl,
                        success:  function(data) {
                            render_submissions(data);
                        }
                    });
                }
            });
        });
    }

    /*
        Peer Assessment Functions
    */
    function render_peer_assessment(data) {
        $('#peer-assessment', element).replaceWith(data);

        function prepare_assessment_post(element) {
            var selector = $("input[type=radio]:checked", element);
            var values = [];
            for (var i=0; i<selector.length; i++) {
                values[i] = selector[i].value;
            }
            return {"submission_uuid":$("div#peer_submission_uuid")[0].innerText, "points_earned":values};
        }

        $('#peer-assessment--001__assessment__submit', element).click(function(eventObject) {
            $.ajax({
                type: "POST",
                url: handlerUrl,
                /* data: JSON.stringify({"submission": $('.openassessment_submission', element).val()}), */
                data: JSON.stringify(prepare_assessment_post(element)),
                success: function(data) {
                    $.ajax({
                        type: "POST",
                        url: renderSelfUrl,
                        success:  function(data) {
                            $('#self-assessment', element).replaceWith(data);
                        }
                    });
                    $.ajax({
                        type: "POST",
                        url: renderPeerUrl,
                        success:  function(data) {
                            render_peer_assessment(data)
                        }
                    });
                }
            });
        });
    }

    $(function ($) {
        /* Here's where you'd do things on page load. */
        $.ajax({
            type: "POST",
            url: renderSubmissionUrl,
            success:  function(data) {
                render_submissions(data);
            }
        });
    });
}
/* END Javascript for OpenassessmentXBlock. */
