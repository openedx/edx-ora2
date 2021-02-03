import React from 'react';
import PropTypes from 'prop-types';

import { Alert, Carousel } from '@edx/paragon';
import "@edx/paragon/dist/paragon.css";

const App = (data) => {
  return (
    <div className="webpack-react-app">
        <Alert>
            This is a test alert using paragon.
        </Alert>
        test?
        The Paragon styles are not loading.
    </div>
  );
};

App.propTypes = {
  data: PropTypes.object,
};

export default App;
