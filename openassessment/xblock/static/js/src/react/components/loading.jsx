import React from 'react';
import { Spinner } from '@edx/paragon';

export default function Loading() {
  return (
    <div className='h-100 w-100 m-auto'>
      <Spinner
        animation='border'
        className='mie-3'
        screenReaderText='loading'
      />
    </div>
  );
}
