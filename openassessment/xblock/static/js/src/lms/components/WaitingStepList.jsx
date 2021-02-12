import React from 'react';
import PropTypes from 'prop-types';
import moment from 'moment';

const getReadableTime = (timestamp) => {
  return moment(timestamp).fromNow(true);
};

const App = ({ data }) => {
  // Gotta find a better and safer way of extracting the data
  // eslint-disable-next-line camelcase
  const { waiting_step_details } = data.CONTEXT;
  return (
    <div className="webpack-react-app">
      This is an intermediate view until the Paragon styles start working.
      <br />
      <br />
      <table>
        <tr>
          <th>Username</th>
          <th>Peers Assessed</th>
          <th>Peer Responses Received</th>
          <th>Time Spent On Current Step</th>
          <th>Staff assessment</th>
          <th>Grade Status</th>
          <th>Individual Grade Override</th>
        </tr>
        {waiting_step_details.map((item) =>{
          const createdAt = getReadableTime(item.created_at);
          return (
            <tr>
              <td>{item.username}</td>
              <td>{item.graded}</td>
              <td>{item.graded_by}</td>
              <td>{createdAt}</td>
            </tr>
          );
        })}
      </table>
    </div>
  );
};

App.propTypes = {
  data: PropTypes.object,
};

export default App;
