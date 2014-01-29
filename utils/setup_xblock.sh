#!/bin/bash

if [ ! -d 'apps' ] || [ ! -f 'manage.py' ]; then
    echo "Sorry; this must be run from the top-level of the tim working tree"
    exit 1;
fi
echo "Ok, installing XBlocks..."

git clone https://github.com/edx/XBlock.git

MODULES=`find XBlock/ -iname 'setup.py' | grep -v prototype`

# Installing XBlock base package is a prerequisite for the rest working
cd XBlock
pip install -e .
cd ..

# This will install XBlock base twice, but that's ok
for dir in $MODULES; do 
    mod_work_dir=`dirname $dir`
    cd $mod_work_dir
    pip install -e .
    if [ ! $? ]; then        # If anything goes wrong
        exit 187             # then die violently
    fi
    cd -
done

cd apps/openassessment_compose
pip install -e .
cd -

echo "You can run the workbench by saying:"
echo "cd XBlock; python manage.py runserver"
