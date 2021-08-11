# Adds an issue to a project (v2)

Adds a issue (in the current repository) to a project.

If the issue is alreaby part of the board nothing is changed.

Optional can also be used to set field values.
 
## Code 

> First, you'll need to have a reasonably modern version of `node` handy. This won't work with versions older than 9, for instance.

Install the dependencies  
```bash
$ npm install
```

Build the typescript and package it for distribution
```bash
$ npm run build && npm run package
```

Run the tests :heavy_check_mark:  
```bash
$ npm test
```

## Usage.

```YAML
uses: ./actions/add-issue-to-project
with:
  project-number: PROJECT_NUMBER
  issues-number: ISSUE_NUMBER
  token: A TOKEN WITH ORG WRITE SCOPE
  set-fields: {'status': 'Closed', myField: "2"} # optional
```
