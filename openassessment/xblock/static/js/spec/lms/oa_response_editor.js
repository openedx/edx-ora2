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
        }
    }

    it('Loads editor js and css properly', function (done) {
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

})
