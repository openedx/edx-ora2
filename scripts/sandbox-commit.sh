#!/usr/bin/env bash

###################################################################
#
#   Echo the commit that is deployed to a sandbox.
#
#   Usage:
#
#       ./sandbox-commit.sh SSH_HOST [SSH_KEY]
#
#   Examples:
#
#       ./sandbox-commit.sh user@example.com
#       ./sandbox-commit.sh user@example.com /home/user/.ssh/id_rsa
#
###################################################################

if [ $# -lt 1 ]; then
    echo "Usage: $0 SSH_HOST [SSH_KEY]"
    exit 1
fi

if [ -z "$2" ]; then
    SSH_CMD="ssh $1"
else
    SSH_CMD="ssh $1 -i $2"
fi

# Disable strict key host checking
# If the sandbox is recreated frequently, we might have a name in known_hosts
# that points to a different IP address.
# This *is* susceptible to man-in-the-middle attacks, so be careful.
SSH_CMD="$SSH_CMD -o StrictHostKeyChecking=no"

$SSH_CMD 'cd /edx/app/edxapp/venvs/edxapp/src/edx-ora2 && git rev-parse HEAD'
