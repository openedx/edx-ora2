import React from 'react';

// Create a new context
export const OraContext = React.createContext();


// Create the provider component
const OraProvider = ({ runtime, element, data, children }) => {
  return (
    <OraContext.Provider value={{
      runtime,
      element,
      data
    }}>
      {children}
    </OraContext.Provider>
  );
};

export default OraProvider;