import json
import os
import datetime
import re
import requests

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
def get_project_data(org, project, repo):
    '''Returns query results for FastTrack Issues + Memex'''
    # First, get the report title for this week
    report_title = 'foo' # get_report_title()

    # Standard Python Format doesn't seem to work with multi-line, so using 'replace'
    issue_query = GRAPHQL_QUERY.replace("{0}", org).\
        replace("{1}", str(project)).replace("{2}", repo).replace("{3}", report_title)

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

def merge_issue_data(project_issue_results):
    '''Merges thhe project and issue data in a unified issue list'''
    issue_list = []

    # Capture all issues from the query
    for node in project_issue_results['data']['organization']['repository']['issues']['nodes']:
        issue = {}
        issue['Number']     = node['number']
        issue['Title']      = node['title']
        issue['Labels']     = str(list(map(lambda x:x['name'], node['labels']['nodes']))) \
            if node.get('labels') else []
        issue['Author']     = node['author']['login']
        issue['Body']       = node.get('body')
        issue['Assignees']  = str(list(map(lambda x:x['login'], node['assignees']['nodes']))) \
            if node.get('assignees') else []

        # Add dates from title if they're available
        dates = dates_from_isse_title(issue['Title'])
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
                issue['Status'] = map_status_field(project_issue_results, issue)
            # Handle exception case for issues not yet on the board
            if not issue.get('Status'):
                issue['Status'] = ''

    return issue_list

def dates_from_isse_title(title):
    '''Parses start and end dates'''
    try:
        date_range_strings = title.rsplit("(")[1].split(")")[0].split("-")
        date_range = []
        for date_string in date_range_strings:
            parts = date_string.split("/")
            if len(parts) == 2:
                parts.append(str(datetime.date.today().year))
            the_date = datetime.date(int(parts[2]), int(parts[0]), int(parts[1]))
            date_range.append(the_date)
        return {"start": date_range[0], "finish": date_range[1]}
    except:
        return {"start": None, "finish": None}

def map_status_field(query_results, issue):
    '''Converts status IDs into status text'''
    global STATUS_MAP
    if STATUS_MAP is None:
        fields = query_results['data']['organization']['projectNext']['fields']['nodes']
        status = list(filter(lambda x:(x['name'] == 'Status'), fields))
        status_settings = json.loads(status[0]['settings'])
        STATUS_MAP = status_settings['options']

    status_text = list(filter(lambda x:(x['id']==issue['Status']), STATUS_MAP))[0]['name'] \
        if issue.get('Status') else ''
    return status_text
#endregion

#region FUNCTIONS: Process Issue data
def get_issue_summary(issues, target_labels):
    '''Build summary issue count by status (columns) and region or remote (rows)'''
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
    markdown = '| '
    for status in sorted(STATUS_HEADERS):
        row_header = status if (status!='') else 'None'
        markdown += '| ' + row_header
    markdown += ' |\n|-|-|-|-|-|-|\n'

    # Add the body of the table
    for row in rows:
        markdown += '| ' + row
        for status in rows[row]:
            markdown += '| ' + str(rows[row][status])
        markdown += ' |\n'

    return markdown

def get_issue_details(issues):
    '''Build list of issues by state with hyperlinks'''
    global STATUS_MAP, ORGANIZATION, REPOSITORY
    status_list = {}
    issue_details = ''
    for status in STATUS_MAP:
        for issue in issues:
            issue_link = format_url(ORGANIZATION, REPOSITORY, issue['Number'])
            if not status_list.get(status['name']):
                status_list[status['name']] = []
            if issue.get('Status') and status['name'] == issue['Status']:
                status_list[status['name']]\
                    .append("- [" + issue['Title'] + "](" + issue_link + ")\n")

        issue_details += '\n' + status['name'] + '\n'
        for issue_text in status_list[status['name']]:
            issue_details += issue_text

    return issue_details
#endregion

#region: FUNCTIONS: Exception reporting
def get_exceptions(issues):
    '''Generate a list of exceptions by assignee'''
    issues_list = {}

    # Loop through all issues and build a list of exceptions
    for issue in issues:
        process_exceptions(issues_list, issue)

    # Convert the data structure to MD
    exception_markdown = ''
    for assignee in issues_list:
        exception_markdown += '\n' + assignee + ' - Please review the following exceptions:\n'
        for message in issues_list[assignee]:
            exception_markdown += '\n' + message
        exception_markdown += '\n'

    return exception_markdown

