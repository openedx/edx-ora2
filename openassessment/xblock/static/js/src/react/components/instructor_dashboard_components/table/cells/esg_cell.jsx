import React, { useContext } from 'react';
import { Hyperlink } from '@edx/paragon';
import { OAListingContext } from '../../oa_listing_provider';

function EsgCell({ row }) {
  const { esgEnabled, esgRootUrl } = useContext(OAListingContext);
  const record = row.original;
  const url = `${esgRootUrl}/${record.id}`;
  const value = esgEnabled ? gettext('View and grade responses') : gettext('Demo the new Grading Experience');
  const hasAssessmentType = record.staff_assessment;
  const teamAssignment = record.team_assignment;
  if (hasAssessmentType && !teamAssignment) {
    return (
      <Hyperlink
        destination={url}
        className="staff-esg-link"
      >
        {value}
      </Hyperlink>
    );
  }
  return null;
}

export default EsgCell;
