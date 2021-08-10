"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ADD_ISSUE_TO_PROJECT = exports.GET_PROJECT_QUERY = void 0;
exports.GET_PROJECT_QUERY = `
query($organization: String!, $number: Int!){
    organization(login: $organization){
      projectNext(number: $number) {
       id
       title      
      }
    }
}`;
exports.ADD_ISSUE_TO_PROJECT = `
mutation ($projectId: ID!, $contentId: ID!) {
  addProjectNextItem(input: {projectId: $projectId, contentId: $contentId}) {
    projectNextItem {
      id
    }
  }
}`;
