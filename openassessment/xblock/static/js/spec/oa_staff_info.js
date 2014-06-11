/**
Tests for staff info.
**/
describe("OpenAssessment.StaffInfoView", function() {

    // Stub server that returns dummy data for the staff info view
    var StubServer = function() {

        // Remember which fragments have been loaded
        this.fragmentsLoaded = [];

        // Render the template for the staff info view
        this.render = function(component) {
            var server = this;
            this.fragmentsLoaded.push(component);
            return $.Deferred(function(defer) {
                fragment = readFixtures("oa_staff_info.html");
                defer.resolveWith(this, [fragment]);
            });
        };
    };

    // Stub base view
    var StubBaseView = function() {
        this.showLoadError = function(msg) {};
        this.toggleActionError = function(msg, step) {};
        this.setUpCollapseExpand = function(sel) {};
        this.scrollToTop = function() {};
        this.loadAssessmentModules = function() {};
        this.loadMessageView = function() {};
    };

    // Stubs
    var baseView = null;
    var server = null;

    /**
    Initialize the staff info view, then check whether it makes
    an AJAX call to load the staff info section.
    **/
    var assertStaffInfoAjaxCall = function(shouldCall) {
        // Load the staff info view
        var el = $("#openassessment-base").get(0);
        var view = new OpenAssessment.StaffInfoView(el, server, baseView);
        view.load();

        // Check whether it tried to load staff info from the server
        var expectedFragments = [];
        if (shouldCall) { expectedFragments = ['staff_info']; }
        expect(server.fragmentsLoaded).toEqual(expectedFragments);
    };

    beforeEach(function() {
        // Configure the Jasmine fixtures path
        jasmine.getFixtures().fixturesPath = 'base/fixtures';

        // Create a new stub server
        server = new StubServer();

        // Create the stub base view
        baseView = new StubBaseView();
    });

    it("Loads staff info if the page contains a course staff section", function() {
        // Load the fixture for the container page that DOES include a course staff section
        loadFixtures('oa_base_course_staff.html');
        assertStaffInfoAjaxCall(true);

    });

    it("Does NOT load staff info if the page does NOT contain a course staff section", function() {
        // Load the fixture for the container page that does NOT include a course staff section
        loadFixtures('oa_base.html');
        assertStaffInfoAjaxCall(false);
    });
});
