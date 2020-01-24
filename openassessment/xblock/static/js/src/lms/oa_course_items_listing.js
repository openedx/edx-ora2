(function(OpenAssessment) {
    'use strict';

    OpenAssessment.CourseItemsListingView = function(runtime, element) {
        var self = this;
        var $section = $(element);
        var block = $section.find('.open-response-assessment-block');
        var itemViewEnabled = (parseInt(block.data('item-view-enabled')) === 1) && XBlock;
        var dataRendered = parseInt(block.data('rendered'));

        this.$section = $section;
        this.runtime = runtime;
        this.oraData = $.parseJSON($('#open-response-assessment-items').text());

        if (!dataRendered) { // if rendered, we're returning after tabbing away
            $section.find('.open-response-assessment-content').hide();
            $section.find('.open-response-assessment-item').hide();
            $section.find('.open-response-assessment-msg').show();
        }

        var AssessmentCell = Backgrid.UriCell.extend({
            staff: false,
            render: function() {
                this.$el.empty();
                var url = this.model.get(this.staff ? 'url_grade_available_responses' : 'url_base');
                var rawValue = this.model.get(this.column.get('name'));
                var staffAssessment = this.model.get('staff_assessment');
                var formattedValue = this.formatter.fromRaw(rawValue, this.model);
                var link = null;
                if (itemViewEnabled && (!this.staff || (this.staff && staffAssessment))) {
                    link = $('<a>', {
                        text: formattedValue,
                        title: this.title || formattedValue,
                    });
                    this.$el.append(link);
                    link.on('click', $.proxy(self, 'displayOraBlock', url));
                } else {
                    this.$el.append(formattedValue);
                }
                this.delegateEvents();
                return this;
            },
        });

        var StaffCell = AssessmentCell.extend({
            staff: true,
        });

        this._columns = [
            {
                name: 'parent_name', label: gettext('Unit Name'), label_summary: gettext('Units'),
                cell: 'string', num: false, editable: false,
            },
            {
                name: 'name', label: gettext('Assessment'), label_summary: gettext('Assessments'),
                cell: AssessmentCell, num: false, editable: false,
            },
            {
                name: 'total', label: gettext('Total Responses'), label_summary: gettext('Total Responses'),
                cell: 'string', num: true, editable: false,
            },
            {
                name: 'training', label: gettext('Training'), label_summary: gettext('Training'),
                cell: 'string', num: true, editable: false,
            },
            {
                name: 'peer', label: gettext('Peer'), label_summary: gettext('Peer'),
                cell: 'string', num: true, editable: false,
            },
            {
                name: 'self', label: gettext('Self'), label_summary: gettext('Self'),
                cell: 'string', num: true, editable: false,
            },
            {
                name: 'waiting', label: gettext('Waiting'), label_summary: gettext('Waiting'),
                cell: 'string', num: true, editable: false,
            },
            {
                name: 'staff', label: gettext('Staff'), label_summary: gettext('Staff'),
                cell: StaffCell, num: true, editable: false,
            },
            {
                name: 'done',
                label: gettext('Final Grade Received'),
                label_summary: gettext('Final Grade Received'),
                cell: 'string',
                num: true,
                editable: false,
            },
        ];
    };

    OpenAssessment.CourseItemsListingView.prototype.refreshGrids = function(force) {
        force = force || false;

        var self = this;
        var $section = this.$section;
        var block = $section.find('.open-response-assessment-block');
        var dataUrl = this.runtime.handlerUrl($section, 'get_ora2_responses');
        var dataRendered = parseInt(block.data('rendered'));

        if (!dataRendered || force) {
            // eslint-disable-next-line new-cap
            return $.Deferred(
                function(defer) {
                    $.ajax({
                        type: 'GET',
                        dataType: 'json',
                        url: dataUrl,
                    }).done(function(data) {
                        self.renderGrids(data);
                        defer.resolve();
                    }).fail(function(data, textStatus) {
                        $section.find('.open-response-assessment-msg')
                            .text(gettext('List of Open Assessments is unavailable'));
                        defer.rejectWith(self, [textStatus]);
                    });
                }
            ).promise();
        }
    };

    OpenAssessment.CourseItemsListingView.prototype.renderGrids = function(data) {
        var self = this;
        var $section = this.$section;
        var block = $section.find('.open-response-assessment-block');
        var oraSteps = ['training', 'peer', 'self', 'waiting', 'staff', 'done'];

        $.each(self.oraData, function(i, oraItem) {
            var total = 0;
            var itemId = oraItem.id;

            $.each(oraSteps, function(j, step) {
                oraItem[step] = 0;
            });

            if (itemId in data) {
                _.extend(oraItem, data[itemId]);
                if (oraItem.staff_assessment) {
                    oraItem.staff = oraItem.waiting;
                    oraItem.waiting = 0;
                }
            }

            $.each(oraSteps, function(j, step) {
                total += oraItem[step];
            });

            oraItem.total = total;
        });

        block.data('rendered', 1);
        $section.find('.open-response-assessment-msg').hide();
        self.showSummaryGrid(self.oraData);
        self.showOpenResponsesGrid(self.oraData);
    };

    OpenAssessment.CourseItemsListingView.prototype.showSummaryGrid = function(data) {
        var $section = this.$section;
        var summaryData = [];
        var summaryDataMap = {};

        $section.find('.open-response-assessment-summary').empty();

        $.each(this._columns, function(index, v) {
            summaryData.push({
                title: v.label_summary,
                value: 0,
                num: v.num,
                class: v.name,
            });
            summaryDataMap[v.name] = index;
        });

        $.each(data, function(index, obj) {
            $.each(obj, function(key, value) {
                var idx = 0;
                if (key in summaryDataMap) {
                    idx = summaryDataMap[key];
                    if (summaryData[idx].num) {
                        summaryData[idx].value += value;
                    } else {
                        summaryData[idx].value += 1;
                    }
                }
            });
        });

        var templateData = _.template($('#open-response-assessment-summary-tpl').text());
        $section.find('.open-response-assessment-summary').append(templateData({
            oraSummary: summaryData,
        }));
    };

    OpenAssessment.CourseItemsListingView.prototype.showOpenResponsesGrid = function(data) {
        var $section = this.$section;
        $section.find('.open-response-assessment-content').show();
        var collection = new Backbone.Collection(data);

        $section.find('.open-response-assessment-main-table').empty();

        var grid = new Backgrid.Grid({
            columns: this._columns,
            collection: collection,
        });

        $section.find('.open-response-assessment-main-table').append(grid.render().el);
    };

    OpenAssessment.CourseItemsListingView.prototype.displayOraBlock = function(url) {
        var $section = this.$section;
        var self = this;

        $section.find('.open-response-assessment-content').hide();
        $section.find('.open-response-assessment-msg').text(gettext('Please wait')).show();

        // eslint-disable-next-line new-cap
        return $.Deferred(
            function(defer) {
                $.ajax({
                    type: 'GET',
                    dataType: 'json',
                    url: url,
                }).done(function(data) {
                    var el = $section.find('.open-response-assessment-item');
                    var block = el.find('.open-response-assessment-item-block');

                    $section.find('.open-response-assessment-msg').hide();
                    el.show();
                    self.renderBreadcrumbs();
                    block.html(data.html);

                    XBlock.initializeBlock($(block).find('.xblock')[0]);

                    defer.resolve();
                }).fail(function(data, textStatus) {
                    $section.find('.open-response-assessment-item').show();
                    $section.find('.open-response-assessment-msg')
                        .text(gettext('Block view is unavailable'));

                    self.renderBreadcrumbs();
                    defer.rejectWith(self, [textStatus]);
                });
            }
        ).promise();
    };

    OpenAssessment.CourseItemsListingView.prototype.renderBreadcrumbs = function() {
        var $section = this.$section;
        var breadcrumbs = $section.find('.open-response-assessment-item-breadcrumbs');
        var text = gettext('Back to Full List');
        var fullListItem = $('<a>', {
            html: '&larr;&nbsp;' + text,
            title: text,
        });

        breadcrumbs.append(fullListItem);
        fullListItem.on('click', $.proxy(this, 'backToOpenResponsesGrid'));
    };

    OpenAssessment.CourseItemsListingView.prototype.backToOpenResponsesGrid = function() {
        var $section = this.$section;
        $section.find('.open-response-assessment-item-breadcrumbs').empty();
        $section.find('.open-response-assessment-item-block').empty();
        $section.find('.open-response-assessment-item').hide();
        $section.find('.open-response-assessment-msg').text(gettext('Please wait')).show();
        this.refreshGrids(true);
    };
})(OpenAssessment);