def process_exceptions(issues_list, issue):
    '''Review checklists and statuses for exceptions'''
    # Initialize Data
    assignees = issue['Assignees']
    status = issue['Status']
    followup = datetime.datetime.strptime(issue['Followup'], '%Y-%m-%dT00:00:00+00:00') \
        if issue.get('Followup') else datetime.datetime.now()
    issue_title = issue['Title']
    issue_id = issue['Number']
    checklists = count_checklist(issue['Body'])

    # Process global exceptions then exceptions for each status
    if (checklists is None) or (checklists['pre'] is None) \
        or (checklists['post'] is None) or (checklists['delivery'] is None):
        add_exception(issues_list, '@dmckinstry', issue_title, \
            issue_id, 'Invalid checklist for {issue_link}')
    # Only look for exceptions after followup dates
    elif followup <= datetime.datetime.now():
        if status == '1-Approved':
            # TODO: Exceptions for approved requests
            if checklists['pre']['checked'] < 3:
                add_exception(issues_list, 'dmckinstry', issue_title, issue_id, \
                    'Incomplete pre-engagement checklist for Approved {issue_link} FastTrack')
        elif status == '2-Scheduled':
            #TODO: Exceptions for scheduled requests
            if checklists['pre']['unchecked'] > 0:
                add_exception(issues_list, 'dmckinstry', issue_title, issue_id, \
                    'Incomplete pre-engagement checklist for Scheduled {issue_link} FastTrack')
        elif status == '3-Delivering':
            #TODO: Exceptions for delivery scheduling
            if checklists['delivery']['unchecked'] > 0:
                add_exception(issues_list, 'dmckinstry', issue_title, issue_id, \
                    'Incomplete delivery checklist for the {issue_link} FastTrack')
        elif status == '4-Done':
            #TODO: Exceptions for completed requests
            if checklists['delivery']['unchecked'] > 0:
                add_exception(issues_list, 'dmckinstry', issue_title, issue_id, \
                    'Incomplete delivery checklist for the {issue_link} FastTrack')
            if checklists['post']['unchecked'] > 0:
                add_exception(issues_list, assignees, issue_title, issue_id, \
                    'Incomplete delivery checklist for the {issue_link} FastTrack')

def add_exception(issues_list, assignees, issue_title, issue_id, message):
    '''Add an exception to the list'''
    if type(assignees) is str:
        assignees = [re.sub(r"[\['\]]", "", assignees)]
    for assignee in assignees:
        if not issues_list.get(assignee):
            issues_list[assignee] = []

        issue_link = '[' + issue_title + '](' + format_url(ORGANIZATION, REPOSITORY, issue_id) +')'
        issues_list[assignee].append('- ' + message.replace('{issue_link}', issue_link))

def get_report_title():
    '''Get the title of the report'''
    return 'FastTrack Status Report (week of ' + str(get_monday_date()) + ')'

def get_report_discussion_id(query_results):
    '''Get the discussion ID for the report'''
    id = query_results['data']['search']['nodes'][0]['id'] \
        if query_results['data']['search']['nodes'] else None

    #TODO: Create an exception if none exists
    if not id:
        print('No discussion found for the report - need to create one here')
        id = DISCUSSION_ID # cop out for now...

    return id

#endregion

#region FUNCTIONS: Utilities
def format_url(org, repo, issue_id):
    '''Returns markdown for a link with the title for a given issue'''
    return 'https://github.com/{0}/{1}/issues/{2}'.format(org, repo, issue_id)

def count_checklist(issue_description):
    '''Parse the issue description to count "[ ]" and "[x]" per checklist'''
    # Pre-engagement Regex - "### Pre((.|\n)*)### Del"
    preengagement = count_checklist_for_region("### Pre((.|\n)*)### Del", issue_description)

    # Delivery Regex - "### Pel((.|\n)*)### Post"
    delivery = count_checklist_for_region("### Del((.|\n)*)### Post", issue_description)

    # Post-engagement Regex - "### Post((.|\n)*)$"
    postengagement = count_checklist_for_region("### Post((.|\n)*)$", issue_description)

    results = {'pre':preengagement, 'delivery': delivery, 'post': postengagement}
    return results

def count_checklist_for_region(regex, issue_description):
    '''Performs the actual [x] parsing for an individual segment of the overall checklist'''
    checked = 0
    unchecked = 0
    try:
        checklist_block = re.search(regex, issue_description).group()
        unchecked = re.findall(r'- \[ \]', checklist_block)
        checked = re.findall(r'- \[x\]', checklist_block, re.IGNORECASE)
        results = { 'checked': checked.count('- [x]') + checked.count('- [X]'), \
            'unchecked': unchecked.count('- [ ]')}
    except:
        print("*** Missing checklist block for regex ", regex)
        results = None

    return results

def update_discussion(discussion_id, title, body):
    '''Update the title and description of a specificed Discussion'''
    # Configure the mutation based on input data
    if discussion_id:
        mutation = 'mutation {update_discussion(input: {discussion_id: "{discussion_id}", body: "{body}", title: "{title}"}) {discussion {id}}}'
        mutation = mutation.replace("{discussion_id}", discussion_id)
    else:
        #TODO: Need Repository Id and Category Id
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

def get_monday_date(input_date = datetime.datetime.now()):
    '''Returns a Date object containing the Monday preceding (or today) the passed param'''
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
issue_data = get_project_data( ORGANIZATION, PROJECT_NUM, REPOSITORY)
issues = merge_issue_data(issue_data)

# Get the ID for the report discussion
report_id = get_report_discussion_id(issue_data)

# Build Status report
issue_details_md = get_issue_details(issues)
region_summary_md = get_issue_summary(issues, ['AMER','APAC','EMEA'])
travel_smmary_md = get_issue_summary(issues, [':house:',':airplane:'])
exception_md = get_exceptions(issues)

# Write the report to the reporting discussion description and title
body = '## Regional Summary\n*Last Updated: ' + str(datetime.date.today()) +\
    '*\n\n' + region_summary_md +\
    '\n\n## Travel Summary\n\n' + travel_smmary_md +\
    '\n\n## Request Details\n\n' + issue_details_md +\
    '\n\n## Exceptions\n\n' + exception_md
TITLE = get_report_title()

print(TITLE)
print(body)
update_discussion(DISCUSSION_ID, TITLE, body)
