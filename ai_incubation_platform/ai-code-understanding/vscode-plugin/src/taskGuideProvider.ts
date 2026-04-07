/**
 * 任务引导视图提供者
 */

import * as vscode from 'vscode';
import { ApiService } from './apiService';

export class TaskGuideProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'aiTaskGuide';

    private _view?: vscode.WebviewView;
    private _extensionUri: vscode.Uri;
    private _apiService: ApiService;

    constructor(extensionUri: vscode.Uri, apiService: ApiService) {
        this._extensionUri = extensionUri;
        this._apiService = apiService;
    }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri],
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView);

        // 监听消息
        webviewView.webview.onDidReceiveMessage(async (message) => {
            switch (message.command) {
                case 'getGuide':
                    await this._getTaskGuide(message.task);
                    break;
            }
        });
    }

    private async _getTaskGuide(task: string) {
        try {
            this._view?.webview.postMessage({
                command: 'loading',
            });

            const result = await this._apiService.getTaskGuide(task);
            this._view?.webview.postMessage({
                command: 'updateGuide',
                result: result,
            });
        } catch (error: any) {
            this._view?.webview.postMessage({
                command: 'error',
                message: error.message,
            });
        }
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>任务引导</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 10px;
            margin: 0;
        }
        .input-section {
            margin-bottom: 15px;
        }
        .input-box {
            width: 100%;
            padding: 8px;
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
            border-radius: 3px;
            box-sizing: border-box;
        }
        .submit-btn {
            width: 100%;
            margin-top: 10px;
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 8px 15px;
            cursor: pointer;
            border-radius: 3px;
        }
        .submit-btn:hover {
            background: var(--vscode-button-hoverBackground);
        }
        .guide-section {
            display: none;
        }
        .guide-section.visible {
            display: block;
        }
        .step {
            margin: 10px 0;
            padding: 10px;
            background: var(--vscode-textBlockQuote-background);
            border-left: 3px solid var(--vscode-progressBar-background);
            border-radius: 3px;
        }
        .step-number {
            font-weight: bold;
            color: var(--vscode-foreground);
        }
        .step-file {
            color: var(--vscode-textLink-foreground);
            cursor: pointer;
        }
        .step-reason {
            color: var(--vscode-descriptionForeground);
            font-size: 13px;
            margin-top: 5px;
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: var(--vscode-descriptionForeground);
            display: none;
        }
        .loading.visible {
            display: block;
        }
        .error {
            color: var(--vscode-errorForeground);
            padding: 10px;
            display: none;
        }
        .error.visible {
            display: block;
        }
    </style>
</head>
<body>
    <h3>任务引导阅读路径</h3>

    <div class="input-section">
        <input type="text" class="input-box" id="taskInput" placeholder="输入任务描述，例如：添加一个新的 API 端点">
        <button class="submit-btn" id="submitBtn">生成阅读路径</button>
    </div>

    <div class="loading" id="loading">正在分析任务，生成阅读路径...</div>
    <div class="error" id="error"></div>

    <div class="guide-section" id="guideSection">
        <h4>建议阅读顺序</h4>
        <div id="steps"></div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();

        document.getElementById('submitBtn').addEventListener('click', () => {
            const task = document.getElementById('taskInput').value;
            if (!task) {
                alert('请输入任务描述');
                return;
            }
            vscode.postMessage({ command: 'getGuide', task: task });
        });

        // 支持回车提交
        document.getElementById('taskInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                document.getElementById('submitBtn').click();
            }
        });

        window.addEventListener('message', event => {
            const message = event.data;
            const loading = document.getElementById('loading');
            const error = document.getElementById('error');
            const guideSection = document.getElementById('guideSection');
            const steps = document.getElementById('steps');

            switch (message.command) {
                case 'loading':
                    loading.classList.add('visible');
                    error.classList.remove('visible');
                    guideSection.classList.remove('visible');
                    break;

                case 'error':
                    loading.classList.remove('visible');
                    error.textContent = '错误：' + message.message;
                    error.classList.add('visible');
                    guideSection.classList.remove('visible');
                    break;

                case 'updateGuide':
                    loading.classList.remove('visible');
                    const result = message.result;

                    if (result.reading_order && result.reading_order.length > 0) {
                        let html = '';
                        result.reading_order.forEach((step, index) => {
                            html += \`
                                <div class="step">
                                    <div class="step-number">\${index + 1}. \${step.file}</div>
                                    <div class="step-reason">\${step.reason}</div>
                                </div>
                            \`;
                        });
                        steps.innerHTML = html;
                        guideSection.classList.add('visible');
                    } else {
                        error.textContent = '未找到相关的阅读路径';
                        error.classList.add('visible');
                    }
                    break;
            }
        });
    </script>
</body>
</html>`;
    }
}
