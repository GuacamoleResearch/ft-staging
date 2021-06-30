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
// import * as fs from 'fs/promises'
const fs_1 = require("fs");
function getContent(contentPath) {
    return __awaiter(this, void 0, void 0, function* () {
        const fileHandle = yield fs_1.promises.open(contentPath, 'r');
        try {
            return (yield fileHandle.readFile()).toString();
        }
        finally {
            fileHandle.close();
        }
    });
}
function bodyHasMarker(body, markerBegin) {
    if (body === null || body === undefined)
        return false;
    return body.includes(markerBegin);
}
function run() {
    return __awaiter(this, void 0, void 0, function* () {
        try {
            const number = parseInt(core.getInput('number', { required: true }));
            const contentPath = core.getInput('content-path', { required: true });
            const marker = core.getInput('marker');
            const token = core.getInput('token');
            const markerBegin = `<!-- ${marker}__BEGIN_DO_NOT_TOUCH -->`;
            const markerEnd = `<!-- ${marker}__END_DO_NOT_TOUCH -->`;
            core.debug(`Inspecting issue ${number}`);
            const octokit = github.getOctokit(token);
            const { data: issue } = yield octokit.rest.issues.get({
                owner: github.context.repo.owner,
                repo: github.context.repo.repo,
                issue_number: number
            });
            const alreadyHasContent = bodyHasMarker(issue.body, markerBegin);
            core.debug(`Already has content=${alreadyHasContent}`);
            let contentAdded = false;
            if (!alreadyHasContent) {
                core.debug(`Appending content from ${contentPath}`);
                const content = yield getContent(contentPath);
                const body = `${issue.body}\n${markerBegin}\n${content}\n${markerEnd}`;
                yield octokit.rest.issues.update({
                    issue_number: number,
                    owner: github.context.repo.owner,
                    repo: github.context.repo.repo,
                    body
                });
                contentAdded = true;
            }
            core.setOutput('content-added', contentAdded);
        }
        catch (error) {
            core.setFailed(error.message);
        }
    });
}
run();
