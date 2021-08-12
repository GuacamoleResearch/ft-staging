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

async function getProject(
  octokit: Octokit,
  number: Number,
  organization: string
): Promise<any> {
  core.debug(`Getting project ${number} in org ${organization}`)

  const result: any = await octokit.graphql(GET_PROJECT_QUERY, {
    organization,
    number,
    headers: getHeaders()
  })

  if (result.organization.projectNext === null) {
    throw new Error(`No project found with number ${number}`)
  }

  return result
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

function getFieldByName(fieldNodes: any[], fieldName: string): any {
  return fieldNodes.find(
    (field: {name: string}) => fieldName.localeCompare(field.name) === 0
  )
}

function getFieldValueId(fieldValue: string, fieldMetadata: any): string {
  if (!fieldMetadata.settings) return fieldValue

  const settings = JSON.parse(fieldMetadata.settings)

  if (!settings || !settings.options) return fieldValue

  const options: Option[] = settings.options

  const option = options.find(o => fieldValue.localeCompare(o.name))

  if (option == null) {
    throw new Error(`No option found with name ${fieldValue}`)
  }

  return option.id
}

async function setIssueBoardFields(
  octokit: Octokit,
  project: any,
  setFields: any,
  issueId: string
): Promise<void> {
  let setFieldsGraphQL = ''
  const projectId = project.organization.projectNext.id

  for (const fieldName of Object.keys(setFields)) {
    const fieldValue = setFields[fieldName]

    core.debug(`setting field ${fieldName}`)

    const fieldMetadata = getFieldByName(
      project.organization.projectNext.fields.nodes,
      fieldName
    )

    if (fieldMetadata === null) {
      core.warning(`field definiton ${fieldName} not found`)

      core.debug(`fields=${project.organization.projectNext.fields.nodes}`)
      continue
    }

    const realFieldValue = getFieldValueId(fieldValue, fieldMetadata)

    setFieldsGraphQL += `set_${fieldName.replace(
      ' ',
      ''
    )} : updateProjectNextItemField(input: {
      projectId: $projectId itemId: $issueId fieldId: "${
        fieldMetadata.id
      }" value: "${realFieldValue}"
      }) { projectNextItem { id } }
    `
  }

  const mutation = `mutation ($projectId: ID!, $issueId: ID!) {
      ${setFieldsGraphQL}
    }`

  // TODO: Field must have selections (field 'updateProjectNextItemField' returns UpdateProjectNextItemFieldPayload but has no selections. Did you mean 'updateProjectNextItemField { ... }'?)
  core.debug(mutation)

  await octokit.graphql(mutation, {
    projectId,
    issueId,
    headers: getHeaders()
  })
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

    const setFieldsJSONString = core.getInput('set-fields', {
      required: false,
      trimWhitespace: true
    })

    core.debug(`Looking for project ${projectNumber}`)

    const octokit = github.getOctokit(token)

    const project = await getProject(octokit, projectNumber, organization)

    core.debug(JSON.stringify(project))

    const projectId = project.organization.projectNext.id

    core.debug(`found projectid ${projectId} for project ${projectNumber}`)

    const issue = await octokit.rest.issues.get({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: issueNumber
    })

    core.debug(
      `Adding issue ${issueNumber} with id ${issue.data.node_id} to project ${projectNumber}`
    )

    const issueInBoardId = await addIssueToProject(
      octokit,
      projectId,
      issue.data.node_id
    )

    if (setFieldsJSONString.length > 0) {
      core.debug(`Setting fields ${setFieldsJSONString}`)
      const setFields = JSON.parse(setFieldsJSONString)

      await setIssueBoardFields(octokit, project, setFields, issueInBoardId)
    }

    core.setOutput('title', issue.data.title)
  } catch (error) {
    core.setFailed(error.message)
  }
}

run()
