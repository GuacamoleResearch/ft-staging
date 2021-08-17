# Sends notifications to a list of issues

Sends a notification to a list of issues, the notification content is stored in a file.

The list of issues can be generated independently or the output of the [get-unclosed-issue-passed-due-date](../get-unclosed-issue-passed-due-date) action.

The issues can be in multiple repositories.

The notification consists of adding a comment with mention to issue assignees plus the content of the notification file.

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

## Usage

```YAML
uses: ./actions/send-notification-issues
with:
  issues-list: # The list of issues (comma separated). Each issue can be in format owner/repo/number or just number (in the case the issue is considered to be in the current repository).)
  # token: # Token (Defaults to github.token). Will need to use a PAT if issues are in other repos.
  content-path: PATH_TO_TEMPLATE_OF_NOTIFICATION
```
