import React, { useCallback, useContext, useState } from 'react';

import axios from 'axios';

import { Alert } from '@edx/paragon';
import { OraContext } from '../../../ora_provider';

// Create a new context
export const OAListingContext = React.createContext();

// Create the provider component
const OAListingProvider = ({ oraItems, oraItemViewEnabled, children }) => {
  const { data, handlerUrl } = useContext(OraContext);
  const [oraData, setOraData] = useState(JSON.parse(oraItems));
  const [showOraBlock, setShowOraBlock] = useState(false);
  const [errMessage, setErrMessage] = useState('');

  const renderGrids = useCallback((newData = {}) => {
    const oraSteps = ['training', 'peer', 'self', 'waiting', 'staff', 'done'];

    const newOraData = [];
    oraData.forEach((oraItem) => {
      let total = 0;
      const itemId = oraItem.id;

      if (itemId in newData) {
        oraItem = { ...oraItem, ...newData[itemId] };
        if (oraItem.staff_assessment) {
          oraItem.staff = oraItem.waiting;
          oraItem.waiting = 0;
        }
      }

      oraSteps.forEach((step) => {
        oraItem[step] = oraItem[step] || 0;
        total += oraItem[step];
      });

      oraItem.total = total;

      newOraData.push({ ...oraItem });
    });
    setOraData(newOraData);
  });

  const refreshGrid = useCallback(() => {
    const dataUrl = handlerUrl('get_ora2_responses');
    setErrMessage('');
    axios
      .get(dataUrl, {
        'Content-Type': 'application/json;charset=UTF-8',
        'Access-Control-Allow-Origin': '*',
      })
      .then((response) => {
        renderGrids(response.data);
        setShowOraBlock(false);
      })
      .catch(() => {
        setErrMessage('List of Open Assessments is unavailable');
      });
  });

  const displayOraBlock = useCallback((url) => {
    setErrMessage('');
    axios
      .get(url, {
        headers: {
          'Content-Type': 'application/json;charset=UTF-8',
          'Access-Control-Allow-Origin': '*',
        },
      })
      .then((response) => {
        // this still need to be manually insert and remove at the moment.
        const block = $('#ora-display-proxy');

        block.html(response.data.html);
        XBlock.initializeBlock($(block).find('.xblock')[0]);
        setShowOraBlock(true);
      })
      .catch(() => {
        setErrMessage('Block view is unavailable');
      });
  });

  const backToOpenResponsesGrid = useCallback(() => {
    const block = $('#ora-display-proxy');
    block.empty();
    refreshGrid();
  });

  const esgEnabled = data.context?.ENHANCED_STAFF_GRADER;
  const esgRootUrl = data.context?.ORA_GRADING_MICROFRONTEND_URL;

  return (
    <OAListingContext.Provider
      value={{
        esgEnabled,
        esgRootUrl,
        oraData,
        oraItemViewEnabled,
        refreshGrid,
        showOraBlock,
        displayOraBlock,
        backToOpenResponsesGrid,
      }}
    >
      {errMessage && <Alert variant="danger">{errMessage}</Alert>}
      {children}
    </OAListingContext.Provider>
  );
};

export default OAListingProvider;
