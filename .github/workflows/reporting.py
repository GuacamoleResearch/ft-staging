import requests
import json
import os
import datetime
import re
import io
#region Variable initialization
issue_query = """
{
  organization(login: "GuacamoleResearch") {
    projectNext(number: 4) {
      items(first: 100) {
        nodes {
          title
          id
          content {
            __typename
          }
          updatedAt
          fieldValues(first: 30) {
            nodes {
              projectField {
                name
              }
              value
            }
          }
        }
      }
    }
    repository(name: "ft-staging") {
      issues(states: OPEN, first: 100) {
        nodes {
          id
          title
          assignees(first: 100) {
            nodes {
              login
            }
          }
          labels(first: 100) {
            nodes { name }
          }
          author {
            login
          }
          body
        }
      }
    }
  }
}
"""

label_count = {
    "AMER": { "Triage": 0, "Confirmed": 0 },
    "EMEA": { "Triage": 0, "Confirmed": 0 },
    "APAC": { "Triage": 0, "Confirmed": 0 }}

token = os.environ["FASTRACK_PROJECT_SECRET"]
#endregion

#
# Read issues and summarize issue counts
#
response = requests.post(
    'https://api.github.com/graphql',
    json={'query':issue_query},
    headers={'Authorization':'bearer '+token, 'GraphQL-Features':'projects_next_graphql' }
)

summary_block=""
if response:
    issues_json = response.json()
    for node in issues_json['data']['organization']['repository']['issues']['nodes']:
        labels_text = str(list(map(lambda x:x['name'], node['labels']['nodes'])))
        for region in label_count.keys():
            for engage_state in label_count[region].keys():
                if labels_text.find(region) > 0 and labels_text.find(engage_state) > 0:
                    label_count[region][engage_state] += 1

    issue_summary = """
## Regional Status Summary
| Region | Triage    | Confirmed | Total |
| ------ | --------- | --------- | ----- |
"""

    for region in label_count.keys():
        summary = "| " + region + "   | "
        total = 0
        for engage_state in label_count[region].keys():
            summary += str(label_count[region][engage_state]) + "        | "
            total += label_count[region][engage_state]
        issue_summary += summary + str(total) + "   |\n"
else:
    issue_summary = response.content

#
# Project board summary for Confirmed/Scheduled/In Progress/Done
# Counts for each state
#
status_summary = """
## Engagement Status Summary
"""

for node in issues_json['data']['organization']['projectNext']['columns']['nodes']:
    status_summary += "- " + node['name'] + ": " + str(len(node['cards']['nodes'])) + "\n"

#
# Project board details for recent and upcoming deliveries
#
def DatesFromIssueText(title):
    date_range_strings = title.rsplit("(")[1].split(")")[0].split("-")
    date_range = []
    for date_string in date_range_strings:
        parts = date_string.split("/")
        try:
            if len(parts) == 2: parts.append(str(datetime.date.today().year))
            the_date = datetime.date(int(parts[2]), int(parts[0]), int(parts[1]))
            date_range.append(the_date)
        except:
            return "Invalid date string"
    return {"start": date_range[0], "finish": date_range[1]}
def FormatUrl(number):
    return 'https://github.com/github/FastTrack/issues/' + str(number)
def ColumnDetails(column_json, column_name, upcoming=False, ending=False):
    issue_detail = ""
    for column in column_json:
        if column['name'] == column_name:
            for card in column['cards']['nodes']:
                title = card["content"]["title"]
                issue_num = card["content"]["number"]
                this_issue = '  - [' + title + ']('+ FormatUrl(issue_num) + ')\n'
                date_range = DatesFromIssueText(title)
                if upcoming and date_range['start'] > datetime.date.today() and date_range['start'] < (datetime.date.today()+datetime.timedelta(days=7)):
                    issue_detail += this_issue
                elif ending and date_range['finish'] > datetime.date.today() and date_range['finish'] < datetime.date.today()+datetime.timedelta(days=7):
                    issue_detail += this_issue
                elif (not upcoming) and (not ending):
                    issue_detail += this_issue
    return issue_detail
column_json = issues_json['data']['repository']['project']['columns']['nodes']
recent_updates = """
## Recent and Upcoming FastTrack Deliveries
- Currently delivering:
""" + ColumnDetails(column_json, "Delivering") + """
- Finishing this week:
""" + ColumnDetails(column_json, "Delivering", ending=True) + """
- Starting next week:
""" + ColumnDetails(column_json, "Scheduled", upcoming=True) + "\n"
#
# Output results
#
# summary = open("StatusSummary-staging.md","w")
# summary.write("# FastTrack Engagement Summary\n")
# summary.write("*Last updated: " + datetime.datetime.now().strftime("%I:%M%p UTC on %B %d, %Y") + "*\n")
# summary.write(issue_summary)
# summary.write(status_summary)
# summary.write(recent_updates)
# summary.close()

print(issue_summary)

print(status_summary)

print(recent_updates)
