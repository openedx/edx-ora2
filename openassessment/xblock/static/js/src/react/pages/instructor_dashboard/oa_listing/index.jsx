import React from 'react';

import ListingTable from '../../../components/instructor_dashboard_components/table/list_table';
import OAListingProvider from '../../../components/instructor_dashboard_components/oa_listing_provider';
import DisplayOraBlock from '../../../components/instructor_dashboard_components/display_ora_block';

function OAListing(props) {
  const { ora_item_view_enabled: oraItemViewEnabled, ora_items: oraItems } = props;

  return (
    <OAListingProvider
      oraItems={oraItems}
      oraItemViewEnabled={oraItemViewEnabled}
    >
      <DisplayOraBlock />
      <ListingTable />
    </OAListingProvider>
  );
}

export default OAListing;
