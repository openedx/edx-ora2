import React from 'react';
import ReactDOM from 'react-dom';
import App from './components/WaitingStepList';

export class ReactView {
  constructor(runtime, element, data) {
    this.runtime = runtime;
    this.element = element;
    this.data = data;
    this.initializeReact = this.initializeReact.bind(this);
    this.initializeReact();
  }

  initializeReact() {
    const rootElement = document.getElementById(
      `openassessment-react-${this.data.XBLOCK_LOCATION}`,
    );
    ReactDOM.render(
      <App data={this.data} />,
      rootElement,
    );
  }
}

export const initReactView = (runtime, element, data) => {
  $(($) => {
    const xblock = new ReactView(runtime, element, data);
  });
};

export default initReactView;
