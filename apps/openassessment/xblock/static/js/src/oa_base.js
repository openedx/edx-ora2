/* START Javascript for OpenassessmentXBlock. */
function OpenAssessmentBlock(runtime, element) {

    var handlerUrl = runtime.handlerUrl(element, 'submit');
    var renderUrl = runtime.handlerUrl(element, 'render_assessment');
    /* Sample Debug Console: http://localhost:8000/submissions/Joe_Bloggs/TestCourse/u_3 */



    /*
        Peer Assessment Functions
    */
    function prepare_assessment_post(element) {
        var selector = $("input[type=radio]:checked", element);
        var values = [];
        for (i=0; i<selector.length; i++) {
            values[i] = selector[i].value;
        }
        return {"submission_uuid":$("div#peer_submission_uuid")[0].innerText, "points_earned":values};
    }

    $('.openassessment_submit', element).click(function(eventObject) {
        $.ajax({
            type: "POST",
            url: handlerUrl,
            /* data: JSON.stringify({"submission": $('.openassessment_submission', element).val()}), */
            data: JSON.stringify(prepare_assessment_post(element)),
            success: function(data) {
                $.ajax({
                    type: "POST",
                    url: renderUrl,
                    data: JSON.stringify({"assessment": "peer-assessment"}),
                    success:  function(data) {
                        $('#peer-assessment', element).replaceWith(data);
                    }
                });
                $.ajax({
                    type: "POST",
                    url: renderUrl,
                    data: JSON.stringify({"assessment": "self-assessment"}),
                    success:  function(data) {
                        $('#self-assessment', element).replaceWith(data);
                    }
                });
            }
        });
    });

    $(function ($) {
        /* Here's where you'd do things on page load. */
        $.ajax({
            type: "POST",
            url: renderUrl,
            data: JSON.stringify({"assessment": "submission"}),
            success:  function(data) {
                $('#submission', element).replaceWith(data);

                /*
                 Submission Functions
                 */
                $('#step--response__submit', element).click(function(eventObject) {
                    $.ajax({
                        type: "POST",
                        url: handlerUrl,
                        data: JSON.stringify({"submission": $('#submission__answer__value', element).val()}),
                        success: function(data) {
                            alert("Success?")
                            $.ajax({
                                type: "POST",
                                url: renderUrl,
                                data: JSON.stringify({"assessment": "submission"}),
                                success:  function(data) {
                                    $('#submission', element).replaceWith(data);
                                }
                            });
                            $.ajax({
                                type: "POST",
                                url: renderUrl,
                                data: JSON.stringify({"assessment": "peer-assessment"}),
                                success:  function(data) {
                                    $('#peer-assessment', element).replaceWith(data);
                                }
                            });
                        },
                        fail: function(data) {alert("FAIL!!")}
                    });
                });
            }
        });
    });
}
/* END Javascript for OpenassessmentXBlock. */
