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
        it('Loads text editor js and css properly', function (done) {
            let loader = new ResponseEditorLoader(availableEditors)
            let elements = $('textarea')
            
            loader.load('text', elements).then(editor => {
    
                // editor is an instance of oa_editor_textarea
                // it should have `elements` property set to given one
                expect(editor.elements).toBe(elements)
    
                // css file should also be included
                expect($(`link[href='${cssFile}']`).length).toBe(1)
                done()
            })
        })

        it('Text area editor get instantiated properly', function(done) {
            let loader = new ResponseEditorLoader(availableEditors)
            let elements = $('textarea')
            loader.load('text', elements).then(editor => {
                editor.response([response])
                expect(editor.response(), response)
                done()
            });
        })
    })

    describe('WYSIWYG text editor', () => {
        let loader = new ResponseEditorLoader(availableEditors)
        let elements = $('textarea')
    
        let editorStub = (elements) => ({
            elements,
            response: () => response
        })
    
        beforeEach(() => {
            loader = new ResponseEditorLoader(availableEditors)
            elements = $('textarea')
    
            spyOn(loader, 'load').and.callFake(function(selectedEditor, elements){
                return new Promise(resolve => {
                    setTimeout(() => resolve(editorStub(elements)), 500)
                })
            })
        })
    
        it('Loads tinymce editor js and css properly', function (done) {
            loader.load('tinymce', elements).then(editor => {
                // editor is an instance of oa_editor_tinymce
                // it should have `elements` property set to given one
                expect(editor.elements).toBe(elements)
                done()
            })
        })
    
        it('TinyMCE editor get instantiated properly', async function(done) {
            loader.load('tinymce', elements).then(editor => {
                // editor should have response even after the delay
                expect(editor.response(), response)
                done()
            });
        })
    })
})
