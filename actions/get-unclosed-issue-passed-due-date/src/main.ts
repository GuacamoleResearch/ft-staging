import * as core from '@actions/core'
import * as github from '@actions/github'
import {Octokit} from '@octokit/core'
import {RequestHeaders} from '@octokit/types/dist-types/'
import {DateTime, Duration} from 'luxon'
import {GET_PROJECT_QUERY, GET_ISSUES_QUERY} from './queries'

export interface Option {
  id: string
  name: string
  name_html: string
}

function getHeaders(): RequestHeaders {
  return {
    Accept: 'application/json',
    'GraphQL-Features': 'projects_next_graphql'
  }
}

function hasLabel(labels: {name: string}[], filterLabels: string[]): boolean {
  return (
    labels.findIndex(l =>
      filterLabels
        .map(label => label.toLowerCase())
        .includes(l.name.toLowerCase())
    ) !== -1
  )
}

async function getIssues(
  octokit: Octokit,
  projectId: string,
  columns: string[],
  filterLabels: string[],
  dueDateFieldName: string,
  thresholdDuration: Duration
): Promise<any> {
  core.debug(`Finding unclosed issues in columns [${columns}]`)

  let cursor = ''
  let hasNextPage = true
  let result = null
  while (hasNextPage) {
    const resultPage: any = await octokit.graphql(GET_ISSUES_QUERY, {
      projectId,
      cursor,
      headers: getHeaders()
    })
    cursor = resultPage.node.items.pageInfo.endCursor
    hasNextPage = resultPage.node.items.pageInfo.hasNextPage

    if (result) {
      result.node.items.nodes = result.node.items.nodes.concat(
        resultPage.node.items.nodes
      )
    } else {
      result = resultPage
    }

    core.debug(
      `#results ${resultPage.node.items.nodes.length} hasNextPage=${hasNextPage} cursor=${cursor}`
    )
  }

  if (!result.node.items.nodes || result.node.items.nodes.length === 0) {
    return null
  }

  let columnIds: string[] | null = null
  return result.node.items.nodes.filter(
    (item: {
      fieldValues: {nodes: any[]}
      content: {closed: any; labels: {nodes: any[]}}
    }) => {
      const status = getFieldByName(item.fieldValues.nodes, 'Status')

      if (!status) return false

      columnIds ||= getColumnIds(status, columns)

      const dueDateField = getFieldByName(
        item.fieldValues.nodes,
        dueDateFieldName
      )

      if (!dueDateField || dueDateField.value === '') return false

      const dueDate = DateTime.fromISO(dueDateField.value)

      return (
        !item.content.closed &&
        columnIds.includes(status.value) &&
        !hasLabel(item.content.labels.nodes, filterLabels) &&
        DateTime.now().plus(thresholdDuration) >= dueDate
      )
    }
  )
}

function getColumnIds(statusField: any, columns: string[]): string[] {
  const options: Option[] = JSON.parse(
    statusField.projectField.settings
  ).options

  const columnIds = options
    .filter(option => columns.includes(option.name))
    .map(option => option.id)

  return columnIds
}

function getFieldByName(fieldNodes: any[], fieldName: string): any {
  return fieldNodes.find(
    (field: {projectField: {name: string}}) =>
      field.projectField.name === fieldName
  )
}

async function getProjectId(
  octokit: Octokit,
  number: Number,
  organization: string
): Promise<string> {
  core.debug(`Getting id for project ${number} in org ${organization}`)

  const result: any = await octokit.graphql(GET_PROJECT_QUERY, {
    organization,
    number,
    headers: getHeaders()
  })

  if (result.organization.projectNext === null) {
    throw new Error(`No project found for number ${number}`)
  }

  return result.organization.projectNext.id
}

async function run(): Promise<void> {
  try {
    const number: number = parseInt(core.getInput('number', {required: true}))
    const columns: string = core.getInput('columns', {required: true})
    const token: string = core.getInput('token')
    const dueDateFieldName: string = core.getInput('due-date-field-name', {
      required: true
    })
    const dueDateThreshold: string = core.getInput('due-date-threshold', {
      required: true
    })
    const organization =
      core.getInput('organization') || github.context.repo.owner

    const filterLabelsList = (core.getInput('filter-labels') || '').split(',')

    const thresholdDuration = Duration.fromISO(dueDateThreshold)

    if (!thresholdDuration.valueOf()) {
      throw new Error(
        `due-date-threshold value ${dueDateThreshold} is not valid`
      )
    }

    core.debug(`Looking for project ${number}`)

    const octokit = github.getOctokit(token)

    const projectId = await getProjectId(octokit, number, organization)

    core.debug(`found projectid ${projectId} for project ${number}`)

    const issues: any = await getIssues(
      octokit,
      projectId,
      columns.split(','),
      filterLabelsList,
      dueDateFieldName,
      thresholdDuration
    )

    if (issues) {
      const issueNumbers = issues.map(
        (issue: {content: {number: any}}) => issue.content.number
      )

      const fullQualifiedIssueNumbers = issues.map(
        (issue: {
          content: {repository: {owner: {login: any}; name: any}; number: any}
        }) =>
          `${issue.content.repository.owner.login}/${issue.content.repository.name}/${issue.content.number}`
      )

      const repos = fullQualifiedIssueNumbers
        .map((item: string) => item.split('/').splice(0, 2).join('/'))
        .filter(
          (value: any, index: any, self: string | any[]) =>
            self.indexOf(value) === index
        )

      core.setOutput('issue-numbers', issueNumbers.join(','))
      core.setOutput('issues-list', fullQualifiedIssueNumbers.join(','))
      core.setOutput('has-multiple-repos', repos.length > 1)
    } else {
      core.setOutput('issue-numbers', '')
      core.setOutput('issues-list', '')
      core.setOutput('has-multiple-repos', false)
    }
  } catch (error) {
    core.setFailed(error.message)
  }
}

run()
