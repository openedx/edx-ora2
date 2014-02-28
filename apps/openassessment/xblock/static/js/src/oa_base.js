/* START Javascript for OpenAssessmentXBlock. */
function OpenAssessmentBlock(runtime, element) {

    var handlerUrl = runtime.handlerUrl(element, 'submit');
    var renderSubmissionUrl = runtime.handlerUrl(element, 'render_submission');
    var renderPeerUrl = runtime.handlerUrl(element, 'render_peer_assessment');
    var renderSelfUrl = runtime.handlerUrl(element, 'render_self_assessment');
    var renderGradeUrl = runtime.handlerUrl(element, 'render_grade');

    var submissionListItem = '#openassessment__response';
    var peerListItem = '#openassessment__peer-assessment';
    var selfListItem = '#openassessment__self-assessment';
    var gradeListItem = '#openassessment__grade';

    /* Sample Debug Console: http://localhost:8000/submissions/Joe_Bloggs/TestCourse/u_3 */

    /*
     * Utility functions
     */
    function collapse(element) {
        element.addClass("is--collapsed");
    }

    function expand(element) {
        element.addClass("is--collapsed");
    }


    /*
     *  Submission Functions
     */
    function render_submissions(data) {
        $(submissionListItem, element).replaceWith(data);
        $('#step--response__submit', element).click(function(eventObject) {
            $.ajax({
                type: "POST",
                url: handlerUrl,
                data: JSON.stringify({"submission": $('#submission__answer__value', element).val()}),
                success: function(data) {
                    $.ajax({
                        type: "POST",
                        url: renderPeerUrl,
                        dataType: "html",
                        success:  function(data) {
                            render_peer_assessment(data);
                        }
                    });
                    collapse($(submissionListItem, element));
                    $.ajax({
                        type: "POST",
                        url: renderSubmissionUrl,
                        success:  function(data) {
                            render_submissions(data);
                            collapse($(submissionListItem, element));
                        }
                    });
                }
            });
        });
    }

    /*
     *  Peer Assessment Functions
     */
    function render_peer_assessment(data) {
        $(peerListItem, element).replaceWith(data);

        function prepare_assessment_post(element) {
            var selector = $("input[type=radio]:checked", element);
            var criteriaChoices = {};
            var values = [];
            for (var i=0; i<selector.length; i++) {
                values[i] = selector[i].value;
                criteriaChoices[selector[i].name] = selector[i].value
            }
            return {
                "submission_uuid":$("span#peer_submission_uuid")[0].innerText,
                "points_earned":values,
                "options_selected":criteriaChoices
            };
        }

        $('#peer-assessment--001__assessment__submit', element).click(function(eventObject) {
            eventObject.preventDefault();
            $.ajax({
                type: "POST",
                url: runtime.handlerUrl(element, 'assess'),
                /* data: JSON.stringify({"submission": $('.openassessment_submission', element).val()}), */
                data: JSON.stringify(prepare_assessment_post(element)),
                success: function(data) {
                    $.ajax({
                        type: "POST",
                        url: renderSelfUrl,
                        dataType: "html",
                        success:  function(data) {
                            $(selfListItem, element).replaceWith(data);
                        }
                    });
                    $.ajax({
                        type: "POST",
                        url: renderPeerUrl,
                        dataType: "html",
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
            dataType: "html",
            success:  function(data) {
                render_submissions(data);
            }
        });

        $.ajax({
            type: "POST",
            url: renderPeerUrl,
            success:  function(data) {
                $(peerListItem, element).replaceWith(data);
                collapse($(peerListItem, element));
            }
        });

        $.ajax({
            type: "POST",
            url: renderSelfUrl,
            success:  function(data) {
                $(selfListItem, element).replaceWith(data);
                collapse($(selfListItem, element));
            }
        });

        $.ajax({
            type: "POST",
            url: renderGradeUrl,
            success:  function(data) {
                $(gradeListItem, element).replaceWith(data);
                collapse($(gradeListItem, element));
            }
        });
    });


}
/* END Javascript for OpenAssessmentXBlock. */
