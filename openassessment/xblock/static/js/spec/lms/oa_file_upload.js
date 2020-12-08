import FileUploader from 'lms/oa_file_upload';

describe("OpenAssessment.FileUploader", function() {

    var fileUploader = null;
    var TEST_URL = "http://www.example.com/upload";
    var TEST_FILE = {
        data: "abcdefghijklmnopqrstuvwxyz",
        name: "test.jpg",
        size: 10471,
        type: "image/jpeg"
    };

    beforeEach(function() {
        fileUploader = new FileUploader();
    });

    it("logs a file upload event", function() {
        // Stub the AJAX call, simulating success
        var successPromise = $.Deferred(
            function(defer) { defer.resolve(); }
        ).promise();
        spyOn($, 'ajax').and.returnValue(successPromise);

        // Stub the event logger
        spyOn(Logger, 'log');

        // Upload a file
        fileUploader.upload(TEST_URL, TEST_FILE);

        // Verify that a PUT request was sent with the right parameters
        expect($.ajax).toHaveBeenCalledWith({
            url: TEST_URL,
            type: 'PUT',
            data: TEST_FILE,
            async: false,
            processData: false,
            contentType: 'image/jpeg',
            headers: { 'Content-Disposition': `attachment; filename="${TEST_FILE.name}"` },
        });

        // Verify that the event was logged
        expect(Logger.log).toHaveBeenCalledWith(
            "openassessment.upload_file", {
                fileName: TEST_FILE.name,
                fileSize: TEST_FILE.size,
                fileType: TEST_FILE.type
            }
        );
    });

    it("logs a file upload error event", function(done) {
        // Stub the AJAX call, simulating success
        var failurePromise = $.Deferred(
            function(defer) { defer.rejectWith(this, ['data', 'textStatus', 'errorThrown']); }
        ).promise();
        spyOn($, 'ajax').and.returnValue(failurePromise);

        // Stub the event logger
        spyOn(Logger, 'log');

        // Upload a file
        fileUploader.upload(TEST_URL, TEST_FILE).then(function() {
            // Verify that the promise was not resolved
            done(new Error('File upload error should not be resolved'));
        }, function(reason) {
            expect(reason).toBe('textStatus');
            done();
        });

        // Verify that the event was logged
        expect(Logger.log).toHaveBeenCalledWith(
            "openassessment.upload_file_error", {
                errorThrown: 'errorThrown'
            }
        );
    });
});
