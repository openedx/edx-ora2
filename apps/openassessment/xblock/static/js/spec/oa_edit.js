/*
Tests for OA XBlock editing.
*/

describe("OpenAssessment editor", function() {

    var runtime = null;

    beforeEach(function() {

        // Load the DOM fixture
        jasmine.getFixtures().fixturesPath = 'base/fixtures'
        loadFixtures('oa_edit.html');

        // Mock the runtime
        runtime = {
            notify: function(type, data) {},

            // Dummy handler URL returns whatever it's passed in for the handler name
            handlerUrl: function(element, handler) {
                return handler;
            }
        };
        spyOn(runtime, 'notify');

    });

    it("loads the XML definition", function() {
        // Stub AJAX calls to always return successful
        spyOn($, 'ajax').andCallFake(function(params) {
            params.success({
                'success': true,
                'xml': '<openassessment></openassessment>',
                'msg': ''
            });
        });

        // Initialize the editor
        var editor = OpenAssessmentEditor(runtime, $('#openassessment-edit'));

        // Expect that the XML definition was loaded
        var editorContents = $('.openassessment-editor').text();
        expect(editorContents).toEqual('<openassessment></openassessment>');
    });

    it("saves the XML definition", function() {
    expect(false).toBe(true);
    });

    it("reverts the XML definition on cancellation", function() {
    expect(false).toBe(true);
    });

    it("displays validation errors but preserves the author's changes", function() {
    expect(false).toBe(true);
    });

});
