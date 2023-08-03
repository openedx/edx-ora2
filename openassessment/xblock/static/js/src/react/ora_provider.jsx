import React from 'react';

// Create a new context
export const OraContext = React.createContext();

// Create the provider component
const OraProvider = ({
 runtime, element, data, children,
}) => {
  const handlerUrl = (handlerName) => runtime.handlerUrl($(element), handlerName);

  return (
    <OraContext.Provider
      value={{
        runtime,
        element,
        data,
        handlerUrl,
      }}
    >
      {children}
    </OraContext.Provider>
  );
};

export default OraProvider;
