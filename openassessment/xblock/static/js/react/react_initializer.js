/* eslint-disable no-new */
import { ReactRenderer } from './ReactRenderer';

import { InstructorDashboard } from './containers/InstructorDashboard';

/**
 * Plan for dynamic loading but these files have to share React, ReactDom from webpack config

window.ora = window.ora || {};
const loadScript = function (component_url, component_name) {
  return new Promise(function (resolve, reject) {
    if (window.ora[component_name]) resolve();
    else {
      const script = document.createElement('script');
      script.src = component_url;

      script.addEventListener('load', resolve);

      document.head.appendChild(script);
    }
  });
};
loadScript(component_url, component_name).then(() => {
  // debugger
  new ReactRenderer({
      component: window.ora[component_name],
      element: element,
      props
    });
});

 */

const bucket = {
  InstructorDashboard
}


window.initialize_react = function (runtime, element, data) {
  const { component_name, props } = data;

  new ReactRenderer({
    component: bucket[component_name],
    element: element,
    props,
  });
};
