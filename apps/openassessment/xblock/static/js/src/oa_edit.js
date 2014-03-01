/* JavaScript for Studio editing view of Open Assessment XBlock */
function OpenAssessmentEditor(runtime, element) {

    function displayError(errorMsg) {
        runtime.notify('error', {msg: errorMsg});
    }

    // Update editor with the XBlock's current content
    function updateEditorFromXBlock(editor) {
        $.ajax({
            type: "POST",
            url: runtime.handlerUrl(element, 'xml'),
            data: "\"\"",
            success: function(data) {
                if (data.success) {
                    editor.setValue(data.xml);
                }

                else {
                    displayError(data.msg);
                }
            }
        });
    }

    function initializeEditor() {
        var textAreas = $(element).find('.openassessment-editor');
        if (textAreas.length < 1) {
            console.warn("Could not find element for OpenAssessmentBlock XML editor");
            return null;
        }
        else {
            return CodeMirror.fromTextArea(
                textAreas[0], {mode: "xml", lineNumbers: true, lineWrapping: true}
            );
        }
    }

    function initializeSaveButton(editor) {
        saveButtons = $(element).find('.openassessment-save-button');
        if (saveButtons.length < 1) {
            console.warn("Could not find element for OpenAssessmentBlock save button");
        }
        else {
            saveButtons.click(function (eventObject) {
                // Notify the client-side runtime that we are starting
                // to save so it can show the "Saving..." notification
                runtime.notify('save', {state: 'start'});

                // POST the updated description to the XBlock
                // The server-side code is responsible for validating and persisting
                // the updated content.
                $.ajax({
                    type: "POST",
                    url: runtime.handlerUrl(element, 'update_xml'),
                    data: JSON.stringify({ xml: editor.getValue() }),
                    success: function(data) {
                        // Notify the client-side runtime that we finished saving
                        // so it can hide the "Saving..." notification.
                        if (data.success) {
                            runtime.notify('save', {state: 'end'});
                        }

                        // Display an error alert if any errors occurred
                        else {
                            displayError(data.msg);
                        }
                    }
                });
            });
        }
    }

    function initializeCancelButton(editor) {
        cancelButtons = $(element).find('.openassessment-cancel-button');
        if (cancelButtons.length < 1) {
            console.warn("Could not find element for OpenAssessmentBlock cancel button");
        }
        else {
            cancelButtons.click(function (eventObject) {
                // Revert to the XBlock's current content
                updateEditorFromXBlock(editor);

                // Notify the client-side runtime so it will close the editing modal.
                runtime.notify('cancel', {});
            });
        }
    }

    $(function ($) {
        editor = initializeEditor();
        if (editor) {
            updateEditorFromXBlock(editor);
            initializeSaveButton(editor);
            initializeCancelButton(editor);
        }
    });
}
