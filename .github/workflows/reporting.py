from array import array
import json
import os
import requests
import datetime
import re

#region Configuration Variables
ORGANIZATION  = os.environ.get('ORG')  or "GuacamoleResearch"
PROJECT_NUM   = os.environ.get('PROJ') or 4
REPOSITORY    = os.environ.get('REPO') or "ft-staging"
DISCUSSION_ID = os.environ.get('DISC_ID') or "MDEwOkRpc2N1c3Npb24zNTIzOTQy"
STATUS_MAP    = None
STATUS_HEADERS= {'':0, '1-Approved':0, '2-Scheduled':0, '3-Delivering':0, '4-Done':0}
GRAPHQL_QUERY = """
{
  search(first: 1 query: "repo:{0}/{1} in:title {3}", type: DISCUSSION) {
    nodes {
      ... on Discussion {
        title
        id
      }
    }
  }
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


# Debugging in the production instance...
ORGANIZATION = 'github'
PROJECT_NUM = 2890
REPOSITORY = 'FastTrack'
DISCUSSION_ID = 'MDEwOkRpc2N1c3Npb24zNTI4MTE5'
#endregion

#region FUNCTIONS: Build master issue list
#
# GetProjectData - Returns query results for FastTrack Issues + Memex
def GetProjectData(org, project, repo):
    # First, get the report title for this week
    report_title = 'foo' # GetReportTitle()

    # Standard Python Format doesn't seem to work with multi-line, so using 'replace'
    issue_query = GRAPHQL_QUERY.replace("{0}", org).replace("{1}", str(project)).replace("{2}", repo).replace("{3}", report_title)

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
            # Handle exception case for issues not yet on the board
            if not issue.get('Status'):
              issue['Status'] = '' 

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
    if (STATUS_MAP is None):
        fields = query_results['data']['organization']['projectNext']['fields']['nodes']
        status = list(filter(lambda x:(x['name'] == 'Status'), fields))
        status_settings = json.loads(status[0]['settings'])
        STATUS_MAP = status_settings['options']

    status_text = list(filter(lambda x:(x['id']==issue['Status']), STATUS_MAP))[0]['name'] if issue.get('Status') else ''
    return status_text

#endregion

#region FUNCTIONS: Process Issue data
#
# GetIssueSummary - Build summary issue count by status (columns) and region or remote (rows)
def GetIssueSummary(issues, target_labels):
    # Initialize data structure based on target labels
    rows = {'TBD':dict.copy(STATUS_HEADERS)}
    for label in target_labels:
        rows[label] = dict.copy(STATUS_HEADERS)

    # Generate a per-label, per-status counts
    for issue in issues:
        labels = issue['Labels']
        found_row = False
        for row in rows:
            if str(labels).find(row) >= 0:
                rows[row][issue['Status']] += 1
                found_row = True
        if not found_row:
            rows['TBD'][issue['Status']] += 1

    # Convert the data structure to MD
    # Start with the header
    md = '| '
    for status in sorted(STATUS_HEADERS):
        row_header = status if (status!='') else 'None'
        md += '| ' + row_header
    md += ' |\n|-|-|-|-|-|-|\n'
    
    # Add the body of the table
    for row in rows:
        md += '| ' + row
        for status in rows[row]:
            md += '| ' + str(rows[row][status])
        md += ' |\n'

    return md

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
            if issue.get('Status') and status['name'] == issue['Status']:
                status_list[status['name']].append("- [" + issue['Title'] + "](" + issue_link + ")\n")

        issue_details += '\n' + status['name'] + '\n'
        for issue_text in status_list[status['name']]:
            issue_details += issue_text

    return issue_details

#endregion

#region: FUNCTIONS: Exception reporting

#
# GetExceptions - Generate a list of exceptions by assignee
def GetExceptions(issues):
    issues_list = {}

    # Loop through all issues and build a list of exceptions
    for issue in issues:
        ProcessExceptions(issues_list, issue)

    # Convert the data structure to MD
    exception_md = ''
    for assignee in issues_list:
        exception_md += '\n' + assignee + ' - Please review the following exceptions:\n'
        for message in issues_list[assignee]:
            exception_md += '\n' + message
        exception_md += '\n'

    return exception_md

def ProcessExceptions(issues_list, issue):
    # Initialize Data
    assignees = issue['Assignees']
    status = issue['Status']
    followup = datetime.datetime.strptime(issue['Followup'], '%Y-%m-%dT00:00:00+00:00') if issue.get('Followup') else datetime.datetime.now()
    issue_title = issue['Title']
    issue_id = issue['Number']
    checklists = CountChecklist(issue['Body'])

    # Process global exceptions then exceptions for each status
    if (checklists is None) or (checklists['pre'] is None) or (checklists['post'] is None) or (checklists['delivery'] is None):
        AddException(issues_list, '@dmckinstry', issue_title, issue_id, 'Invalid checklist for {issue_link}')
    # Only look for exceptions after followup dates
    elif followup <= datetime.datetime.now():
        if status == '1-Approved':
            # TODO: Exceptions for approved requests
            if checklists['pre']['checked'] < 3:
                AddException(issues_list, 'dmckinstry', issue_title, issue_id, 'Incomplete pre-engagement checklist for Approved {issue_link} FastTrack')
        elif status == '2-Scheduled':
            # TODO: Exceptions for scheduled requests
            if checklists['pre']['unchecked'] > 0:
                AddException(issues_list, 'dmckinstry', issue_title, issue_id, 'Incomplete pre-engagement checklist for Scheduled {issue_link} FastTrack')
        elif status == '3-Delivering':
            # TODO: Exceptions for delivery scheduling
            if checklists['delivery']['unchecked'] > 0:
                AddException(issues_list, 'dmckinstry', issue_title, issue_id, 'Incomplete delivery checklist for the {issue_link} FastTrack')
        elif status == '4-Done':
            # TODO: Exceptions for completed requests
            if checklists['delivery']['unchecked'] > 0:
                AddException(issues_list, 'dmckinstry', issue_title, issue_id, 'Incomplete delivery checklist for the {issue_link} FastTrack')
            if checklists['post']['unchecked'] > 0:
                AddException(issues_list, assignees, issue_title, issue_id, 'Incomplete delivery checklist for the {issue_link} FastTrack')

#
# AddException - Add an exception to the list
def AddException(issues_list, assignees, issue_title, issue_id, message):
    if type(assignees) is str: assignees = [re.sub(r"[\['\]]", "", assignees)]
    for assignee in assignees:
        if not issues_list.get(assignee):
            issues_list[assignee] = []

        issue_link = '[' + issue_title + '](' + FormatUrl(ORGANIZATION, REPOSITORY, issue_id) +')'
        issues_list[assignee].append('- ' + message.replace('{issue_link}', issue_link))

#
# GetReportTitle - Get the title of the report
def GetReportTitle():
    return 'FastTrack Status Report (week of ' + str(GetMondayDate()) + ')' 

#
# GetReportDiscussionId - Get the discussion ID for the report
def GetReportDiscussionId(query_results):
    id = query_results['data']['search']['nodes'][0]['id'] if query_results['data']['search']['nodes'] else None

    #TODO: Create an exception if none exists
    if not id:
        print('No discussion found for the report - need to create one here')
        id = DISCUSSION_ID # cop out for now...

    return id

#endregion

#region FUNCTIONS: Utilities
#
# FormatUrl - Returns markdown for a link with the title for a given issue
def FormatUrl(org, repo, issue_id):
    return 'https://github.com/{0}/{1}/issues/{2}'.format(org, repo, issue_id)

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

# CountChecklistForRegion - Performs the actual [x] parsing for an individual segment of the overall checklist
def CountChecklistForRegion(regex, issue_description):
    checked = 0
    unchecked = 0
    try:
        checklist_block = re.search(regex, issue_description).group()
        unchecked = re.findall(r'- \[ \]', checklist_block)
        checked = re.findall(r'- \[x\]', checklist_block, re.IGNORECASE)
        results = { 'checked': checked.count('- [x]') + checked.count('- [X]'), 'unchecked': unchecked.count('- [ ]')}
    except:
        print("*** Missing checklist block for regex ", regex)
        results = None

    return results

#
# UpdateDiscussion - Update the title and description of a specificed Discussion
def UpdateDiscussion(discussionId, title, body):
    # Configure the mutation based on input data
    if discussionId:
        mutation = 'mutation {updateDiscussion(input: {discussionId: "{discussionId}", body: "{body}", title: "{title}"}) {discussion {id}}}'
        mutation = mutation.replace("{discussionId}", discussionId)
    else:
        # TODO: Need Repository Id and Category Id
        mutation = 'mutation {createDiscussion(input: {body: "{body}", title: "{title}", repository: "{repository}", category:"{category}"}) {discussion {id}}}'

    mutation = mutation.replace("{body}", body).replace("{title}", title)

    token = os.environ["FASTRACK_PROJECT_SECRET"]
    response = requests.post(
        'https://api.github.com/graphql',
        json={'query':mutation},
        headers={'Authorization':'bearer '+token, 'GraphQL-Features':'projects_next_graphql' }
    )
    if response:
        return response.json()
    else:
        return

#
# GetMondayDate - Returns a Date object containing the Monday preceding (or today) the passed param
def GetMondayDate(input_date = datetime.datetime.now()):
    # Get the date of the Monday of the given date
    results = input_date - datetime.timedelta(days=input_date.weekday())
    return results.date() if type(results) == datetime.datetime else results

#endregion

#----------------------------------------------------------------------------
#----------------------------------------------------------------------------
#
# Begin Main
#

# Read issues and summarize issue counts
issue_data = GetProjectData( ORGANIZATION, PROJECT_NUM, REPOSITORY)
issues = MergeIssueData(issue_data)

# Get the ID for the report discussion
report_id = GetReportDiscussionId(issue_data)

# Build Status report
issue_details_md = GetIssueDetails(issues)
region_summary_md = GetIssueSummary(issues, ['AMER','APAC','EMEA'])
travel_smmary_md = GetIssueSummary(issues, [':house:',':airplane:'])
exception_md = GetExceptions(issues)

# Write the report to the reporting discussion description and title
body = '## Regional Summary\n*Last Updated: ' + str(datetime.date.today()) + '*\n\n' + region_summary_md + '\n\n## Travel Summary\n\n' + travel_smmary_md + '\n\n## Request Details\n\n' + issue_details_md + '\n\n## Exceptions\n\n' + exception_md
title = GetReportTitle()

print(title)
print(body)
UpdateDiscussion(DISCUSSION_ID, title, body)
