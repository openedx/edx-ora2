##############################################################################
#
#   Run the acceptance tests in Jenkins
#
#   This assumes that:
#       * Jenkins has Python and virtualenv installed
#       * Jenkins has the SauceConnect plugin installed.
#       * The Jenkins job provides the environment variables
#           - BASIC_AUTH_USER: The basic auth username for the sandbox.
#           - BASIC_AUTH_PASSWORD: The basic auth password for the sandbox.
#           - TEST_HOST: The hostname of the sandbox (e.g. test.example.com)
#
##############################################################################

set -x

if [ -z "$BASIC_AUTH_USER" ]; then
    echo "Need to set BASIC_AUTH_USER env variable"
    exit 1;
fi

if [ -z "$BASIC_AUTH_PASSWORD" ]; then
    echo "Need to set BASIC_AUTH_PASSWORD env variable"
    exit 1;
fi

if [ -z "$TEST_HOST" ]; then
    echo "Need to set TEST_HOST env variable"
    exit 1;
fi

export ORA_SANDBOX_URL="https://${BASIC_AUTH_USER}:${BASIC_AUTH_PASSWORD}@${TEST_HOST}"
EXIT=0

########## Install python requirements #########
virtualenv venv
source venv/bin/activate
pip install -r requirements/test-acceptance.txt

######### Run acceptance tests #########
make test-acceptance || EXIT=1

######### Run accessibility tests #########
make test-a11y || EXIT=1

######### exit with correct code #########
exit $EXIT
