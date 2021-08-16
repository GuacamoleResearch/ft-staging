import requests
import json
import os
import datetime
import re

#region Configuration Variables
ORGANIZATION  = os.environ.get('ORG')  or "GuacamoleResearch"
PROJECT_NUM   = os.environ.get('PROJ') or 4
REPOSITORY    = os.environ.get('REPO') or "ft-staging"
STATUS_MAP    = None
#endregion

#region FUNCTIONS: Build master isse list
#
# GetProjectData - Returns query results for FastTrack Issues + Memex
def GetProjectData(org, project, repo):
  issue_query = """
  {
    organization(login: "{0}") {
      projectNext(number: {1}) {
        items(first: 100) {
          nodes {
            title
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
        fields(first: 50) {
          nodes {
            name
            settings
          }
        }
      }
      repository(name: "{2}") {
        issues(states: OPEN, first: 100) {
          nodes {
            number
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
  
  # Standard Python Format doesn't seem to work with multi-line, so using 'replace'
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

#
# MergeIssueData - Merges thhe project and issue data in a unified issue list:
def MergeIssueData(project_issue_results):
  issue_list = []

  # Capture all issues from the query
  for node in project_issue_results['data']['organization']['repository']['issues']['nodes']:
    issue = {}
    issue['Number']     = node['number']
    issue['Title']      = node['title']
    issue['Labels']     = str(list(map(lambda x:x['name'], node['labels']['nodes']))) if node.get('labels') else []
    issue['Author']     = node['author']['login']
    issue['Body']       = node.get('body')
    issue['Assignees']  = str(list(map(lambda x:x['login'], node['assignees']['nodes']))) if node.get('assignees') else []

    # Add dates from title if they're available
    dates = DatesFromIssueTitle(issue['Title'])
    issue['Start_Date'] = dates['start']
    issue['End_Date']   = dates['finish']

    issue_list.append(issue)

  # Next, Copy in all fields from the projectNext data
  for node in project_issue_results['data']['organization']['projectNext']['items']['nodes']:
    # There has to be a better way in python to find an item in a list
    for issue in issue_list:
      # Joining on Title as I don't have a better choice
      if issue['Title'] == node['title']:
        # Promote custom fields
        for field in node['fieldValues']['nodes']:
          fieldName = field['projectField']['name']
          issue[fieldName] = field['value']
        issue['Status'] = MapStatusField(project_issue_results, issue)

  return issue_list

#
# DatesFromIssueTitle: Parses start and end dates
def DatesFromIssueTitle(title):
  try:
    date_range_strings = title.rsplit("(")[1].split(")")[0].split("-")
    date_range = []
    for date_string in date_range_strings:
      parts = date_string.split("/")
      if len(parts) == 2: parts.append(str(datetime.date.today().year))
      the_date = datetime.date(int(parts[2]), int(parts[0]), int(parts[1]))
      date_range.append(the_date)
    return {"start": date_range[0], "finish": date_range[1]}
  except:
    return {"start": None, "finish": None}

#
# MapStatusField - Converts status IDs into status text
def MapStatusField(query_results, issue):
  global STATUS_MAP
  if (STATUS_MAP == None):
    fields = query_results['data']['organization']['projectNext']['fields']['nodes']
    status = list(filter(lambda x:(x['name'] == 'Status'), fields))
    status_settings = json.loads(status[0]['settings'])
    STATUS_MAP = status_settings['options']

  status_text = list(filter(lambda x:(x['id']==issue['Status']), STATUS_MAP))[0]['name'] if issue.get('Status') else ''
  return status_text

#endregion

#region FUNCTIONS: Process Issue data

#
# GetIssueCounts - Returns markdown summary of issues by state by region
def GetIssueCounts(issues):
  # TODO: Evolve this into dynamic status columns and add a section for travel/remote/unknown
  # Initialize variables
  issue_summary = """
