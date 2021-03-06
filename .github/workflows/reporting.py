'''Provides functions to process and report on the FastTrack project board'''
import json
import os
import datetime
import re
import requests

# pylint: disable=C0321

#region Configuration Variables
STATUS_MAP    = None
STATUS_HEADERS= {'':0, '1-Approved':0, '2-Scheduled':0, '3-Delivering':0, '4-Done':0, '5-Archive':0}
#endregion

# Debugging in the production instance...
ORGANIZATION = 'github'
PROJECT_NUM = 2890
REPOSITORY = 'FastTrack'
DISCUSSION_ID = 'MDEwOkRpc2N1c3Npb24zNTI4MTE5'
#endregion

class GitHubWrapper():
    '''Wrapper class for GitHub GraphQL interactions'''
    #region GraphQL Query contstant
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
    #endregion

    def __init__(self):
        self.organization   = os.environ.get('ORG')  or "GuacamoleResearch"
        self.project        = os.environ.get('PROJ') or 4
        self.repository     = os.environ.get('REPO') or "ft-staging"
        self.discussion_id  = os.environ.get('DISC_ID') or "MDEwOkRpc2N1c3Npb24zNTIzOTQy"
        self.token          = os.environ["FASTTRACK_PROJECT_TOKEN"]
        self.query_results = None
        # Debug variables
        self.organization   = 'github'
        self.project        = 2890
        self.repository     = 'FastTrack'
        self.discussion_id  = 'MDEwOkRpc2N1c3Npb24zNTI4MTE5'

    def get_project_data(self, report_title):
        '''Returns query results for FastTrack Issues + Memex'''
        # Standard Python Format doesn't seem to work with multi-line, so using 'replace'
        issue_query = self.GRAPHQL_QUERY.replace("{0}", self.organization)\
            .replace("{1}", str(self.project))\
            .replace("{2}", self.repository)\
            .replace("{3}", report_title)

        response = requests.post(
            'https://api.github.com/graphql',
            json={'query':issue_query},
            headers={'Authorization':'bearer '+self.token, \
                'GraphQL-Features':'projects_next_graphql' }
        )
        if response:
            self.query_results = response.json()
        return self.query_results

    def get_report_discussion_id(self):
        '''Get the discussion ID for the report and create if it doesn't exist'''
        self.discussion_id = self.query_results['data']['search']['nodes'][0]['id'] \
            if self.query_results['data']['search']['nodes'] \
            else None

        # Create a discussion if it doesn't exist
        if not self.discussion_id:
            #TODO: Create discussion
            print('No discussion found for the report - need to create one here')
            self.discussion_id = DISCUSSION_ID # cop out for now...

        return self.discussion_id

    def set_discussion_description(self, title, post_body):
        '''Update the title and description of a specificed Discussion'''
        repository = 'TODO'
        category = 'TODO'

        # Configure the mutation based on input data
        if self.discussion_id:
            mutation=f'mutation {{updateDiscussion(input: {{discussionId: "{self.discussion_id}", '
        else:
            #TODO: Need to look up Repository Id and Category Id
            mutation = 'mutation {createDiscussion(input: {repository: ' \
                + f'"{repository}", category:"{category}", '
        mutation += f'body: "{post_body}", title: "{title}"}}) {{discussion {{id}}}}}}'

        # Execute the mutation and return the discussion id
        response = requests.post(
            'https://api.github.com/graphql',
            json={'query':mutation},
            headers={'Authorization':'bearer '+self.token, \
                'GraphQL-Features':'projects_next_graphql' }
        )
        if response:
            response_data = response.json()["data"]
            return response_data["updateDiscussion"]["discussion"]["id"] \
                if response_data["updateDiscussion"] \
                    else response_data["createDiscussion"]["discussion"]["id"]
        return -1

    def add_discussion_comment(self, comment_markdown):
        '''Add a new discussion comment for a given discussion'''
        #TODO: GraphQL query to add a discussion comment
        print(f"TODO - Add comment:\n{comment_markdown}")
        return

