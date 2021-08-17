import * as core from '@actions/core'
import * as github from '@actions/github'

async function run(): Promise<void> {
  try {
    const number: number = parseInt(core.getInput('number', {required: true}))
    const token: string = core.getInput('token')
    const assigneesString = core.getInput('assignees', {required: true})

    core.debug(`Setting assignees for issue ${number}`)

    const assignees = assigneesString
      .split(',')
      .map(assigneeName => assigneeName.trim())

    const octokit = github.getOctokit(token)

    core.info(`Assigning issue ${number} to users ${JSON.stringify(assignees)}`)

    await octokit.rest.issues.addAssignees({
      owner: github.context.repo.owner,
      repo: github.context.repo.repo,
      issue_number: number,
      assignees
    })
  } catch (error) {
    core.setFailed(error.message)
  }
}

run()
