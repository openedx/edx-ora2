/**
 * API function to retrieve the waiting step details.
 *
 * Args:
 *   waitingStepDataUrl (string): URL of the waiting step details API.
 *
 * Returns:
 *   Object containing the transation status and the waiting step data.
 *   Example reponse:
 *   {
 *     "success": true,
 *     "waitingStepData": { ... } // Object with API response contents
 *   }
 * */
// eslint-disable-next-line import/prefer-default-export
export const fetchWaitingStepDetails = async (waitingStepDataUrl) => {
  let success = false;
  let waitingStepData = {};

  try {
    // Retrieve waiting step data and decode JSON
    const response = await fetch(waitingStepDataUrl);
    waitingStepData = await response.json();
    success = true;
  } catch (requestError) {
    success = false;
  }

  return { success, waitingStepData };
};
