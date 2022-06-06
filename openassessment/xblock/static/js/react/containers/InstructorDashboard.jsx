import React from 'react';
import { DataTable } from '@edx/paragon';

export const InstructorDashboard = ({
  ora_items,
  ora_item_view_enabled,
  enhanced_staff_grader,
  ora_grading_microfrontend_url,
}) => {
  const data = JSON.parse(ora_items);
  const itemViewEnabled = ora_item_view_enabled && XBlock;

  const esgEnabled = enhanced_staff_grader;
  const esgRootUrl = ora_grading_microfrontend_url;

  const AssessmentCell = ({ row, column, value }) => {
    const name = column.id;
    const rawValue = row[name];
    // debugger
    if (
      itemViewEnabled
      // && (!this.type || (this.type && hasAssessmentType)) &&
      // this.shouldShowLink()
    ) {
      // link = $('<a>', {
      //   text: formattedValue,
      //   title: this.title || formattedValue,
      // });
      // this.$el.append(link);
      // link.on('click', $.proxy(self, 'displayOraBlock', url));
      return <a>Display Ora Block</a>
    }
    return <div>{value}</div>;
  };

  // const AssessmentCell = Backgrid.UriCell.extend({
  //   type: null,
  //   url: null,
  //   // Should be removed as a part of AU-617
  //   shouldShowLink() {
  //     return true;
  //   },
  //   render() {
  //     this.$el.empty();
  //     const name = this.column.get('name');
  //     this.$el.addClass(name);
  //     const url = this.model.get(this.url ? this.url : 'url_base');
  //     const rawValue = this.model.get(name);
  //     const formattedValue = this.formatter.fromRaw(rawValue, this.model);
  //     const hasAssessmentType = this.model.get(this.type ? this.type : 'staff_assessment');
  //     let link = null;
  //     if (itemViewEnabled && (!this.type || (this.type && hasAssessmentType)) && this.shouldShowLink()) {
  //       link = $('<a>', {
  //         text: formattedValue,
  //         title: this.title || formattedValue,
  //       });
  //       this.$el.append(link);
  //       link.on('click', $.proxy(self, 'displayOraBlock', url));
  //     } else {
  //       this.$el.append(formattedValue);
  //     }
  //     this.delegateEvents();
  //     return this;
  //   },
  // });

  const ESGCell = ({row}) => {
    const displayValue = esgEnabled ? gettext('View and grade responses') : gettext('Demo the new Grading Experience');
    const { id, staff_assessment, team_assignment } = row;
    const url = `${esgRootUrl}/${id}`;
    
    return staff_assessment && team_assignment ? <a href={url}>{displayValue}</a>: null;
  };

  // const StaffCell = AssessmentCell.extend({
  //   url: 'url_grade_available_responses',
  //   type: 'staff_assessment',
  //   // Should be removed as a part of AU-617
  //   shouldShowLink() {
  //     return this.model.get('team_assignment') || !esgEnabled;
  //   },
  // });

  return (
    <DataTable
      columns={[
        {
          accessor: 'parent_name',
          Header: gettext('Unit Name'),
        },
        {
          accessor: 'name',
          Header: gettext('Assessment'),
          Cell: AssessmentCell,
        },
        {
          accessor: 'total',
          Header: gettext('Total Responses'),
        },
        {
          accessor: 'training',
          Header: gettext('Training'),
        },
        {
          accessor: 'peer',
          Header: gettext('Peer'),
        },
        {
          accessor: 'self',
          Header: gettext('Self'),
        },
        {
          accessor: 'waiting',
          Header: gettext('Waiting'),
          cell: AssessmentCell,
          type: 'peer_assessment',
          url: 'url_waiting_step_details',
        },
        {
          accessor: 'staff',
          Header: gettext('Staff'),
          // cell: StaffCell,
        },
        {
          accessor: 'done',
          Header: gettext('Final Grade Received'),
        },
        {
          accessor: 'staff_grader',
          Header: gettext('Staff Grader'),
          cell: ESGCell,
        },
      ]}
      itemCount={data.length}
      data={data}
    >
      {/* <DataTable.TableControlBar /> */}
      <DataTable.Table />
      <DataTable.EmptyTable content='No results found' />
      <DataTable.TableFooter />
    </DataTable>
  );
};

export default InstructorDashboard;

// window.ora = window.ora || {};
// window.ora.InstructorDashboard = InstructorDashboard;
