(function (window) {
    'use strict';
    /**
    Interface for TrackChanges assessment view.

    Args:
        element (DOM element): The DOM element representing the XBlock.
        server (OpenAssessment.Server): The interface to the XBlock server.
        baseView (OpenAssessment.BaseView): Container view.

    Returns:
        OpenAssessment.TrackChangesView
    **/
    var OpenAssessment = window.OpenAssessment || {};
    function TrackChangesView(element, server, baseView) {
        this.element = element;
        this.server = server;
        this.baseView = baseView;
        this.content = null;
        this.initialSubmission = '';
    }

    TrackChangesView.prototype.enableTrackChanges = function enableTrackChanges() {
        var tracker;
        var $ = window.jQuery;
        var ice = window.ice;
        var confirm = window.confirm;
        var element = document.getElementById('track-changes-content');

        if (!element) {
            return;
        }
        this.initialSubmission = $(element).html();
        tracker = new ice.InlineChangeEditor({
            element: element,
            handleEvents: true,
            currentUser: { id: 1, name: 'Reviewer' },
            plugins: [
                {
                    // Track content that is cut and pasted
                    name: 'IceCopyPastePlugin',
                    settings: {
                        // List of tags and attributes to preserve when cleaning a paste
                        preserve: 'p,a[href],span[id,class]em,strong'
                    }
                }
            ]
        });
        tracker.startTracking();

        $('#track_changes_clear_button').click(function () {
            if (confirm('Are you sure you want to clear your changes?')) {
                tracker.rejectAll();
            }
        });
    };

    TrackChangesView.prototype.getEditedContent = function getEditedContent() {
        var $ = window.jQuery;
        var view = this;
        var changeTracking = $('#openassessment__peer-assessment');
        var editedContent = $('#track-changes-content', changeTracking).html();
        if (editedContent === view.initialSubmission) {
            editedContent = '';
        }
        return editedContent;
    };

    TrackChangesView.prototype.displayTrackChanges = function displayTrackChanges() {
        var view = this;
        var $ = window.jQuery;
        var changeTracking = $('.submission__answer__display__content__edited', view.element);
        var gradingTitleHeader = changeTracking.siblings('.submission__answer__display__title');
        gradingTitleHeader.wrapInner('<span class="yours"></span>');
        var peerEditSelect = $('<select><option value="yours">Your Unedited Submission</option></select>')
            .insertBefore(gradingTitleHeader)
            .wrap("<div class='submission__answer__display__content__peeredit__select'>");
        $('<span>Show response with: </span>').insertBefore(peerEditSelect);
        $(changeTracking).each(function () {
            var peerNumber = $(this).data('peer-num');
            $('<span class="peer' + peerNumber + '">Peer ' + peerNumber + "'s Edits</span>")
                .appendTo(gradingTitleHeader).hide();
            $('<option value="peer' + peerNumber + '">Peer ' + peerNumber + "'s Edits</option>")
                .appendTo(peerEditSelect);
        });
        $(peerEditSelect).change(function () {
            var valueSelected = $(':selected', this).val();
            $('.submission__answer__display__title span', view.element).hide();
            $('.submission__answer__display__title', view.element).children('.' + valueSelected).show();

            if (valueSelected === 'yours') {
                $('.submission__answer__display__content__edited', view.element).hide();
                $('#submission__answer__display__content__original', view.element).show();
            } else {
                $('#submission__answer__display__content__original', view.element).hide();
                $('.submission__answer__display__content__edited', view.element).hide();
                $('#submission__answer__display__content__edited__' + valueSelected, view.element).show();
            }
        });
    };

    OpenAssessment.TrackChangesView = TrackChangesView;
    window.OpenAssessment = OpenAssessment;
}(window));
