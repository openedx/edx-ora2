/*
Upload a file using a one-time URL.
This object doesn't do much work, but it makes it
easier to stub out the upload in tests.

This request requires appropriate CORS configuration for AJAX
PUT requests on the server.

Args:
    url (string): The one-time URL we're uploading to.
    imageData (object): The object to upload, which should have properties:
        data (string)
        name (string)
        size (int)
        type (string)
    contentType (string): The MIME type of the data to upload.

Returns:
    JQuery promise

*/
OpenAssessment.FileUploader = function() {
    this.upload = function(url, imageData, contentType) {
        return $.Deferred(
            function(defer) {
                $.ajax({
                    url: url,
                    type: 'PUT',
                    data: imageData,
                    async: false,
                    processData: false,
                    contentType: contentType,
                }).done(
                    function(data, textStatus, jqXHR) {
                        // Log an analytics event
                        Logger.log(
                            "openassessment.upload_file",
                            {
                                contentType: contentType,
                                imageName: imageData.name,
                                imageSize: imageData.size,
                                imageType: imageData.type
                            }
                        );

                        // Return control to the caller
                        defer.resolve();
                    }
                ).fail(
                    function(data, textStatus, jqXHR) {
                        defer.rejectWith(this, [textStatus]);
                    }
                );
            }
        ).promise();
    };
};