class ReportUtilities():
    '''Collection of functions used for string parsing'''
    @staticmethod
    def dates_from_issue_title(title):
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
            if date_range[1] < date_range[0]:
                date_range[1] = datetime.date( \
                    date_range[1].year+1, date_range[1].month, date_range[1].day)
            return {"start": date_range[0], "finish": date_range[1]}
        except (IndexError, ValueError):
            print(f"Error parsing dates for '{title}'")
            return {"start": None, "finish": None}

    @staticmethod
    def get_report_title():
        '''Get the title of the report'''
        return 'FastTrack Status Report (week of ' + str(ReportUtilities.get_monday_date()) + ')'

    @staticmethod
    def format_url(org, repo, issue_id):
        '''Returns markdown for a link with the title for a given issue'''
        return f'https://github.com/{org}/{repo}/issues/{issue_id}'

    @staticmethod
    def get_monday_date(input_date = datetime.datetime.now()):
        '''Returns a Date object containing the Monday preceding (or today) the passed param'''
        # Get the date of the Monday of the given date
        results = input_date - datetime.timedelta(days=input_date.weekday())
        return results.date() if isinstance(results, datetime.datetime) else results

    @staticmethod
    def count_checklist(issue_description):
        '''Parse the issue description to count "[ ]" and "[x]" per checklist'''
        # Pre-engagement Regex - "### Pre((.|\n)*)### Del"
        preengagement = ReportUtilities.count_checklist_for_region( \
            "### Pre((.|\n)*)### Del", issue_description)

        # Delivery Regex - "### Pel((.|\n)*)### Post"
        delivery = ReportUtilities.count_checklist_for_region( \
            "### Del((.|\n)*)### Post", issue_description)

        # Post-engagement Regex - "### Post((.|\n)*)$"
        postengagement = ReportUtilities.count_checklist_for_region( \
            "### Post((.|\n)*)$", issue_description)

        results = {'pre':preengagement, 'delivery': delivery, 'post': postengagement}
        return results

    @staticmethod
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
        except AttributeError:
            print("*** Missing checklist block for regex ", regex)
            results = None

        return results


#region FUNCTIONS: Build master issue list
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
        dates = ReportUtilities.dates_from_issue_title(issue['Title'])
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
                    field_name = field['projectField']['name']
                    issue[field_name] = field['value']
                issue['Status'] = map_status_field(project_issue_results, issue)
            # Handle exception case for issues not yet on the board
            if not issue.get('Status'):
                issue['Status'] = ''

    return issue_list

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
def get_issue_summary(issue_list, target_labels):
    '''Build summary issue count by status (columns) and region or remote (rows)'''
    # Initialize data structure based on target labels
    rows = {'TBD':dict.copy(STATUS_HEADERS)}
    for label in target_labels:
        rows[label] = dict.copy(STATUS_HEADERS)

    # Generate a per-label, per-status counts
    for issue in issue_list:
        labels = issue['Labels']
        found_row = False
        for row_label, status_count in rows.items():
            if str(labels).find(row_label) >= 0:
                status_count[issue['Status']] += 1
                found_row = True
        if not found_row:
            rows['TBD'][issue['Status']] += 1

    # Convert the data structure to MD
    # Start with the header
    markdown = '| '
    for status in sorted(STATUS_HEADERS):
        row_header = status if (status!='') else 'None'
        markdown += '| ' + row_header
    markdown += ' |\n|-|-|-|-|-|-|-|\n'

    # Add the body of the table
    for row_label, status_count in rows.items():
        markdown += '| ' + row_label
        for status in status_count:
            markdown += '| ' + str(status_count[status])
        markdown += ' |\n'

    return markdown

