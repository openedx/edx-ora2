import EditSettingsView from 'studio/oa_edit_settings';

/**
Tests for the edit settings view.
**/
describe("OpenAssessment.EditSettingsView", function() {

    var StubView = function(name, descriptionText) {
        this.name = name;
        this.isValid = true;

        var validationErrors = [];

        this.description = function() {
            return { dummy: descriptionText };
        };

        var _enabled = true;
        this.isEnabled = function(isEnabled) {
            if (typeof(isEnabled) !== "undefined") { this._enabled = isEnabled; }
            return this._enabled;
        };

        this.element = $('<div>', {id: name});

        this.validate = function() {
            return this.isValid;
        };

        this.setValidationErrors = function(errors) { validationErrors = errors; };
        this.validationErrors = function() { return validationErrors; };
        this.clearValidationErrors = function() { validationErrors = []; };
    };

    var view = null;
    var assessmentViews = null;
    var data = null;

    // The Peer and Self Editor ID's
    var PEER = "oa_peer_assessment_editor";
    var SELF = "oa_self_assessment_editor";
    var TRAINING = "oa_student_training_editor";
    var STAFF = "oa_staff_assessment_editor";

    beforeEach(function() {
        // Load the DOM fixture
        loadFixtures('oa_edit.html');

        // Create the stub assessment views
        assessmentViews = {};
        assessmentViews[SELF] = new StubView("self-assessment", "Self assessment description");
        assessmentViews[PEER] = new StubView("peer-assessment", "Peer assessment description");
        assessmentViews[TRAINING] = new StubView("student-training", "Student Training description");
        assessmentViews[STAFF] = new StubView("staff-assessment", "Staff assessment description");

        // mock data from backend
        data = {
            ALLOWED_IMAGE_EXTENSIONS: ['png', 'jpg', 'gif'],
            ALLOWED_FILE_EXTENSIONS: ['pdf', 'md'],
            FILE_EXT_BLACK_LIST: ['exe', 'app'],
        };

        // Create the view
        var element = $("#oa_basic_settings_editor").get(0);
        view = new EditSettingsView(element, assessmentViews, data);
    });

    it("sets and loads display name", function() {
        view.displayName("");
        expect(view.displayName()).toEqual("");
        view.displayName("This is the name of the problem!");
        expect(view.displayName()).toEqual("This is the name of the problem!");
    });

    it("sets and loads the file upload state", function() {
        view.fileUploadResponseNecessity('optional', true);
        view.fileUploadType('image');
        expect(view.fileUploadType()).toBe('image');
        view.fileUploadType('pdf-and-image');
        expect(view.fileUploadType()).toBe('pdf-and-image');
        view.fileUploadType('custom');
        expect(view.fileUploadType()).toBe('custom');

        view.fileUploadResponseNecessity('', true);
        expect(view.fileUploadType()).toBe('');

        view.fileUploadResponseNecessity('required', true);
        expect(view.fileUploadType()).toBe('custom');
    });

    it("sets and loads the file type white list", function() {
        view.fileTypeWhiteList('pdf,gif,png,doc');
        expect(view.fileTypeWhiteList()).toBe('pdf,gif,png,doc');

        view.fileTypeWhiteList('');
        expect(view.fileTypeWhiteList()).toBe('');
    });

    it("sets and loads the leaderboard number", function() {
        view.leaderboardNum(18);
        expect(view.leaderboardNum()).toEqual(18);

        view.leaderboardNum(0);
        expect(view.leaderboardNum()).toEqual(0);
    });

    it("validates the leaderboard number field", function() {
        // Valid value for the leaderboard number
        view.leaderboardNum(0);
        expect(view.validate()).toBe(true);
        expect(view.validationErrors()).toEqual([]);

        // Below the minimum
        view.leaderboardNum(-1);
        expect(view.validate()).toBe(false);
        expect(view.validationErrors()).toContain(
            "Leaderboard number is invalid"
        );

        // Clear validation errors
        view.clearValidationErrors();
        expect(view.validationErrors()).toEqual([]);

        // Valid, near the maximum
        view.leaderboardNum(100);
        expect(view.validate()).toBe(true);

        // Above the maximum
        view.leaderboardNum(101);
        expect(view.validate()).toBe(false);
    });

    it("validates file upload type and white list fields", function() {
        view.fileUploadResponseNecessity('optional', true);

        view.fileUploadType("image");
        expect(view.validate()).toBe(true);
        expect(view.validationErrors().length).toBe(0);

        // expect white list field is not empty when upload type is custom
        view.fileUploadType("custom");
        view.fileTypeWhiteList('');
        expect(view.validate()).toBe(false);
        expect(view.validationErrors()).toContain('File types can not be empty.');

        // expect white list field doesn't contain black listed exts
        view.fileUploadType("custom");
        view.fileTypeWhiteList("pdf, EXE, .app");
        expect(view.validate()).toBe(false);
        expect(view.validationErrors()).toContain('The following file types are not allowed: exe,app');
    });

    it('shows and enables/disables extension list for preset file upload types', function() {
        var fileTypesSelector = '#openassessment_submission_white_listed_file_types',
            extensionBanner = '#openassessment_submission_white_listed_file_types_wrapper .extension-warning';

        view.fileUploadResponseNecessity('optional', true);

        // Custom uploads allow for entering extensions, and hides the note about custom uploads
        view.fileUploadType('custom');
        expect($(fileTypesSelector).prop('disabled')).toBe(false);
        expect(view.isHidden($(extensionBanner))).toBe(true);

        // Image/PDF uploads populate with the correct extensions, are disabled, and show a note about adding extensions
        view.fileUploadType('image');
        expect(view.fileTypeWhiteList()).toBe('png, jpg, gif');
        expect($(fileTypesSelector).prop('disabled')).toBe(true);
        expect(view.isHidden($(extensionBanner))).toBe(false);

        view.fileUploadType('image-and-pdf');
        expect(view.fileTypeWhiteList()).toBe('pdf, md');
        expect($(fileTypesSelector).prop('disabled')).toBe(true);
        expect(view.isHidden($(extensionBanner))).toBe(false);
    });

    it("enables the teamset selector when teams are enabled, and disabled it otherwise", function() {
        view.teamsEnabled(false);
        expect(view.teamsEnabled()).toBe(false);

        view.teamsEnabled(true);
        expect(view.teamsEnabled()).toBe(true);
    });

    it('hides the training, self, and peer assessment types when teams are enabled', function() {
        // Default config: teams are disabled, all assessments shown
        view.teamsEnabled(false);
        expect(view.teamsEnabled()).toBe(false);

        var allAssessmentTypes = [SELF, TRAINING, PEER, STAFF];
        allAssessmentTypes.forEach(function(type) {
            var selector = $(assessmentViews[type].element);
            expect(view.isHidden(selector)).toBe(false);
        });

        // Teams config: only staff assessments supported, others hidden
        view.teamsEnabled(true);
        expect(view.teamsEnabled()).toBe(true);

        var shownForTeamAssessments = [STAFF];
        var hiddenForTeamAssessments = [SELF, TRAINING, PEER];

        hiddenForTeamAssessments.forEach(function(type) {
            var selector = $(assessmentViews[type].element);
            expect(view.isHidden(selector)).toBe(true);
        });

        shownForTeamAssessments.forEach(function(type) {
            var selector = $(assessmentViews[type].element);
            expect(view.isHidden(selector)).toBe(false);
        });

        // for team assessments, it also automatically selects 'staff-assessment'
        expect(assessmentViews[STAFF].isEnabled()).toBe(true);
    });

    it('disables leaderboard and shows warnings when teams are enabled', function() {
        var warning_selectors = [
          '#openassessment_leaderboard_wrapper .teams-warning',
          '#openassessment_leaderboard_wrapper .disabled-label',
        ];

        // Default config: teams are disabled, warnings are hidden and input is enabled
        view.teamsEnabled(false);
        expect(view.teamsEnabled()).toBe(false);
        warning_selectors.forEach(function(selector) {
          expect(view.isHidden($(selector))).toBe(true);
        });
        expect($('#openassessment_leaderboard_editor').prop('disabled')).toBe(false);

        // Teams config: teams are enabled, so warnings are shown and input is disabled
        view.teamsEnabled(true);
        expect(view.teamsEnabled()).toBe(true);

        warning_selectors.forEach(function(selector) {
          expect(view.isHidden($(selector))).toBe(false);
        });
        expect($('#openassessment_leaderboard_editor').prop('disabled')).toBe(true);
    });
});
