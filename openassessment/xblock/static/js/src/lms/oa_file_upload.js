/*
Upload a file using a one-time URL.
This object doesn't do much work, but it makes it
easier to stub out the upload in tests.

This request requires appropriate CORS configuration for AJAX
PUT requests on the server.

Args:
    url (string): The one-time URL we're uploading to.
    file (File): The HTML5 file reference.

Returns:
    JQuery promise

*/
OpenAssessment.FileUploader = function() {
    this.upload = function(url, file) {
        return $.Deferred(
            function(defer) {
                $.ajax({
                    url: url,
                    type: 'PUT',
                    data: file,
                    async: false,
                    processData: false,
                    contentType: file.type
                }).done(
                    function() {
                        // Log an analytics event
                        Logger.log(
                            "openassessment.upload_file",
                            {
                                fileName: file.name,
                                fileSize: file.size,
                                fileType: file.type
                            }
                        );

                        // Return control to the caller
                        defer.resolve();
                    }
                ).fail(
                    function(data, textStatus) {
                        defer.rejectWith(this, [textStatus]);
                    }
                );
            }
        ).promise();
    };
};
