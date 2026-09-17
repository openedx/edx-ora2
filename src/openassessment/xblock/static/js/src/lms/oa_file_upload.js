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
        headers: { 'Content-Disposition': `attachment; filename*=UTF-8''${this.encodeRFC5987ValueChars(file.name)}` },
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

  // How to correctly encode filenames in headers (although |?~* are not preserved)
  // From https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/encodeURIComponent
  encodeRFC5987ValueChars(str) {
    return encodeURIComponent(str)
      // Note that although RFC3986 reserves "!", RFC5987 does not,
      // so we do not need to escape it
      .replace(/['()]/g, escape) // i.e., %27 %28 %29
      .replace(/\*/g, '%2A')
      // The following are not required for percent-encoding per RFC5987,
      // so we can allow for a little better readability over the wire: |`^
      .replace(/%(?:7C|60|5E)/g, unescape);
  }
}

export default FileUploader;
