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

        this.peerAssess = function() {
            return successPromise;
        };

        this.render = function() {
            return successPromise;
        };

        this.renderContinuedPeer = function() {
            return successPromise;
        };
    };

    // Stubs
    var server = null;
    var runtime = {};

    var createPeerAssessmentView = function(template) {
        loadFixtures(template);

        var assessmentElement = $('#openassessment__peer-assessment').get(0);
        var baseView = new OpenAssessment.BaseView(runtime, assessmentElement, server, {});
        var view = new OpenAssessment.PeerView(assessmentElement, server, baseView);
        view.installHandlers();
        return view;
    };

    var submitPeerAssessment = function(view) {
        spyOn(server, 'peerAssess').and.callThrough();

        // Select options in the rubric
        var optionsSelected = {};
        optionsSelected['Criterion 1'] = 'Poor';
        optionsSelected['Criterion 2'] = 'Fair';
        optionsSelected['Criterion 3'] = 'Good';
        view.rubric.optionsSelected(optionsSelected);

        // Provide per-criterion feedback
        var criterionFeedback = {};
        criterionFeedback['Criterion 1'] = "You did a fair job";
        criterionFeedback['Criterion 3'] = "You did a good job";
        view.rubric.criterionFeedback(criterionFeedback);

        // Provide overall feedback
        var overallFeedback = "Good job!";
        view.rubric.overallFeedback(overallFeedback);

        // Submit the peer assessment
        view.peerAssess();

        // Expect that the peer assessment was sent to the server
        // with the options and feedback we selected
        expect(server.peerAssess).toHaveBeenCalledWith(
            optionsSelected, criterionFeedback, overallFeedback, ''
        );
    };

    beforeEach(function() {
        // Create a new stub server
        server = new StubServer();
        server.renderLatex = jasmine.createSpy('renderLatex');
    });

    afterEach(function() {
        OpenAssessment.clearUnsavedChanges();
    });

    it("sends a peer assessment to the server", function() {
        var view = createPeerAssessmentView('oa_peer_assessment.html');
        submitPeerAssessment(view);
    });

    it("re-enables the peer assess button on error", function() {
        var view = createPeerAssessmentView('oa_peer_assessment.html');
        // Simulate a server error
        spyOn(server, 'peerAssess').and.callFake(function() {
            expect(view.peerSubmitEnabled()).toBe(false);
            return $.Deferred(function(defer) {
                defer.rejectWith(this, ['ENOUNKNOWN', 'Error occurred!']);
            }).promise();
        });
        view.peerAssess();

        // Expect the submit button to have been re-enabled
        expect(view.peerSubmitEnabled()).toBe(true);
    });

    it("re-enables the continued grading button on error", function() {
        var view = createPeerAssessmentView('oa_peer_complete.html');

        // Simulate a server error
        spyOn(server, 'renderContinuedPeer').and.callFake(function() {
            expect(view.continueAssessmentEnabled()).toBe(false);
            return $.Deferred(function(defer) {
                defer.rejectWith(this, ['Error occurred!']);
            }).promise();
        });
        view.loadContinuedAssessment();

        // Expect the submit button to have been re-enabled
        expect(view.continueAssessmentEnabled()).toBe(true);
    });

    it("can submit assessments in turbo mode", function() {
        var view = createPeerAssessmentView('oa_turbo_mode.html');
        submitPeerAssessment(view);
    });

    it("warns of unsubmitted assessments", function() {
        var view = createPeerAssessmentView('oa_peer_assessment.html');

        expect(view.baseView.unsavedWarningEnabled()).toBe(false);

        // Click on radio buttons, to create unsubmitted changes.
        $('.question__answers', view.el).each(function() {
            $('input[type="radio"]', this).first().click();
        });

        expect(view.baseView.unsavedWarningEnabled()).toBe(true);

        // When submitPeerAssessment is executed, the views will all re-render. However,
        // as the test does not mock out the surrounding elements, the re-render
        // of the peer assessment module will keep the original HTML intact (with selected
        // options), causing the unsavedWarnings callback to be triggered again (after it is properly
        // cleared during the submit operation). To avoid this, have the view re-render fail.
        server.render = function() {
            return $.Deferred(
                function(defer) {
                    defer.fail();
                }
            ).promise();
        };

        submitPeerAssessment(view);

        expect(view.baseView.unsavedWarningEnabled()).toBe(false);
    });
});