## Regional Status Summary
| Region | Triage    | Confirmed | Total |
| ------ | --------- | --------- | ----- |
"""
  label_count = {
    "AMER": { "Triage": 0, "Confirmed": 0 },
    "EMEA": { "Triage": 0, "Confirmed": 0 },
    "APAC": { "Triage": 0, "Confirmed": 0 }}

  # count issues by region and state
  for issue in issues:
    for region in label_count.keys():
      if issue["Labels"].find(region):            
        for engage_state in label_count[region].keys():
          if issue["Labels"].find(region) > 0 and issue["Labels"].find(engage_state) > 0:
            label_count[region][engage_state] += 1
  
  # Build markdown for summary data
  for region in label_count.keys():
    summary = "| " + region + "   | "
    total = 0
    for engage_state in label_count[region].keys():
      summary += str(label_count[region][engage_state]) + "        | "
      total += label_count[region][engage_state]
    issue_summary += summary + str(total) + "   |\n"

  return issue_summary

#
# GetIssueSummary - Build summary issue count by status (columns) and region or remote (rows)
def GetIssueSummary(issues):
  regions = {'AMER':{}, 'APAC':{}, 'EMEA':{}, 'TBD':{}}
  #delivery = {':house:':0, ':airplane:':0, 'TBD':0}

  # Generate a per-label, per-status count
  for issue in issues:
    labels = issue['Labels']
    found_region = False
    for region in regions:
      if not regions[region].get(issue['Status']):
        regions[region][issue['Status']] = 0
      if str(labels).find(region) >= 0:
        regions[region][issue['Status']] += 1
        found_region = True
    if not found_region: 
      if not regions[region].get('TBD'):
        regions[region]['TBD'] = 1
      else:
        regions[region]['TBD'] += 1

  # Convert the data structure to MD
  # Start with the header
  md = '| '
  for status in regions['TBD'].keys():
    md += '| ' + status
  md += ' |\n|-|-|-|-|-|-|\n'
  
  # Add the body of the table
  for region in regions:
    md += '| ' + region
    for status in regions[region]:
      md += '| ' + str(regions[region][status])
    md += ' |\n'

  return md

  # return issue_details


#
# GetIssueDetails - Build list of issues by state with hyperlinks
def GetIssueDetails(issues):
  global STATUS_MAP, ORGANIZATION, REPOSITORY
  status_list = {}
  issue_details = ''
  for status in STATUS_MAP:
    for issue in issues:
      issue_link = FormatUrl(ORGANIZATION, REPOSITORY, issue['Number'])
      if not status_list.get(status['name']):
        status_list[status['name']] = []
      if status['name'] == issue['Status']:
        status_list[status['name']].append("- [" + issue['Title'] + "](" + issue_link + ")\n")

    issue_details += '\n' + status['name'] + '\n'
    for issue_text in status_list[status['name']]:
      issue_details += issue_text

  return issue_details

#endregion

#region FUNCTIONS: Utilities
#
# FormatUrl - Returns markdown for a link with the title for a given issue
def FormatUrl(org, repo, issue_id):
    return 'https://github.com/{0}/{1}/issues/{2}'.format(org, repo, issue_id)

#
# ColunmnDetails - Project board details for recent and upcoming deliveries
def ColumnDetails(column_json, column_name, upcoming=False, ending=False):
  issue_detail = ""
  for column in column_json:
    if column['name'] == column_name:
      for card in column['cards']['nodes']:
        title = card["content"]["title"]
        issue_num = card["content"]["number"]
        # TODO: Pass in ORG & REPOSITORY
        this_issue = '  - [' + title + ']('+ FormatUrl(ORGANIZATION, REPOSITORY, issue_num) + ')\n'
        date_range = DatesFromIssueTitle(title)
        if upcoming and date_range['start'] > datetime.date.today() and date_range['start'] < (datetime.date.today()+datetime.timedelta(days=7)):
          issue_detail += this_issue
        elif ending and date_range['finish'] > datetime.date.today() and date_range['finish'] < datetime.date.today()+datetime.timedelta(days=7):
          issue_detail += this_issue
        elif (not upcoming) and (not ending):
          issue_detail += this_issue
  return issue_detail

#
# CountChecklist - Parse the issue description to count "[ ]" and "[x]" per 
def CountChecklist(issue_description):
  # Pre-engagement Regex - "### Pre((.|\n)*)### Del"
  preengagement = CountChecklistForRegion("### Pre((.|\n)*)### Del", issue_description)

  # Delivery Regex - "### Pel((.|\n)*)### Post"
  delivery = CountChecklistForRegion("### Del((.|\n)*)### Post", issue_description)
  
  # Post-engagement Regex - "### Post((.|\n)*)$"
  postengagement = CountChecklistForRegion("### Post((.|\n)*)$", issue_description)

  results = {'pre':preengagement, 'delivery': delivery, 'post': postengagement}
  return results

def CountChecklistForRegion(regex, issue_description):
  checked = 0
  unchecked = 0
  try:
    checklist_block = re.search(regex, issue_description).group()
    unchecked = re.findall(r'- \[ \]', checklist_block)
    checked = re.findall(r'- \[x\]', checklist_block, re.IGNORECASE)
  except:
    print("*** Missing checklist block for regex ", regex)

  results = { 'checked': checked.count('- [x]') + checked.count('- [X]'), 'unchecked': unchecked.count('- [ ]')}
  return results

#endregion

#----------------------------------------------------------------------------
#
# Begin Main
#

# Read issues and summarize issue counts
issue_data = GetProjectData( ORGANIZATION, PROJECT_NUM, REPOSITORY)
issues = MergeIssueData(issue_data)

# Build Status report
issue_summary_md = GetIssueCounts(issues) 
issue_details_md = GetIssueDetails(issues)

GetIssueSummary(issues)

# Emit report
print(issue_summary_md)
print(issue_details_md)
