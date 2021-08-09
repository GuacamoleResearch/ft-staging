import * as core from '@actions/core'
import * as github from '@actions/github'
import {promises as fs} from 'fs'

interface Issue {
  number: number
  owner: string
  repo: string
}

function getIssues(issuesList: string): Issue[] {
  if (!issuesList || issuesList.trim() === '') {
    return []
  }

  const issues = issuesList.split(',').map(issue => {
    let issueNumber: number
    let owner: string = github.context.repo.owner
    let repo: string = github.context.repo.repo

    issue = issue.trim()

    if (issue.includes('/')) {
      const parts = issue.split('/')

      owner = parts[0]
      repo = parts[1]
      issueNumber = parseInt(parts[2])
    } else {
      issueNumber = parseInt(issue)
    }

    return {
      number: issueNumber,
      owner,
      repo
    }
  })

  return issues
}

async function sendNotifications(
  notificationIssue: Issue,
  notificationContent: string,
  token: string
): Promise<void> {
  const octokit = github.getOctokit(token)

  core.debug(
    `getting issue ${notificationIssue.number} from ${notificationIssue.owner}/${notificationIssue.repo}`
  )

  const issue = await octokit.rest.issues.get({
    owner: notificationIssue.owner,
    repo: notificationIssue.repo,
    issue_number: notificationIssue.number
  })

  if (issue.data.assignees?.length === 0) {
    core.warning(
      `issue ${notificationIssue.number} has no assignees. Cannot notify`
    )
    return
  }

  const notificationList = issue.data.assignees
    ?.map(assignee => {
      return `@${assignee?.login}`
    })
    .join(' ')

  const notificationBody = `${notificationList} \n\n${notificationContent} `

  octokit.rest.issues.createComment({
    owner: notificationIssue.owner,
    repo: notificationIssue.repo,
    issue_number: notificationIssue.number,
    body: `${notificationBody} `
  })
}

export async function exists(fsPath: string): Promise<boolean> {
  try {
    await fs.stat(fsPath)
  } catch (err) {
    if (err.code === 'ENOENT') {
      return false
    }

    throw err
  }

  return true
}

async function run(): Promise<void> {
  try {
    const contentPath = core.getInput('content-path', {required: true})
    const token = core.getInput('token')
    const issuesList = core.getInput('issues-list', {
      required: false
    })

    core.info(`issuesList: ${issuesList}`) // TODO: DEBUG

    if ((await exists(contentPath)) === false) {
      core.setFailed(`File ${contentPath} does not exist.`)
      return
    }

    const issues = getIssues(issuesList)

    if (issues.length === 0) {
      core.warning(`No issues list provided`)
    } else {
      const content = (await fs.readFile(contentPath)).toString()

      for (const issue of issues) {
        await sendNotifications(issue, content, token)
      }
    }
  } catch (error) {
    core.setFailed(error.message)
  }
}

run()
