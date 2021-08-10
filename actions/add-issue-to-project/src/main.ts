import * as core from '@actions/core'
import * as github from '@actions/github'
import {context} from '@actions/github/lib/utils'
import {Octokit} from '@octokit/core'
import {RequestHeaders} from '@octokit/types/dist-types/'
import {GET_PROJECT_QUERY, ADD_ISSUE_TO_PROJECT} from './queries'

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
    throw new Error(`No project found with number ${number}`)
  }

  return result.organization.projectNext.id
}

async function addIssueToProject(
  octokit: Octokit,
  projectId: string,
  contentId: string
): Promise<string> {
  const result: any = await octokit.graphql(ADD_ISSUE_TO_PROJECT, {
    projectId,
    contentId,
    headers: getHeaders()
  })

  return result.addProjectNextItem.projectNextItem.id
}

async function run(): Promise<void> {
  try {
    const projectNumber: number = parseInt(
      core.getInput('project-number', {required: true})
    )
    const issueNumber: number = parseInt(
      core.getInput('issue-number', {required: true})
    )
    const token: string = core.getInput('token')
    const organization =
      core.getInput('organization') || github.context.repo.owner

    core.debug(`Looking for project ${projectNumber}`)

    const octokit = github.getOctokit(token)

    const projectId = await getProjectId(octokit, projectNumber, organization)

    core.debug(`found projectid ${projectId} for project ${projectNumber}`)

    const issue = await octokit.rest.issues.get({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: issueNumber
    })

    core.debug(
      `Adding issue ${issueNumber} with id ${issue.data.node_id} to project ${projectNumber}`
    )

    await addIssueToProject(octokit, projectId, issue.data.node_id)

    core.setOutput('title', issue.data.title)
  } catch (error) {
    core.setFailed(error.message)
  }
}

run()
