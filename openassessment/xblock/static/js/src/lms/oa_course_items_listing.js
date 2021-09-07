export class CourseItemsListingView {
  constructor(runtime, element, data) {
    const self = this;
    const $section = $(element);
    const block = $section.find('.open-response-assessment-block');
    const itemViewEnabled = (parseInt(block.data('item-view-enabled'), 10) === 1) && XBlock;
    const dataRendered = parseInt(block.data('rendered'), 10);

    this.$section = $section;
    this.runtime = runtime;
    this.oraData = $.parseJSON($('#open-response-assessment-items').text());
    this.data = data;

    if (!dataRendered) { // if rendered, we're returning after tabbing away
      $section.find('.open-response-assessment-content').hide();
      $section.find('.open-response-assessment-item').hide();
      $section.find('.open-response-assessment-msg').show();
    }

    const AssessmentCell = Backgrid.UriCell.extend({
      type: null,
      url: null,
      render() {
        this.$el.empty();
        const url = this.model.get(this.url ? this.url : 'url_base');
        const rawValue = this.model.get(this.column.get('name'));
        const formattedValue = this.formatter.fromRaw(rawValue, this.model);
        const hasAssessmentType = this.model.get(this.type ? this.type : 'staff_assessment');
        let link = null;
        if (itemViewEnabled && (!this.type || (this.type && hasAssessmentType))) {
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

    const WaitingStepCell = AssessmentCell.extend({
      type: 'peer_assessment',
      url: 'url_waiting_step_details',
    });

    const StaffCell = AssessmentCell.extend({
      type: 'staff_assessment',
      url: 'url_grade_available_responses',
    });

    this._columns = [
      {
        name: 'parent_name',
        label: gettext('Unit Name'),
        label_summary: gettext('Units'),
        cell: 'string',
        num: false,
        editable: false,
      },
      {
        name: 'name',
        label: gettext('Assessment'),
        label_summary: gettext('Assessments'),
        cell: AssessmentCell,
        num: false,
        editable: false,
      },
      {
        name: 'total',
        label: gettext('Total Responses'),
        label_summary: gettext('Total Responses'),
        cell: 'string',
        num: true,
        editable: false,
      },
      {
        name: 'training',
        label: gettext('Training'),
        label_summary: gettext('Training'),
        cell: 'string',
        num: true,
        editable: false,
      },
      {
        name: 'peer',
        label: gettext('Peer'),
        label_summary: gettext('Peer'),
        cell: 'string',
        num: true,
        editable: false,
      },
      {
        name: 'self',
        label: gettext('Self'),
        label_summary: gettext('Self'),
        cell: 'string',
        num: true,
        editable: false,
      },
      {
        name: 'waiting',
        label: gettext('Waiting'),
        label_summary: gettext('Waiting'),
        cell: WaitingStepCell,
        num: true,
        editable: false,
      },
      {
        name: 'staff',
        label: gettext('Staff'),
        label_summary: gettext('Staff'),
        cell: StaffCell,
        num: true,
        editable: false,
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
  }

  /* eslint-disable-next-line consistent-return */
  refreshGrids(force) {
    force = force || false;

    const self = this;
    const { $section } = this;
    const block = $section.find('.open-response-assessment-block');
    const dataUrl = this.runtime.handlerUrl($section, 'get_ora2_responses');
    const dataRendered = parseInt(block.data('rendered'), 10);

    if (!dataRendered || force) {
      // eslint-disable-next-line new-cap
      return $.Deferred(
        (defer) => {
          $.ajax({
            type: 'GET',
            dataType: 'json',
            url: dataUrl,
          }).done((data) => {
            self.renderGrids(data);
            defer.resolve();
          }).fail((data, textStatus) => {
            $section.find('.open-response-assessment-msg')
              .text(gettext('List of Open Assessments is unavailable'));
            defer.rejectWith(self, [textStatus]);
          });
        },
      ).promise();
    }
  }

  renderGrids(data) {
    const self = this;
    const { $section } = this;
    const block = $section.find('.open-response-assessment-block');
    const oraSteps = ['training', 'peer', 'self', 'waiting', 'staff', 'done'];

    $.each(self.oraData, (i, oraItem) => {
      let total = 0;
      const itemId = oraItem.id;

      $.each(oraSteps, (j, step) => {
        oraItem[step] = 0;
      });

      if (itemId in data) {
        _.extend(oraItem, data[itemId]);
        if (oraItem.staff_assessment) {
          oraItem.staff = oraItem.waiting;
          oraItem.waiting = 0;
        }
      }

      $.each(oraSteps, (j, step) => {
        total += oraItem[step];
      });

      oraItem.total = total;
    });

    block.data('rendered', 1);
    $section.find('.open-response-assessment-msg').hide();
    self.showSummaryGrid(self.oraData);
    self.showOpenResponsesGrid(self.oraData);
  }

  showSummaryGrid(data) {
    const { $section } = this;
    const summaryData = [];
    const summaryDataMap = {};

    $section.find('.open-response-assessment-summary').empty();

    $.each(this._columns, (index, v) => {
      summaryData.push({
        title: v.label_summary,
        value: 0,
        num: v.num,
        class: v.name,
      });
      summaryDataMap[v.name] = index;
    });

    $.each(data, (index, obj) => {
      $.each(obj, (key, value) => {
        let idx = 0;
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

    const templateData = _.template($('#open-response-assessment-summary-tpl').text());
    $section.find('.open-response-assessment-summary').append(templateData({
      oraSummary: summaryData,
    }));
  }

  showOpenResponsesGrid(data) {
    const { $section } = this;
    $section.find('.open-response-assessment-content').show();
    const collection = new Backbone.Collection(data);

    $section.find('.open-response-assessment-main-table').empty();

    const grid = new Backgrid.Grid({
      columns: this._columns,
      collection,
    });

    $section.find('.open-response-assessment-main-table').append(grid.render().el);
  }

  displayOraBlock(url) {
    const { $section } = this;
    const self = this;

    $section.find('.open-response-assessment-content').hide();
    $section.find('.open-response-assessment-msg').text(gettext('Please wait')).show();

    // eslint-disable-next-line new-cap
    return $.Deferred(
      (defer) => {
        $.ajax({
          type: 'GET',
          dataType: 'json',
          url,
        }).done((data) => {
          const el = $section.find('.open-response-assessment-item');
          const block = el.find('.open-response-assessment-item-block');

          $section.find('.open-response-assessment-msg').hide();
          el.show();
          self.renderBreadcrumbs();
          block.html(data.html);

          XBlock.initializeBlock($(block).find('.xblock')[0]);

          defer.resolve();
        }).fail((data, textStatus) => {
          $section.find('.open-response-assessment-item').show();
          $section.find('.open-response-assessment-msg')
            .text(gettext('Block view is unavailable'));

          self.renderBreadcrumbs();
          defer.rejectWith(self, [textStatus]);
        });
      },
    ).promise();
  }

  renderBreadcrumbs() {
    const { $section } = this;
    const breadcrumbs = $section.find('.open-response-assessment-item-breadcrumbs');
    const text = gettext('Back to Full List');
    const fullListItem = $('<a>', {
      html: `&larr;&nbsp;${text}`,
      title: text,
    });

    breadcrumbs.append(fullListItem);
    fullListItem.on('click', $.proxy(this, 'backToOpenResponsesGrid'));
  }

  backToOpenResponsesGrid() {
    const { $section } = this;
    $section.find('.open-response-assessment-item-breadcrumbs').empty();
    $section.find('.open-response-assessment-item-block').empty();
    $section.find('.open-response-assessment-item').hide();
    $section.find('.open-response-assessment-msg').text(gettext('Please wait')).show();
    this.refreshGrids(true);
  }
}
export default CourseItemsListingView;
