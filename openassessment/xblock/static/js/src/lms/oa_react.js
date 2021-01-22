import React from 'react';
import ReactDOM from 'react-dom';
import PropTypes from 'prop-types';


export class App extends React.Component {
  render() {
    return (
      <div className="webpack-react-app">
        ORA REACT APP!
      </div>
    );
  }
}

App.propTypes = {
  data: PropTypes.object,
};

/* Javascript for webpack_xblock. */
export class SimpleReactView {
  constructor(runtime, element, data) {
    this.runtime = runtime;
    this.element = element;
    this.data = data;
    this.initializeReact = this.initializeReact.bind(this);
    this.initializeReact();
  }


  initializeReact() {
    console.log("Initialize React!");
    const rootElement = document.getElementById(
      `openassessment-react-${this.data.XBLOCK_LOCATION}`
    );
    console.log({
      rootElement,
      location: this.data.XBLOCK_LOCATION,
      oraReactData: this.data
    });
    ReactDOM.render(
      <div className="webpack-xblock-react-wrapper">
        <App data={this.data}/>
      </div>,
      rootElement
    )
  }
}

export const initReactView = (runtime, element, data) => {
  $(($) => {
    const xblock = new SimpleReactView(runtime, element, data);
  });
}

export default initReactView;