def get_issue_details(all_issues):
    '''Build list of issues by state with hyperlinks'''
    global STATUS_MAP, ORGANIZATION, REPOSITORY
    status_list = {}
    issue_details = ''
    for status in STATUS_MAP:
        for issue in all_issues:
            issue_link = ReportUtilities.format_url(ORGANIZATION, REPOSITORY, issue['Number'])
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
def get_exceptions(all_issues):
    '''Generate a list of exceptions by assignee'''
    issues_list = {}

    # Loop through all issues and build a list of exceptions
    for issue in all_issues:
        process_exceptions(issues_list, issue)

    # Convert the data structure to MD
    exception_markdown = ''
    for assignee, messages in issues_list.items():
        exception_markdown += '\n' + assignee + ' - Please review the following exceptions:\n'
        for message in messages:
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
    checklists = ReportUtilities.count_checklist(issue['Body'])

    # Process global exceptions then exceptions for each status
    if (checklists is None) or (checklists['pre'] is None) \
        or (checklists['post'] is None) or (checklists['delivery'] is None):
        add_exception(issues_list, '@dmckinstry', issue_title, \
            issue_id, 'Invalid checklist for {issue_link}')
    # Only look for exceptions after followup dates
    elif followup <= datetime.datetime.now():
        if status == '1-Approved':
            if checklists['pre']['checked'] < 3:
                add_exception(issues_list, 'dmckinstry', issue_title, issue_id, \
                    'Incomplete pre-engagement checklist for Approved {issue_link} FastTrack')
        elif status == '2-Scheduled':
            if checklists['pre']['unchecked'] > 0:
                add_exception(issues_list, 'dmckinstry', issue_title, issue_id, \
                    'Incomplete pre-engagement checklist for Scheduled {issue_link} FastTrack')
        elif status == '3-Delivering':
            if checklists['delivery']['unchecked'] > 0:
                add_exception(issues_list, 'dmckinstry', issue_title, issue_id, \
                    'Incomplete delivery checklist for the {issue_link} FastTrack')
        elif status == '4-Done':
            if checklists['delivery']['unchecked'] > 0:
                add_exception(issues_list, 'dmckinstry', issue_title, issue_id, \
                    'Incomplete delivery checklist for the {issue_link} FastTrack')
            if checklists['post']['unchecked'] > 0:
                add_exception(issues_list, assignees, issue_title, issue_id, \
                    'Incomplete delivery checklist for the {issue_link} FastTrack')

def add_exception(issues_list, assignees, issue_title, issue_id, message):
    '''Add an exception to the list'''
    if isinstance(assignees, str):
        assignees = [re.sub(r"[\['\]]", "", assignees)]
    for assignee in assignees:
        if not issues_list.get(assignee):
            issues_list[assignee] = []

        issue_link = '[' + issue_title + '](' \
            + ReportUtilities.format_url(ORGANIZATION, REPOSITORY, issue_id) +')'
        issues_list[assignee].append('- ' + message.replace('{issue_link}', issue_link))

#endregion

#region FUNCTIONS: Utilities

#endregion

#----------------------------------------------------------------------------
#----------------------------------------------------------------------------
#
# Begin Main
#

gitHub = GitHubWrapper()

# Determine the report title based on current date
REPORT_TITLE = ReportUtilities.get_report_title()

# Read issues and summarize issue counts
issue_data = gitHub.get_project_data(REPORT_TITLE)

# Get the ID for the report discussion
report_id = gitHub.get_report_discussion_id()

# Process the query resultws into usable issue data
issues = merge_issue_data(issue_data)

# Build Status report markdown
issue_details_md = get_issue_details(issues)
region_summary_md = get_issue_summary(issues, ['AMER','APAC','EMEA'])
travel_smmary_md = get_issue_summary(issues, [':house:',':airplane:'])
exception_md = get_exceptions(issues)

# Write the report to the reporting discussion description and title
body = '## Regional Summary\n*Last Updated: ' + str(datetime.date.today()) +\
    '*\n\n' + region_summary_md +\
    '\n\n## Travel Summary\n\n' + travel_smmary_md +\
    '\n\n## Request Details\n\n' + issue_details_md

# Update the discussion description
print(REPORT_TITLE)
print(body)
discussion_identifier = gitHub.set_discussion_description(REPORT_TITLE, body)

# Add an exception report comment to the discussion
discussion_comment = f'## Exceptions as of {datetime.datetime.utcnow()} UTC\n{exception_md}'
print(discussion_comment)
gitHub.add_discussion_comment(discussion_comment)
