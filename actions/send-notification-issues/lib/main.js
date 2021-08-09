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
exports.exists = void 0;
const core = __importStar(require("@actions/core"));
const github = __importStar(require("@actions/github"));
const fs_1 = require("fs");
function getIssues(issuesList) {
    if (!issuesList || issuesList.trim() === '') {
        return [];
    }
    const issues = issuesList.split(',').map(issue => {
        let issueNumber;
        let owner = github.context.repo.owner;
        let repo = github.context.repo.repo;
        issue = issue.trim();
        if (issue.includes('/')) {
            const parts = issue.split('/');
            owner = parts[0];
            repo = parts[1];
            issueNumber = parseInt(parts[2]);
        }
        else {
            issueNumber = parseInt(issue);
        }
        return {
            number: issueNumber,
            owner,
            repo
        };
    });
    return issues;
}
function sendNotifications(notificationIssue, notificationContent, token) {
    var _a, _b;
    return __awaiter(this, void 0, void 0, function* () {
        const octokit = github.getOctokit(token);
        core.debug(`getting issue ${notificationIssue.number} from ${notificationIssue.owner}/${notificationIssue.repo}`);
        const issue = yield octokit.rest.issues.get({
            owner: notificationIssue.owner,
            repo: notificationIssue.repo,
            issue_number: notificationIssue.number
        });
        if (((_a = issue.data.assignees) === null || _a === void 0 ? void 0 : _a.length) === 0) {
            core.warning(`issue ${notificationIssue.number} has no assignees. Cannot notify`);
            return;
        }
        const notificationList = (_b = issue.data.assignees) === null || _b === void 0 ? void 0 : _b.map(assignee => {
            return `@${assignee === null || assignee === void 0 ? void 0 : assignee.login}`;
        }).join(' ');
        const notificationBody = `${notificationList} \n\n${notificationContent} `;
        octokit.rest.issues.createComment({
            owner: notificationIssue.owner,
            repo: notificationIssue.repo,
            issue_number: notificationIssue.number,
            body: `${notificationBody} `
        });
    });
}
function exists(fsPath) {
    return __awaiter(this, void 0, void 0, function* () {
        try {
            yield fs_1.promises.stat(fsPath);
        }
        catch (err) {
            if (err.code === 'ENOENT') {
                return false;
            }
            throw err;
        }
        return true;
    });
}
exports.exists = exists;
function run() {
    return __awaiter(this, void 0, void 0, function* () {
        try {
            const contentPath = core.getInput('content-path', { required: true });
            const token = core.getInput('token');
            const issuesList = core.getInput('issues-list', {
                required: false
            });
            core.info(`issuesList: ${issuesList}`); // TODO: DEBUG
            if ((yield exists(contentPath)) === false) {
                core.setFailed(`File ${contentPath} does not exist.`);
                return;
            }
            const issues = getIssues(issuesList);
            if (issues.length === 0) {
                core.warning(`No issues list provided`);
            }
            else {
                const content = (yield fs_1.promises.readFile(contentPath)).toString();
                for (const issue of issues) {
                    yield sendNotifications(issue, content, token);
                }
            }
        }
        catch (error) {
            core.setFailed(error.message);
        }
    });
}
run();
