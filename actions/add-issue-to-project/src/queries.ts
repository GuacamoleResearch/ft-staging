export const GET_PROJECT_QUERY = `
query($organization: String!, $number: Int!){
    organization(login: $organization){
      projectNext(number: $number) {
       id
       title      
      }
    }
}`

export const ADD_ISSUE_TO_PROJECT = `
mutation ($projectId: ID!, $contentId: ID!) {
  addProjectNextItem(input: {projectId: $projectId, contentId: $contentId}) {
    projectNextItem {
      id
    }
  }
}`
