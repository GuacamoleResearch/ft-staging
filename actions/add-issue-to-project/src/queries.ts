export const GET_PROJECT_QUERY = `
query($organization: String!, $number: Int!){
    organization(login: $organization){
      projectNext(number: $number) {
       id
       fields(first: 100) {
        nodes { 
          id
          name
          settings
        }
      }
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
