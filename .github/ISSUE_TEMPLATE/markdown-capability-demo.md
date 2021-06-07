---
name: Markdown capability demo
about: Use this issue template to demonstrate the capabilities of Markdown.
title: ''
labels: ''
assignees: ''

---

# GitHub flavored markdown

## GitHub resources

- [GitHub.com](https://github.com)
- [GitHub on Microsoft Learn](https://docs.microsoft.com/en-us/learn/github/)

## Octocats

![Dinotocat](https://octodex.github.com/images/dinotocat.png)

> Dinotocat is one of many Octocats in the [Octodex](https://octodex.github.com/). You can build your own [here](https://myoctocat.com/)!

## Code examples

----

```yml
- name: Super-Linter
   uses: github/super-linter@v3.14.0
   env:
     VALIDATE_ALL_CODEBASE: false
     DEFAULT_BRANCH: main
     GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```
