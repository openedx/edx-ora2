#!/usr/bin/env bash

cd `dirname $BASH_SOURCE` && cd ..

echo "Running JavaScript tests..."
npm test
