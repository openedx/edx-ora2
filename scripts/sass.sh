#!/usr/bin/env bash

cd `dirname $BASH_SOURCE` && cd ../apps/openassessment/xblock/static
sass --update sass:css --force
