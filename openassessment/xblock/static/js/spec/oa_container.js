/**
 Tests for the Openassessment Container Object.
 **/

describe("OpenAssessment.Container", function () {

    var container = null;
    beforeEach(function () {
        jasmine.getFixtures().fixturesPath = 'base/fixtures';
        loadFixtures('oa_edit.html');

        container = new OpenAssessment.Container(
            $('#openassessment_criterion_list'),
            {
                'openassessment_criterion': OpenAssessment.RubricCriterion
            }
        )
    });

    it("adds a criterion", function () {
        var previousSize = $('.openassessment_criterion').length;
        container.add('openassessment_criterion');
        var newSize = $('.openassessment_criterion').length;
        expect(newSize).toEqual(previousSize + 1);
    });

    it("removes a criterion", function () {
        container.add('openassessment_criterion');
        var previousSize = $('.openassessment_criterion').length;
        container.remove(1);
        var newSize = $('.openassessment_criterion').length;
        expect(newSize).toEqual(previousSize - 1);
    });

    it("requests an invalid template", function () {
        var error = false;
        try{
            container.getHtmlTemplate('not_a_template');
        } catch (e) {
            error = true;
        }
        expect(error).toBe(true);
    });

    it("installs delete buttons", function () {
        container.installDeleteButtons($('#openassessment_criterion_list'));
    });

    it("parses out unacceptable container items", function () {
        container.element.append("<p> Hello, not an element here. </p>");
        var error = false;
        try{
            container.getItemValues();
        } catch (e) {
            error = true;
        }
        expect(error).toBe(true);
    });

    it("returns correct item dictionary", function () {
        var items = container.getItemValues();
        var item = items[0];

        expect(item.name).toEqual(jasmine.any(String));
        expect(item.prompt).toEqual(jasmine.any(String));
        expect(item.feedback).toEqual(jasmine.any(String));
        expect(item.options).toEqual(jasmine.any(Array));
        expect(item.options[0].name).toEqual(jasmine.any(String));
        expect(parseInt(item.options[0].points)).toEqual(jasmine.any(Number));
        expect(item.options[0].explanation).toEqual(jasmine.any(String));

    });

    it("checks for undefined selection type", function () {
        var error = false;
        try{
            container.add("lolz this isn't a valid selection type");
        } catch (e) {
            error = true;
        }
        expect(error).toBe(true);
    });
});