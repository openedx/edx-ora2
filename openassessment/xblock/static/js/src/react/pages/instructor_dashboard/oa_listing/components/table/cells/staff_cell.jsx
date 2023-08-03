import React, { useContext } from 'react';
import { Hyperlink } from '@edx/paragon';
import { OAListingContext } from '../../../oa_listing_provider';

function StaffCell({ row, column }) {
  const { oraItemViewEnabled, esgEnabled, displayOraBlock } = useContext(OAListingContext);
  const record = row.original;
  const url = record.url_base;
  const value = record[column.id] || 0;
  const hasAssessmentType = record.staff_assessment;
  const shouldShowLink = record.team_assignment || !esgEnabled;
  if (oraItemViewEnabled && hasAssessmentType && shouldShowLink) {
    return (
      <Hyperlink
        destination={url}
        onClick={(e) => {
          e.preventDefault();
          displayOraBlock(url);
        }}
      >
        {value}
      </Hyperlink>
    );
  }
  return <span>{value}</span>;
}

export default StaffCell;
