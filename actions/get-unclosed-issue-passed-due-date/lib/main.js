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
const luxon_1 = require("luxon");
const queries_1 = require("./queries");
function getHeaders() {
    return {
        Accept: 'application/json',
        'GraphQL-Features': 'projects_next_graphql'
    };
}
function hasLabel(labels, filterLabels) {
    return (labels.findIndex(l => filterLabels
        .map(label => label.toLowerCase())
        .includes(l.name.toLowerCase())) !== -1);
}
function getIssues(octokit, projectId, columns, filterLabels, dueDateFieldName, thresholdDuration) {
    return __awaiter(this, void 0, void 0, function* () {
        core.debug(`Finding unclosed issues in columns [${columns}]`);
        let cursor = '';
        let hasNextPage = true;
        let result = null;
        while (hasNextPage) {
            const resultPage = yield octokit.graphql(queries_1.GET_ISSUES_QUERY, {
                projectId,
                cursor,
                headers: getHeaders()
            });
            cursor = resultPage.node.items.pageInfo.endCursor;
            hasNextPage = resultPage.node.items.pageInfo.hasNextPage;
            if (result) {
                result.node.items.nodes = result.node.items.nodes.concat(resultPage.node.items.nodes);
            }
            else {
                result = resultPage;
            }
            core.debug(`#results ${resultPage.node.items.nodes.length} hasNextPage=${hasNextPage} cursor=${cursor}`);
        }
        if (!result.node.items.nodes || result.node.items.nodes.length === 0) {
            return null;
        }
        let columnIds = null;
        return result.node.items.nodes.filter((item) => {
            const status = getFieldByName(item.fieldValues.nodes, 'Status');
            if (!status)
                return false;
            columnIds || (columnIds = getColumnIds(status, columns));
            const dueDateField = getFieldByName(item.fieldValues.nodes, dueDateFieldName);
            if (!dueDateField || dueDateField.value === '')
                return false;
            const dueDate = luxon_1.DateTime.fromISO(dueDateField.value);
            return (!item.content.closed &&
                columnIds.includes(status.value) &&
                !hasLabel(item.content.labels.nodes, filterLabels) &&
                luxon_1.DateTime.now().plus(thresholdDuration) >= dueDate);
        });
    });
}
function getColumnIds(statusField, columns) {
    const options = JSON.parse(statusField.projectField.settings).options;
    const columnIds = options
        .filter(option => columns.includes(option.name))
        .map(option => option.id);
    return columnIds;
}
function getFieldByName(fieldNodes, fieldName) {
    return fieldNodes.find((field) => field.projectField.name === fieldName);
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
function run() {
    return __awaiter(this, void 0, void 0, function* () {
        try {
            const number = parseInt(core.getInput('number', { required: true }));
            const columns = core.getInput('columns', { required: true });
            const token = core.getInput('token');
            const dueDateFieldName = core.getInput('due-date-field-name', {
                required: true
            });
            const dueDateThreshold = core.getInput('due-date-threshold', {
                required: true
            });
            const organization = core.getInput('organization') || github.context.repo.owner;
            const filterLabelsList = (core.getInput('filter-labels') || '').split(',');
            const thresholdDuration = luxon_1.Duration.fromISO(dueDateThreshold);
            if (!thresholdDuration.valueOf()) {
                throw new Error(`due-date-threshold value ${dueDateThreshold} is not valid`);
            }
            core.debug(`Looking for project ${number}`);
            const octokit = github.getOctokit(token);
            const projectId = yield getProjectId(octokit, number, organization);
            core.debug(`found projectid ${projectId} for project ${number}`);
            const issues = yield getIssues(octokit, projectId, columns.split(','), filterLabelsList, dueDateFieldName, thresholdDuration);
            if (issues) {
                const issueNumbers = issues.map((issue) => issue.content.number);
                const fullQualifiedIssueNumbers = issues.map((issue) => `${issue.content.repository.owner.login}/${issue.content.repository.name}/${issue.content.number}`);
                const repos = fullQualifiedIssueNumbers
                    .map((item) => item.split('/').splice(0, 2).join('/'))
                    .filter((value, index, self) => self.indexOf(value) === index);
                core.setOutput('issue-numbers', issueNumbers.join(','));
                core.setOutput('issues-list', fullQualifiedIssueNumbers.join(','));
                core.setOutput('has-multiple-repos', repos.length > 1);
            }
            else {
                core.setOutput('issue-numbers', '');
                core.setOutput('issues-list', '');
                core.setOutput('has-multiple-repos', false);
            }
        }
        catch (error) {
            core.setFailed(error.message);
        }
    });
}
run();
