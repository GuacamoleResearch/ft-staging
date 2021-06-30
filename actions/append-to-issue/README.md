# Append a file to a given issue body

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
uses: ./actions/append-to-issue
with:
  number: ISSUE_NUMBER
  content-path: PATH_TO_TEMPLATE_TO_APPEND
```