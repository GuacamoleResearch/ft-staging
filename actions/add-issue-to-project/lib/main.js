"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    Object.defineProperty(o, k2, { enumerable: true, get: function() { return m[k]; } });
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", { value: true });
const core = __importStar(require("@actions/core"));
const github = __importStar(require("@actions/github"));
const utils_1 = require("@actions/github/lib/utils");
const queries_1 = require("./queries");
function getHeaders() {
    return {
        Accept: 'application/json',
        'GraphQL-Features': 'projects_next_graphql'
    };
}
function getProjectId(octokit, number, organization) {
    return __awaiter(this, void 0, void 0, function* () {
        core.debug(`Getting id for project ${number} in org ${organization}`);
        const result = yield octokit.graphql(queries_1.GET_PROJECT_QUERY, {
            organization,
            number,
            headers: getHeaders()
        });
        if (result.organization.projectNext === null) {
            throw new Error(`No project found for number ${number}`);
        }
        return result.organization.projectNext.id;
    });
}
function addIssueToProject(octokit, projectId, contentId) {
    return __awaiter(this, void 0, void 0, function* () {
        const result = yield octokit.graphql(queries_1.ADD_ISSUE_TO_PROJECT, {
            projectId,
            contentId,
            headers: getHeaders()
        });
        return result.addProjectNextItem.projectNextItem.id;
    });
}
function run() {
    return __awaiter(this, void 0, void 0, function* () {
        try {
            const projectNumber = parseInt(core.getInput('project-number', { required: true }));
            const issueNumber = parseInt(core.getInput('issue-number', { required: true }));
            const token = core.getInput('token');
            const organization = core.getInput('organization') || github.context.repo.owner;
            core.debug(`Looking for project ${projectNumber}`);
            const octokit = github.getOctokit(token);
            const projectId = yield getProjectId(octokit, projectNumber, organization);
            core.debug(`found projectid ${projectId} for project ${projectNumber}`);
            const issue = yield octokit.rest.issues.get({
                owner: utils_1.context.repo.owner,
                repo: utils_1.context.repo.repo,
                issue_number: issueNumber
            });
            core.debug(`Adding issue ${issueNumber} with id ${issue.data.node_id} to project ${projectNumber}`);
            yield addIssueToProject(octokit, projectId, issue.data.node_id);
            core.setOutput('title', issue.data.title);
        }
        catch (error) {
            core.setFailed(error.message);
        }
    });
}
run();
