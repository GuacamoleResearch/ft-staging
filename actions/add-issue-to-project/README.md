# Sends notifications for due issues after X days

Sends a notification for all issues in a board/state that have passed their due by X days.

This only works for projects (beta)

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
uses: ./actions/send-unclosed-issue-notification
with:
  number: PROJECT_NUMBER
  column: PROJECT_COLUMN_NAME
  notification-threshold: 1s
  content-path: PATH_TO_TEMPLATE_OF_NOTIFICATION
```