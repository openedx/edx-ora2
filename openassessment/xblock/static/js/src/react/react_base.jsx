import React from 'react';
import ReactDOM from 'react-dom';

import { IntlProvider } from 'react-intl';
import OraProvider from './ora_provider';

import Loading from './components/loading';

import '../../../sass/react.scss';

export function RenderReact(runtime, element, data) {
  const reactElement = element.lastElementChild;
  const {
    PAGE_NAME, IS_DEV_SERVER, PROPS,
  } = data;

  // this is necessary for webpack-dev-server to work
  // eslint-disable-next-line
  if (!IS_DEV_SERVER) { __webpack_public_path__ = `${window.baseUrl}dist/`; }

  const Page = React.lazy(async () => {
    try {
      // There seems to be a bug in babel-eslint that causes the checker to crash with the following error
      // if we use a template string here:
      //     TypeError: Cannot read property 'range' of null with using template strings here.
      // Ref: https://github.com/babel/babel-eslint/issues/530
      // eslint-disable-next-line
      return await import(`./pages/${PAGE_NAME}`);
    } catch (error) {
      console.error(error);
      return null;
    }
  });

  ReactDOM.render(
    <React.Suspense fallback={<Loading />}>
      <OraProvider runtime={runtime} element={element} data={data}>
        <IntlProvider locale="en">
          <Page {...PROPS} />
        </IntlProvider>
      </OraProvider>
    </React.Suspense>,
    reactElement,
  );
}

window.RenderReact = RenderReact;
export default RenderReact;
