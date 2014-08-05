(function(window) {
    'use strict';
    /**
    Interface for TrackChanges assessment view.

    Args:
        element (DOM element): The DOM element representing the XBlock.
        trackChangesElements (array of DOM elements): The track changes DOM elements.

    Returns:
        OpenAssessment.TrackChangesView
    **/
    var OpenAssessment = window.OpenAssessment || {};
    function TrackChangesView(element, trackChangesElements) {
        this.element = element;
        this.trackChangesElements = trackChangesElements;
    }

    function clearChangesHandler(e) {
        if (window.confirm(gettext('Are you sure you want to clear your changes?'))) {
            e.data.tracker.rejectAll();
        }
    }

    TrackChangesView.prototype.enableTrackChanges = function enableTrackChanges() {
        var view = this;
        var tracker;
        var $ = window.jQuery;
        var ice = window.ice;

        this.trackChangesElements.forEach(function(trackChangesElement) {
            tracker = new ice.InlineChangeEditor({
                element: trackChangesElement,
                handleEvents: true,
                currentUser: {id: 1, name: 'Reviewer'},
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
            var partNum = trackChangesElement.id.split('_').pop();
            $('#track_changes_clear_button_' + partNum, view.element).click({tracker: tracker}, clearChangesHandler);
        });
    };

    TrackChangesView.prototype.getEditedContent = function getEditedContent() {
        var editedContents = [];
        this.trackChangesElements.forEach(function(trackChangesElement) {
            var editedContentHtml = trackChangesElement.innerHTML;
            editedContents.push(editedContentHtml);
        });
        return editedContents;
    };

    TrackChangesView.prototype.displayTrackChanges = function displayTrackChanges() {
        var view = this;
        var $ = window.jQuery;
        var numPeerEdits = $('.submission__answer__part__text__value.edited').filter(':last').data('peer-num');
        var gradeContent = $('[id^=openassessment__grade__] .submission__answer__display__content', view.element);
        var peerEditSelect = $(
            '<select><option value="original">' +
            gettext('Your Unedited Submission') +
            '</option></select>'
        )
            .insertBefore(gradeContent)
            .wrap("<div class='submission__answer__display__content__peeredit__select'>");
        $('<span>' + gettext('Showing response with:') + ' </span>').insertBefore(peerEditSelect);
        for (var peerNumber = 1; peerNumber <= numPeerEdits; peerNumber++) {
            $('<option value="peer' + peerNumber + '">Peer ' + peerNumber + "'s Edits</option>")
                .appendTo(peerEditSelect);
        }
        var responseHeaders = $('[id^=openassessment__grade__] .submission__answer__response__title');
        var originalAnswerLabel = responseHeaders.first().text();
        $(peerEditSelect).change(function() {
            var valueSelected = $(':selected', this).val();
            if (valueSelected === 'original') {
                responseHeaders.html(originalAnswerLabel);
                $('.submission__answer__part__text__value.edited', view.element).hide();
                $('.submission__answer__part__text__value.original', view.element).show();
            } else {
                responseHeaders.html($(':selected', this).text());
                $('.submission__answer__part__text__value.original', view.element).hide();
                $('.submission__answer__part__text__value.edited', view.element).hide();
                $('.submission__answer__part__text__value.edited.' + valueSelected, view.element).show();
            }
        });
    };

    OpenAssessment.TrackChangesView = TrackChangesView;
    window.OpenAssessment = OpenAssessment;
}(window));
