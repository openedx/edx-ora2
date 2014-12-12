#!/usr/bin/env bash

cd `dirname $BASH_SOURCE` && cd ../openassessment/xblock/static
sass --update sass:css --force --style compressed -I ./sass/vendor/bi-app
