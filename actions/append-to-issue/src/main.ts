import * as core from '@actions/core'
import * as github from '@actions/github'
// import * as fs from 'fs/promises'
import {promises as fs} from 'fs'

async function getContent(contentPath: string): Promise<string> {
  const fileHandle = await fs.open(contentPath, 'r')
  try {
    return (await fileHandle.readFile()).toString()
  } finally {
    fileHandle.close()
  }
}

function bodyHasMarker(
  body: string | null | undefined,
  markerBegin: string
): boolean {
  if (body === null || body === undefined) return false

  return body.includes(markerBegin)
}

async function run(): Promise<void> {
  try {
    const number: number = parseInt(core.getInput('number', {required: true}))
    const contentPath: string = core.getInput('content-path', {required: true})
    const marker: string = core.getInput('marker')
    const token: string = core.getInput('token')

    const markerBegin = `<!-- ${marker}__BEGIN_DO_NOT_TOUCH -->`
    const markerEnd = `<!-- ${marker}__END_DO_NOT_TOUCH -->`

    core.debug(`Inspecting issue ${number}`)

    const octokit = github.getOctokit(token)

    const {data: issue} = await octokit.rest.issues.get({
      owner: github.context.repo.owner,
      repo: github.context.repo.repo,
      issue_number: number
    })

    const alreadyHasContent = bodyHasMarker(issue.body, markerBegin)

    core.debug(`Already has content=${alreadyHasContent}`)

    let contentAdded = false

    if (!alreadyHasContent) {
      core.debug(`Appending content from ${contentPath}`)

      const content = await getContent(contentPath)

      const body = `${issue.body}\n${markerBegin}\n${content}\n${markerEnd}`

      await octokit.rest.issues.update({
        issue_number: number,
        owner: github.context.repo.owner,
        repo: github.context.repo.repo,
        body
      })
      contentAdded = true
    }

    core.setOutput('content-added', contentAdded)
  } catch (error) {
    core.setFailed(error.message)
  }
}

run()
