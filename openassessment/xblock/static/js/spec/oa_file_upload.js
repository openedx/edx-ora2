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
        fileUploader = new OpenAssessment.FileUploader();
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
            contentType: 'image/jpeg'
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
});