export const GET_PROJECT_QUERY = `
query($organization: String!, $number: Int!){
    organization(login: $organization){
      projectNext(number: $number) {
       id
       title      
      }
    }
}`

export const GET_ISSUES_QUERY = `
query($projectId: ID!, $cursor:String) {
  node(id: $projectId) {
    ... on ProjectNext {
      items(first: 100, after: $cursor) {
        pageInfo {
          endCursor
          hasNextPage
        }
        nodes{
          id
          title
          fieldValues(first: 100) {
            nodes{
              value
              projectField{
                name
                settings
              }
            }
          }
          content{
            ...on Issue {
              closed
              number
              repository {
                owner {
                  login                    
                }
                name
              }
              labels(first: 100) {
                nodes {
                  name
                }
              }
            }
          }
        }
      }
    }
  }
}`
