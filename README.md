# fasttrack-staging

Automation test repository before code is integrated into [fasttrack repository](https://github.com/github/fasttrack)

> DO NOT STORE ANY RELEAVANT DATA IN HERE

> All reminders are defined in a template file stored in the repo (markdown)

## Workflow/Automations

The state of the issue can be done either via commands or tags (preferably commands)

### Commands

#### Triaged

Should we have a triage command????

#### Approved 

- Adds the issue to board(s)
- If the approval specifies the assigned architect(s) then the WI is assigned to
- If the WI is assigned send a reminder to the assigned people to:
  - Schedule the KO
  - ?????
- The tasks to be performed (template) are appended to the body of issue
  - Other Engagement Data (to be filled by Operations)
  - Deliverables
  - ETC 

> TODO: the appending of tasks should be done only when approved (cons: the tasks are not visible in rollups for non approved FTs) or after it has been created? (or triaged)

### Schedule events

#### End date is reached (NOT calculated)

This date is not calculated, so we need to add it to the fields

Every day a cron action will scan for issues in the state `delivering` or `done` and if the end date has been reached it will send a reminder to whom the issue is assigned to with
actions that need to be performed:
- Trip reports needs to be finished in X days
- Survey needs to be sent
- Partner survey needs to be sent
- ????

> If state is `delivering` should we move it to `done` automatically?

#### Issue has not been closed in X days reminder

If the issue has not been closed after `X` days of the end date (X being configurable) then send a reminder to the person(s) whose issue is assigned to.

> Should we send just one reminder or one every `Y` days?

### TODO

Define how reminders are sent:
- Mention in the issue
- Slack message
