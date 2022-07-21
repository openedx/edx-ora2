/* eslint-disable no-new */
import { camelCaseObject } from '@edx/frontend-platform';

const loadJavascript = (url) => new Promise(resolve => {
  const jsElement = document.createElement('script');
  jsElement.onload = resolve;
  jsElement.src = url;
  document.head.append(jsElement);
});

const loadUrls = ({ cssUrl, jsUrl }) => new Promise((resolve) => {
  if (!window.OraReactRenderer) {
    const cssElement = document.createElement('link');
    cssElement.rel = 'stylesheet';
    cssElement.type = 'text/css';
    cssElement.href = cssUrl;
    document.head.append(cssElement);

    loadJavascript(jsUrl).then(resolve);
  } else {
    resolve();
  }
});

const loadComponent = (url) => new Promise(resolve => {
  $.ajax({
    url,
    dataType: 'script',
    // eslint-disable-next-line no-eval
    success: script => resolve(eval(script)),
  });
});

const InitializeReact = async (runtime, element, data) => {
  // camelCaseObject is doing deep camel case
  const {
    componentName, componentUrl, props, prevOraSupport,
  } = camelCaseObject(data);

  await loadUrls(prevOraSupport);
  const module = await loadComponent(componentUrl);

  new window.OraReactRenderer({
    component: module[componentName],
    element,
    props: {
      ...camelCaseObject(props),
      prevOra: {
        runtime,
        element,
        // I do not want object in prev_ora_support to be camelCase
        prevOraSupport: data.prev_ora_support,
      },
    },
  });
};

window.InitializeReact = InitializeReact;
