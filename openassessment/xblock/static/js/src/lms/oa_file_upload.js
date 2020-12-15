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
export class FileUploader {
  upload(url, file) {
    // eslint-disable-next-line new-cap
    return $.Deferred((defer) => {
      $.ajax({
        url,
        type: 'PUT',
        data: file,
        async: false,
        processData: false,
        contentType: file.type,
        headers: { 'Content-Disposition': `attachment; filename="${file.name}"` },
      }).done(() => {
        // Log an analytics event
        Logger.log(
          'openassessment.upload_file',
          {
            fileName: file.name,
            fileSize: file.size,
            fileType: file.type,
          },
        );

        // Return control to the caller
        defer.resolve();
      }).fail((data, textStatus) => {
        Logger.log(
          'openassessment.upload_file_error',
          {
            statusText: data.statusText,
          },
        );
        defer.rejectWith(this, [textStatus]);
      });
    }).promise();
  }
}

export default FileUploader;
