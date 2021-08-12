#!/bin/bash


env INPUT_ORGANIZATION=tspascoal-tests \
    INPUT_ISSUE-NUMBER=1 \
    INPUT_PROJECT-NUMBER=1 \
    INPUT_SET-FIELDS='{ "Status": "Done", "Type": "Task", "Points": 66, "Finish Date":"2021-02-02"}' \
node dist/index.js