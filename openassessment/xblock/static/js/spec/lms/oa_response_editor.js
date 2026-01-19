import ResponseEditorLoader from 'lms/oa_response_editor'


/**
 * Tests for ResponseEditorLoader
 */
describe("OpenAssessment.ResponseEditorLoader", function () {

    let cssFile = '/example/css/file.css'

    let availableEditors = {
        'text': {
            'js': ['/base/js/src/lms/editors/oa_editor_textarea.js'],
            'css': [ cssFile ]
        },
        'tinymce': {
            'js': ['/base/js/src/lms/editors/oa_editor_tinymce.js']
        }
    }

    let response = 'generic response'

    describe('Simple text editor', () => {
        let loader;
        let originalRequire;
        beforeEach(() => {
            originalRequire = window.require;
            window.require = function(modules, callback) {
                const MockEditorTextarea = function() {
                    return {
                        elements: null,
                        load: function(elements) {
                            this.elements = elements;
                            return Promise.resolve();
                        },
                        response: function(texts) {
                            if (typeof texts !== 'undefined') {
                                this._response = texts;
                                return this._response;
                            }
                            return this._response || [];
                        },
                        setOnChangeListener: function(callback) {
                            this._changeCallback = callback;
                        }
                    };
                };
                setTimeout(() => callback(MockEditorTextarea), 0);
            };
            loader = new ResponseEditorLoader(availableEditors);
        });
        afterEach(() => {
            window.require = originalRequire;
        });

        it('Loads text editor js and css properly', function (done) {
            let elements = $('textarea');

            loader.load('text', elements).then(editor => {
                // editor is an instance of oa_editor_textarea
                // it should have `elements` property set to given one
                expect(editor.elements).toBe(elements);

                // css file should also be included
                expect($(`link[href='${cssFile}']`).length).toBe(1);
                done();
            });
        });

        it('Text area editor get instantiated properly', function(done) {
            let elements = $('textarea');
            loader.load('text', elements).then(editor => {
                editor.response([response]);
                expect(editor.response()).toEqual([response]);
                done();
            });
        });
    })

    describe('WYSIWYG text editor', () => {
        let loader;
        let elements;
        let originalRequire;
    
        beforeEach(() => {
            originalRequire = window.require;
            window.require = function(modules, callback) {
                const MockEditorTinyMCE = function() {
                    return {
                        elements: null,
                        load: function(elements) {
                            this.elements = elements;
                            return Promise.resolve();
                        },
                        response: function() {
                            return response;
                        }
                    };
                };
                setTimeout(() => callback(MockEditorTinyMCE), 0);
            };
            loader = new ResponseEditorLoader(availableEditors);
            elements = $('textarea');
        });
        afterEach(() => {
            window.require = originalRequire;
        });

        it('Loads tinymce editor js and css properly', function (done) {
            loader.load('tinymce', elements).then(editor => {
                // editor is an instance of oa_editor_tinymce
                // it should have `elements` property set to given one
                expect(editor.elements).toBe(elements);
                done();
            });
        });

        it('TinyMCE editor get instantiated properly', function(done) {
            loader.load('tinymce', elements).then(editor => {
                // editor should have response even after the delay
                expect(editor.response()).toBe(response);
                done();
            });
        });
    })
})