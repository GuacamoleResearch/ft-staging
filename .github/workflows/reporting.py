import requests
import json
import os
import datetime
import re
import io

#region Configuration Variables
ORGANIZATION  = "GuacamoleResearch"
PROJECT_NUM   = 4
REPOSITORY    = "ft-staging"
#endregion

#region Functions
# GetProjectData - Returns query results for FastTrack Issues + Memex
def GetProjectData(org, project, repo):
  issue_query = """
  {
    organization(login: "{0}") {
      projectNext(number: {1}) {
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
      repository(name: "{2}") {
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
  }"""
  
  # Standard Python Format doesn't seem to work with multi-line, so using 'sub'
  issue_query = issue_query.replace("{0}", org).replace("{1}", str(project)).replace("{2}", repo)

  token = os.environ["FASTRACK_PROJECT_SECRET"]
  response = requests.post(
      'https://api.github.com/graphql',
      json={'query':issue_query},
      headers={'Authorization':'bearer '+token, 'GraphQL-Features':'projects_next_graphql' }
    )
  if response:
    return response.json()
  else:
    return

# MergeIssueData - Merges thhe project and issue data in a unified issue list:
# Returns Issues list with:
# - Id
# - Title
# - Labels (string with comma delimited list)
# - Body
# - Author
# - LastUpdated
# - Assignees (string with comma delimited list)
# - Fields (JSON)
def MergeIssueData(project_issue_results):
  issue_list = []

  # First, capture all issues from the query
  for node in project_issue_results['data']['organization']['repository']['issues']['nodes']:
      issue = {}
      issue['title']      = node['title']
      issue['labels']     = str(list(map(lambda x:x['name'], node['labels']['nodes'])))
      issue['author']     = node['author']['login']
      issue['body']       = node.get('body')
      issue['assignees']  = node.get('missing', 'none')
      issue_list.append(issue)

  # Next, Copy in all fields from the projectNext data
  for node in project_issue_results['data']['organization']['projectNext']['items']['nodes']:
    # There has to be a better way in python to find an item in a list
    for issue in issue_list:
      # Joining on Title as I don't have a better choice
      if issue['title'] == node['title']:
        issue['lastUpdated'] = node['updatedAt']
        issue['fields'] = []
        for field in node['fieldValues']['nodes']:
          issue['fields'].append( {field['projectField']['name']: field['value']})

    # Clean up and promote special fields (e.g., Status)
    PromoteAndMapFields(issue_list)
  return issue_list

# PromoteAndMapFields - Cleans up the 'status' field and maybe more to come...
def PromoteAndMapFields(issues):
  for issue in issues:
    print('TODO: PromoteAndMap {0}', issue)
    # Including mapping Status field from Id

# DatesFromIssueTitle: Parses start and end dates
def DatesFromIssueTitle(title):
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

def FormatUrl(repo, number):
    return 'https://github.com/github/{0}/issues/{1}'.format(repo, number)

#
# Project board details for recent and upcoming deliveries
#
def ColumnDetails(column_json, column_name, upcoming=False, ending=False):
    issue_detail = ""
    for column in column_json:
        if column['name'] == column_name:
            for card in column['cards']['nodes']:
                title = card["content"]["title"]
                issue_num = card["content"]["number"]
                # TODO: Pass in REPOSITORY
                this_issue = '  - [' + title + ']('+ FormatUrl(REPOSITORY, issue_num) + ')\n'
                date_range = DatesFromIssueTitle(title)
                if upcoming and date_range['start'] > datetime.date.today() and date_range['start'] < (datetime.date.today()+datetime.timedelta(days=7)):
                    issue_detail += this_issue
                elif ending and date_range['finish'] > datetime.date.today() and date_range['finish'] < datetime.date.today()+datetime.timedelta(days=7):
                    issue_detail += this_issue
                elif (not upcoming) and (not ending):
                    issue_detail += this_issue
    return issue_detail


#endregion

label_count = {
    "AMER": { "Triage": 0, "Confirmed": 0 },
    "EMEA": { "Triage": 0, "Confirmed": 0 },
    "APAC": { "Triage": 0, "Confirmed": 0 }}

#
# Read issues and summarize issue counts
#

summary_block=""
issue_data = GetProjectData( ORGANIZATION, PROJECT_NUM, REPOSITORY)

if issue_data:
    issues = MergeIssueData(issue_data)

    for issue in issues:
        for region in label_count.keys():
          if issue["labels"].find(region):            
            for engage_state in label_count[region].keys():
                if issue["labels"].find(region) > 0 and issue["labels"].find(engage_state) > 0:
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
    issue_summary = "ERROR COUNTING REGION LABELS!"

#
# Project board summary for Confirmed/Scheduled/In Progress/Done
# Counts for each state
#
status_summary = """
## Engagement Status Summary
"""

# for node in issues_json['data']['organization']['projectNext']['columns']['nodes']:
#     status_summary += "- " + node['name'] + ": " + str(len(node['cards']['nodes'])) + "\n"

# column_json = issues_json['data']['repository']['project']['columns']['nodes']
# recent_updates = """
# ## Recent and Upcoming FastTrack Deliveries
# - Currently delivering:
# """ + ColumnDetails(column_json, "Delivering") + """
# - Finishing this week:
# """ + ColumnDetails(column_json, "Delivering", ending=True) + """
# - Starting next week:
# """ + ColumnDetails(column_json, "Scheduled", upcoming=True) + "\n"


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

# print(recent_updates)
