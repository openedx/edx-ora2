import BaseView from 'lms/oa_base';
import StudentTrainingView from 'lms/oa_training';

/**
Tests for OpenAssessment Student Training view.
**/

describe("OpenAssessment.StudentTrainingView", function() {

    // Stub server
    var StubServer = function() {
        var successPromise = $.Deferred(
            function(defer) { defer.resolve(); }
        ).promise();

        this.render = function(step) {
            return successPromise;
        };

        this.trainingAssess = function() {
            var server = this;
            return $.Deferred(function(defer) {
                defer.resolveWith(server, [server.corrections]);
            }).promise();
        };

        // The corrections returned by the stub server.
        // Tests can update this property to control
        // the behavior of the stub.
        this.corrections = {};
    };

    // Stubs
    var server = null;
    var runtime = {};

    // View under test
    var view = null;

    beforeEach(function(done) {
        // Load the DOM fixture
        loadFixtures('oa_student_training.html');

        // Create a new stub server
        server = new StubServer();
        server.renderLatex = jasmine.createSpy('renderLatex');

        // Create the object under test
        var rootElement = $('.step--student-training').parent().get(0);
        var baseView = new BaseView(runtime, rootElement, server, {
            "TEXT_RESPONSE_EDITOR": 'text',
            "AVAILABLE_EDITORS": {
                'text': {
                    'js': ['/base/js/src/lms/editors/oa_editor_textarea.js']
                }
            }
        });
        view = baseView.trainingView;
        
        // Create a mock editor controller to avoid RequireJS loading issues in tests
        var mockEditorController = {
            _response: ['', ''],
            load: function(elements) {
                this.elements = elements;
                return Promise.resolve();
            },
            response: function(texts) {
                if (typeof texts !== 'undefined') {
                    this._response = texts;
                    return this._response;
                }
                return this._response;
            },
            setOnChangeListener: function(callback) {
                this._changeCallback = callback;
            }
        };
        
        // Mock the responseEditorLoader to avoid async loading issues
        spyOn(view.responseEditorLoader, 'load').and.returnValue(Promise.resolve(mockEditorController));
        
        // Now call renderResponseViaEditor and installHandlers
        view.renderResponseViaEditor().then(() => {
            view.installHandlers();
            done();
        });
    });

    it("submits an assessment for a training example", function() {
        server.corrections = {
            "Criterion 1": "Good",
            "Criterion 2": "Poor",
            "Criterion 3": "Fair"
        };
        spyOn(server, 'trainingAssess').and.callThrough();

        // Select rubric options
        var optionsSelected = {};
        optionsSelected['Criterion 1'] = 'Poor';
        optionsSelected['Criterion 2'] = 'Fair';
        optionsSelected['Criterion 3'] = 'Good';
        view.rubric.optionsSelected(optionsSelected);

        // Submit the assessment
        view.assess();

        // Expect that the assessment was sent to the server
        expect(server.trainingAssess).toHaveBeenCalledWith(optionsSelected);
    });

    it("disable the assess button when the user submits", function() {
        server.corrections = {
            "Criterion 1": "Good",
            "Criterion 2": "Poor",
            "Criterion 3": "Fair"
        };

        // Initially, the button should be disabled
        expect(view.assessButtonEnabled()).toBe(false);

        // Select options and submit an assessment
        var optionsSelected = {};
        optionsSelected['Criterion 1'] = 'Poor';
        optionsSelected['Criterion 2'] = 'Fair';
        optionsSelected['Criterion 3'] = 'Good';
        view.rubric.optionsSelected(optionsSelected);

        // Enable the button (we do this manually to avoid dealing with async change handlers)
        view.assessButtonEnabled(true);

        // Submit the assessment
        view.assess();

        // The button should be disabled after submission
        expect(view.assessButtonEnabled()).toBe(false);
    });

    it("reloads the assessment steps when the user submits an assessment", function() {
        // Simulate that the user answered the problem correctly, so there are no corrections
        server.corrections = {};
        spyOn(server, 'trainingAssess').and.callThrough();
        spyOn(view.baseView, 'loadAssessmentModules').and.callThrough();

        // Select rubric options
        var optionsSelected = {};
        optionsSelected['Criterion 1'] = 'Poor';
        optionsSelected['Criterion 2'] = 'Fair';
        optionsSelected['Criterion 3'] = 'Good';
        view.rubric.optionsSelected(optionsSelected);

        // Submit the assessment
        view.assess();

        // Expect that the assessment was sent to the server
        expect(server.trainingAssess).toHaveBeenCalledWith(optionsSelected);

        // Expect that the steps were reloaded
        expect(view.baseView.loadAssessmentModules).toHaveBeenCalled();
    });
});