import React, { useContext } from 'react';
import { Hyperlink } from '@edx/paragon';
import { OAListingContext } from '../../../oa_listing_provider';

function AssessmentCell({ row, column }) {
  const { oraItemViewEnabled, displayOraBlock } = useContext(OAListingContext);
  const record = row.original;
  const url = record.url_base;
  const value = record[column.id] || 0;
  if (oraItemViewEnabled) {
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

export default AssessmentCell;
