/**
 Tests for course items listing.
 **/

describe("OpenAssessment.CourseItemsListingView", function() {

    // Stubs
    var view = null;
    var rootElement = null;
    var section = null;
    var runtime = {
        handlerUrl: function(el, handler) {
            return '/' + handler;
        }
    };
    window.XBlock = {
        initializeBlock: function(el){}
    };

    var createCourseItemsListingView = function(template) {
        loadFixtures(template);

        section = $('.open-response-assessment-block');
        rootElement = section.parent();
        return new OpenAssessment.CourseItemsListingView(runtime, rootElement);
    };

    var stubAjax = function(success, responseData) {
        spyOn($, 'ajax').and.returnValue(
            $.Deferred(function(defer) {
                if (success) {
                    defer.resolveWith(this, [responseData]);
                } else {
                    defer.reject();
                }
           }).promise()
        );
    };

    var oraCourseItems = {
        "block-v1:SomeOrg+ORA101+2017+type@openassessment+block@9d1af6220a4d4ecbafb22a3506effcce": {
            "name": "Test ORA 1",
            "staff_assessment": false,
            "parent": {
                "id": "block-v1:SomeOrg+ORA101+2017+type@vertical+block@5570454d5dc4469ca75f36dd792ee316",
                "name": "Vertical 1"
            },
            "responses": {
                "training": 0,
                "self": 0,
                "peer": 1,
                "waiting": 1,  // will remain 'waiting'
                "ai": 0,
                "done": 0,
                "cancelled": 0,
                "total": 1,
                "staff": 0
            }
        },
        "block-v1:SomeOrg+ORA101+2017+type@openassessment+block@3ec2343a95734a87af494455f52b1141": {
            "name": "Test ORA 2",
            "staff_assessment": true,
            "parent": {
                "id": "block-v1:SomeOrg+ORA101+2017+type@vertical+block@90b4edff50bc47d9ba037a3180c44e97",
                "name": "Vertical 2"
            },
            "responses": {
                "training": 3,
                "self": 0,
                "peer": 0,
                "waiting": 5,  //will be translated to 'staff'
                "ai": 0,
                "done": 0,
                "cancelled": 0,
                "total": 8,
                "staff": 0
            }
        },
        "block-v1:SomeOrg+ORA101+2017+type@openassessment+block@40b4edfe60bc47d9ba037a3180c44e97": {
            "name": "Test ORA 3",
            "staff_assessment": false,
            "parent": {
                "id": "block-v1:SomeOrg+ORA101+2017+type@openassessment+block@40b4edfe60bc47d9ba037a3180c44e97",
                "name": "Vertical 3"
            },
            "responses": {
                "training": 0,
                "self": 0,
                "peer": 1,
                "waiting": 0,
                "ai": 0,
                "done": 2,
                "cancelled": 0,
                "total": 3,
                "staff": 0
            }
        }
    };

    var testData = [];
    var ora2responses = {};

    $.each(oraCourseItems, function(locationId, oraItem) {
        testData.push({
            "parent_name": oraItem['parent']['name'],
            "name": oraItem['name'],
            "url_grade_available_responses": "/grade_available_responses_view",
            "staff_assessment": oraItem['staff_assessment'],
            "parent_id": oraItem['parent']['id'],
            "url_base": "/student_view",
            "id": locationId
        });
        ora2responses[locationId] = oraItem['responses'];
    });

    beforeEach(function() {
        // Create a new stub server
        view = createCourseItemsListingView('oa_listing_view.html');

        // Add test data
        view.oraData = testData;
    });

    it('shows tables on success callback', function() {
        expect(section.find('.open-response-assessment-msg').is(':visible')).toBe(true);
        expect(section.find('.open-response-assessment-content').is(':visible')).toBe(false);

        spyOn(view, 'showSummaryGrid').and.callThrough();
        spyOn(view, 'showOpenResponsesGrid').and.callThrough();

        stubAjax(true, ora2responses);

        view.refreshGrids();

        expect($.ajax).toHaveBeenCalledWith({
            url: '/get_ora2_responses',
            type: "GET",
            dataType: "json"
        });

        expect(view.showSummaryGrid).toHaveBeenCalled();
        expect(view.showOpenResponsesGrid).toHaveBeenCalled();

        expect(section.find('.open-response-assessment-msg').is(':visible')).toBe(false);
        expect(section.find('.open-response-assessment-content').is(':visible')).toBe(true);

        var expectedArr = [3, 3, 13, 3, 2, 0, 1, 5, 2];
        var summaryRowValuesArr = [];
        section.find('.open-response-assessment-summary td div.ora-summary-value').each(function(i, val) {
            summaryRowValuesArr.push(parseInt($(val).text()));
        });
        expect(summaryRowValuesArr).toEqual(expectedArr);

        var rows = $('.open-response-assessment-main-table tbody tr');
        expect(rows.length).toBe(3);

        var tds = [];
        var td = null;
        $.each(rows, function(i, val){
            td = [];
            $(val).find('td').each(function(j, item){
                td.push($(item).html());
            });
            tds.push(td);
        });

        var expectedTds = [
            ["Vertical 1", '<a title="Test ORA 1">Test ORA 1</a>',
                '2', '0', '1', '0', '1', '0', '0'],
            ["Vertical 2", '<a title="Test ORA 2">Test ORA 2</a>',
                '8', '3', '0', '0', '0', '<a title="5">5</a>', '0'],
            ["Vertical 3", '<a title="Test ORA 3">Test ORA 3</a>',
                '3', '0', '1', '0', '0', '0', '2']
        ];
        expect(tds).toEqual(expectedTds);
    });

    it('shows error on failure callback', function() {
        expect(section.find('.open-response-assessment-msg').is(':visible')).toBe(true);
        expect(section.find('.open-response-assessment-content').is(':visible')).toBe(false);

        spyOn(view, 'showSummaryGrid').and.callThrough();
        spyOn(view, 'showOpenResponsesGrid').and.callThrough();

        stubAjax(false, null);

        view.refreshGrids();

        expect($.ajax).toHaveBeenCalledWith({
            url: '/get_ora2_responses',
            type: "GET",
            dataType: "json"
        });

        expect(view.showSummaryGrid).not.toHaveBeenCalled();
        expect(view.showOpenResponsesGrid).not.toHaveBeenCalled();

        expect(section.find('.open-response-assessment-msg').text())
                      .toEqual('List of Open Assessments is unavailable');
    });

    it('shows ora block after click on title field', function() {
        spyOn(window.XBlock, 'initializeBlock');
        spyOn(view, 'displayOraBlock').and.callThrough();
        spyOn(view, 'renderBreadcrumbs').and.callThrough();
        spyOn(view, 'backToOpenResponsesGrid').and.callThrough();

        view.renderGrids(ora2responses);

        var items = $('.open-response-assessment-main-table tbody tr:first td a');
        var link = items[0];

        stubAjax(true, {html: 'test_html'});

        $(link).trigger('click');

        expect(view.displayOraBlock).toHaveBeenCalledWith(testData[0].url_base, jasmine.any(Object));
        expect($.ajax).toHaveBeenCalledWith({
            url: testData[0].url_base,
            type: "GET",
            dataType: "json"
        });

        expect(view.renderBreadcrumbs).toHaveBeenCalled();
        expect(window.XBlock.initializeBlock).toHaveBeenCalled();

        expect(section.find('.open-response-assessment-msg').is(':visible')).toBe(false);
        expect(section.find('.open-response-assessment-content').is(':visible')).toBe(false);
        expect(section.find('.open-response-assessment-item-block').html()).toBe('test_html');
        expect(section.find('.open-response-assessment-item').is(':visible')).toBe(true);

        var backLinks = section.find('.open-response-assessment-item-breadcrumbs a');
        expect(backLinks.length).toBe(1);
        expect($(backLinks[0]).attr('title')).toBe('Back to Full List');

        $.ajax = jasmine.createSpy().and.returnValue($.Deferred(function(defer) {}).promise());

        $(backLinks[0]).trigger('click');
        expect(view.backToOpenResponsesGrid).toHaveBeenCalled();

        expect(section.find('.open-response-assessment-msg').is(':visible')).toBe(true);
        expect(section.find('.open-response-assessment-content').is(':visible')).toBe(false);
        expect(section.find('.open-response-assessment-item').is(':visible')).toBe(false);
    });

    it('shows error with return back button if xblock view is unavailable', function() {
        spyOn(view, 'displayOraBlock').and.callThrough();
        spyOn(view, 'renderBreadcrumbs').and.callThrough();
        spyOn(view, 'backToOpenResponsesGrid').and.callThrough();

        view.renderGrids(ora2responses);

        var items = $('.open-response-assessment-main-table tbody tr:first td a');
        var link = items[0];

        stubAjax(false, null);

        $(link).trigger('click');

        expect(view.displayOraBlock).toHaveBeenCalledWith(testData[0].url_base, jasmine.any(Object));
        expect($.ajax).toHaveBeenCalledWith({
            url: testData[0].url_base,
            type: "GET",
            dataType: "json"
        });

        expect(section.find('.open-response-assessment-msg').text())
                      .toEqual('Block view is unavailable');

        var backLinks = section.find('.open-response-assessment-item-breadcrumbs a');
        expect(backLinks.length).toBe(1);
        expect($(backLinks[0]).attr('title')).toBe('Back to Full List');
    });

    it('display grade available responses view after click on staff field', function() {
        spyOn(view, 'displayOraBlock').and.callThrough();

        view.renderGrids(ora2responses);

        var items = $('.open-response-assessment-main-table tbody tr td a');
        var link = items[2];

        stubAjax(true, {html: 'test_html'});

        $(link).trigger('click');

        expect(view.displayOraBlock).toHaveBeenCalledWith(testData[0].url_grade_available_responses,
            jasmine.any(Object));
        expect($.ajax).toHaveBeenCalledWith({
            url: testData[0].url_grade_available_responses,
            type: "GET",
            dataType: "json"
        });
    });
});
