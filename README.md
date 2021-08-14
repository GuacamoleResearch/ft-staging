# fasttrack-staging

Automation test repository before code is integrated into [fasttrack repository](https://github.com/github/fasttrack)

> DO NOT STORE ANY RELEAVANT DATA IN HERE. THIS ORG IS NOT UNDER GITHUB CONTROL

> All reminders are defined in a template file stored in the repo (markdown)

## Questions for the team
- How much data should we embed in Project board custom field and how much should be in the issues itself...
  - Start and End Dates (Title and fields for now)
  - Follow-up date triggers (Field)
  - OKR information (?)
  - Organizations (?)
  - Platform type (Field)
  - Other?

## Process Overview
1. TRIAGE (No status on the project board)
    - **Trigger:** Request is opened, filled out by AM/CSM/CSA/SE/TSAM, automatically labeled `Triage` and assigned to FastTrack Ops (dmckinstry) via the `ISSUE_TEMPLATE`
    - Workflow moves the issue onto the project (no status), sets the FollowDate to tomorrow, and appends the checklist to the description
    - Requester and FastTrack Ops iterate on preapproval process (outside of any automation)
    - FastTrack Ops presents to customer and documents the results
2. REJECTED (Closed)
    - **Trigger:** FastTrack Ops issues a "/REJECT" command; this can be at any time during the entire engagement process but will typically be before or during the FastTrack Kickoff call (first call) with the customer
    - Issue is removed from the project board and closed
    - @mention is appended to the issue discussion via automation notifying the person who opened the request and @dmckinstry (e.g., "*:point_up: @someone @dmckinstry - This request has been rejected per tha above comments. Please let us know if you believe this was a mistake.*")
3. APPROVED (1-Approved)
    - **Trigger:** FastTrack Ops approves via the "/APPROVE" command
    - Workflow removes the `Triage` label and moves the issue to the `1-Approved` status in the project board
      - @tspascoal :point_right: I do not anticipate the need to auto-assign as part of the approval process. It is possible that we will know the right assignee but that usually follows looking at the schedule.  And if we do know, I am concerned about too much clutter for the DevOps Architect before things settle... Your thoughts?
3. SCHEDULED (2-Scheduled)
    - **Trigger:** FastTrack Ops formats the title into standard format including dates, assignsthe  DevOps Architect(s) and manually moves to the `2-Scheduled` status on the project board
4. DELIVERING (3-Delivering)
    - **Trigger:** Workflow moves the request into the `3-Delivering` column the morning of the start date.

## Commands
- "/REJECT" is issued at any time to close out and clean up a request (see "REJECTED" in the **Process Overview**)
- "/APPROVE" is used to move a request from TRIAGE to APPROVED (see "APPROVED" in the **Process Overview**)

## Reporting

A scheduled workfow will scan through all open requests every morning and append/notify participants when there are exceptions or follow-up needed.

- *Status report*
  - **Trigger:** Manual (may change to scheduled in the future)
  - **Format:** Delivered in a known discussion thread in the FastTrack repo, with prior runs appended to the bottom of the discussion and new runs overwriting the discussion Descritpion
  - Includes contents from the current status report workflow...  "Currently delivering" and "starting next week" with links to the request issues
  - New content for Approved list and summary count of triage requests
- *Calendar report*
  - **Trigger:** Manual (may change to scheduled in the future)
  - **Format:** Delivered in a known discussion thread in the FastTrack repo, with prior runs appended to the bottom of the discussion and new runs overwriting the discussion Descritpion
  - Simulate the existing calednar spreadsheet with dates (weeks) in columns, DevOps Architects in the rows, and customer names in the individual cells based on assigment.  Note that an architect may be assigned multiple engagements in a week (but our delivery model doesn't support that)
- Exception reports
  - **Trigger:** Run daily on schedule but "debounce" logic in individual reports
  - **Format:** Appended to the discussion in the individual (exception) request issue
  - **Scheduling Exception** *(TBD - for Dave while in **2-Scheduled** to make sure we aren't scheduled while still missing data)* 
  - **Delivery Exception** *(TBD - for Dave+Architects while in **3-Delivering** to make sure we have all data required to run the engagement captured)* 
  - **Wrap-up Reminder** *(TBD - for Architects while in **3-Delivering** and half way through the engaged to remind of wrap-up stuff... making sure the right meetings are scheduled, the right people are invite, the right data is captured, etc.)*
  - **Post-Delivery Exception**
    - *(TBD - for Architects while in **4-Done** and 2+ work days after the engagement completes to make sure all the post-engagement Architect checkboxes are checked)* 
    - *(TBD - for Dave while in **4-Done** and 7+ work days after the engagement completes to make sure all the post-engagement operations checkboxes are checked)*

## Workflow/Automations

The state of the issue can be done either via commands or tags (preferably commands)



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

This date is not calculated, so we need to add it to the fields (or is it the `follow up` field?)

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



--- 
Dave's thoughts based on FY22:
FastTrack process automation:

1 - Request is made per template, labeled as Triage and assigned to dmckinstry
2 - After discussion, dmckinstry "/approve" the issue
  - Remove Triage label
  - Move to 1-Approved on the Project board
3 - Manually move 2-Scheduled
4 - On start date, move to 3-Delivering
5 - Day after end date, move to 4-Done


Exception nudges...
- In Triage without a follow-up date, nudge dmckinstry
- It is 48 hours after the Follow-up date, nudge all assignees
- In scheduled but insufficient checkboxes or missing labels, or bad dates - nudge dmckinstry
- In done but missing Architect checkboxes, missing key fields (e.g., it's GHEC but no orgs) - ping assignee but only once on M/W/F
