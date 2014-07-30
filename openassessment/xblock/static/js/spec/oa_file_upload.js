describe("OpenAssessment.FileUploader", function() {

    var fileUploader = null;
    var TEST_URL = "http://www.example.com/upload";
    var TEST_IMAGE = {
        data: "abcdefghijklmnopqrstuvwxyz",
        name: "test.jpg",
        size: 10471,
        type: "image/jpeg"
    };
    var TEST_CONTENT_TYPE = "image/jpeg";

    beforeEach(function() {
        fileUploader = new OpenAssessment.FileUploader();
    });

    it("logs a file upload event", function() {
        // Stub the AJAX call, simulating success
        var successPromise = $.Deferred(
            function(defer) { defer.resolve(); }
        ).promise();
        spyOn($, 'ajax').andReturn(successPromise);

        // Stub the event logger
        spyOn(Logger, 'log');

        // Upload a file
        fileUploader.upload(TEST_URL, TEST_IMAGE, TEST_CONTENT_TYPE);

        // Verify that the event was logged
        expect(Logger.log).toHaveBeenCalledWith(
            "openassessment.upload_file", {
                contentType: TEST_CONTENT_TYPE,
                imageName: TEST_IMAGE.name,
                imageSize: TEST_IMAGE.size,
                imageType: TEST_IMAGE.type
            }
        );
    });
});