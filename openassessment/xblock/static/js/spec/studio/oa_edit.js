/**
Tests for OA XBlock editing.
**/

describe("OpenAssessment.StudioView", function() {

    var runtime = {
        notify: function(type, data) {}
    };

    // Stub server that returns dummy data or reports errors.
    var StubServer = function() {
        this.updateError = false;
        this.isReleased = false;
        this.receivedData = null;
        this.successPromise = $.Deferred(function(defer) {
            defer.resolve();
        });
        this.errorPromise = $.Deferred(function(defer) {
            defer.rejectWith(this, ['Test error']);
        }).promise();

        this.updateEditorContext = function(kwargs) {
            if (this.updateError) {
                return this.errorPromise;
            }
            else {
                this.receivedData = kwargs;
                return this.successPromise;
            }
        };

        this.checkReleased = function() {
            var server = this;
            return $.Deferred(function(defer) {
                defer.resolveWith(this, [server.isReleased]);
            }).promise();
        };
    };

    var server = null;
    var view = null;

    beforeEach(function() {
        // Load the DOM fixture
        jasmine.getFixtures().fixturesPath = 'base/fixtures';
        loadFixtures('oa_edit.html');

        // Create the stub server
        server = new StubServer();

        // Mock the runtime
        spyOn(runtime, 'notify');

        // Create the object under test
        var el = $('#openassessment-editor').get(0);
        view = new OpenAssessment.StudioView(runtime, el, server);
    });

    it("confirms changes for a released problem", function() {
        // Simulate an XBlock that has been released
        server.isReleased = true;

        // Stub the confirmation step (avoid showing the dialog)
        spyOn(view, 'confirmPostReleaseUpdate').andCallFake(
            function(onConfirm) { onConfirm(); }
        );

        // Save the updated context
        view.save();

        // Verify that the user was asked to confirm the changes
        expect(view.confirmPostReleaseUpdate).toHaveBeenCalled();
    });

    it("cancels editing", function() {
        view.cancel();
        expect(runtime.notify).toHaveBeenCalledWith('cancel', {});
    });

    it("displays an error when server reports an update XML error", function() {
        server.updateError = true;
        view.save();
        expect(runtime.notify).toHaveBeenCalledWith('error', {msg: 'Test error'});
    });

    it("displays the correct tab on initialization", function() {
        $(".oa_editor_tab", view.element).each(function(){
            if ($(this).attr('aria-controls') == "oa_prompt_editor_wrapper"){
                expect($(this).hasClass('ui-state-active')).toBe(true);
            } else {
                expect($(this).hasClass('ui-state-active')).toBe(false);
            }
        });
    });

    it("installs checkbox listeners with callback", function () {
        this.funct = function(){};

        spyOn(this, 'funct');

        var toggler = new OpenAssessment.ToggleControl(
            view.element,
            "#ai_assessment_description_closed",
            "#ai_assessment_settings_editor"
        );

        toggler.show();
        toggler.hide();
        expect(this.funct.calls.length).toEqual(0);

        toggler = new OpenAssessment.ToggleControl(
            view.element,
            "#ai_assessment_description_closed",
            "#ai_assessment_settings_editor",
            this.funct
        );

        toggler.show();
        toggler.hide();
        expect(this.funct.calls.length).toEqual(2);

    });
});
