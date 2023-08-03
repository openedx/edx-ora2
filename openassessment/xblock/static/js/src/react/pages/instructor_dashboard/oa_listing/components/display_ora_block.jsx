import React, { useContext } from 'react';

import { Hyperlink } from '@edx/paragon';
import { OAListingContext } from '../oa_listing_provider';

function DisplayOraBlock() {
  const { showOraBlock, backToOpenResponsesGrid } = useContext(OAListingContext);
  return (
    <div className="open-response-assessment-item">
      {showOraBlock && (
        <Hyperlink
          destination=""
          onClick={(e) => {
            e.preventDefault();
            backToOpenResponsesGrid();
          }}
          className="open-response-assessment-item-breadcrumbs"
        >
          Back to Full List
        </Hyperlink>
      )}

      <div id="ora-display-proxy" />
    </div>
  );
}

export default DisplayOraBlock;
