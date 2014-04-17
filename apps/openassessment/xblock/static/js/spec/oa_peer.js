/**
 Tests for OpenAssessment Peer view.
 **/

describe("OpenAssessment.PeerView", function() {

    // Stub server
    var StubServer = function() {
        var successPromise = $.Deferred(
            function(defer) {
                defer.resolve();
            }
        ).promise();

        this.peerAssess = function(optionsSelected, feedback) {
            return $.Deferred(function(defer) { defer.resolve(); }).promise();
        };

        this.render = function(step) {
            return successPromise;
        };
    };
    // Stub runtime
    var runtime = {};

    // Stubs
    var server = null;

    // View under test
    var view = null;

    beforeEach(function() {
        // Load the DOM fixture
        jasmine.getFixtures().fixturesPath = 'base/fixtures';
        loadFixtures('oa_peer_assessment.html');

        // Create a new stub server
        server = new StubServer();

        // Create the object under test
        var el = $("#openassessment").get(0);
        view = new OpenAssessment.BaseView(runtime, el, server);
    });

    it("re-enables the peer assess button on error", function() {
        // Simulate a server error
        spyOn(server, 'peerAssess').andCallFake(function() {
            expect(view.peerSubmitEnabled()).toBe(false);
            return $.Deferred(function(defer) {
                defer.rejectWith(this, ['ENOUNKNOWN', 'Error occurred!']);
            }).promise();
        });
        view.peerAssess();
        // Expect the submit button to have been re-enabled
        expect(view.peerSubmitEnabled()).toBe(true);
    });
});
