/**
 * 代码地图视图提供者
 */

import * as vscode from 'vscode';
import { ApiService } from './apiService';

export class CodeMapProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'aiCodeMap';

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
                case 'refresh':
                    await this._refreshMap();
                    break;
            }
        });
    }

    private async _refreshMap() {
        try {
            const map = await this._apiService.getGlobalMap();
            this._view?.webview.postMessage({
                command: 'updateMap',
                map: map,
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
    <title>全局代码地图</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 10px;
            margin: 0;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .refresh-btn {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 5px 10px;
            cursor: pointer;
            border-radius: 3px;
        }
        .refresh-btn:hover {
            background: var(--vscode-button-hoverBackground);
        }
        .layer {
            margin: 10px 0;
            padding: 10px;
            background: var(--vscode-textBlockQuote-background);
            border-radius: 5px;
        }
        .layer-title {
            font-weight: bold;
            margin-bottom: 5px;
            color: var(--vscode-foreground);
        }
        .file-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .file-item {
            padding: 3px 5px;
            cursor: pointer;
            font-size: 13px;
        }
        .file-item:hover {
            background: var(--vscode-list-hoverBackground);
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: var(--vscode-descriptionForeground);
        }
        .error {
            color: var(--vscode-errorForeground);
            padding: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h3>全局代码地图</h3>
        <button class="refresh-btn" id="refreshBtn">刷新</button>
    </div>
    <div id="content">
        <div class="loading">加载中...</div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();

        document.getElementById('refreshBtn').addEventListener('click', () => {
            vscode.postMessage({ command: 'refresh' });
        });

        window.addEventListener('message', event => {
            const message = event.data;
            const content = document.getElementById('content');

            switch (message.command) {
                case 'updateMap':
                    const map = message.map;
                    let html = '';

                    if (map.layers) {
                        for (const [layerName, files] of Object.entries(map.layers)) {
                            html += \`
                                <div class="layer">
                                    <div class="layer-title">\${layerName}</div>
                                    <ul class="file-list">
                                        \${files.map(f => \`<li class="file-item" data-file="\${f}">\${f}</li>\`).join('')}
                                    </ul>
                                </div>
                            \`;
                        }
                    } else {
                        html = '<div class="error">暂无数据，请先索引项目</div>';
                    }

                    content.innerHTML = html;

                    // 添加点击事件
                    document.querySelectorAll('.file-item').forEach(item => {
                        item.addEventListener('click', () => {
                            vscode.postMessage({
                                command: 'openFile',
                                file: item.dataset.file
                            });
                        });
                    });
                    break;

                case 'error':
                    content.innerHTML = \`<div class="error">\${message.message}</div>\`;
                    break;
            }
        });

        // 初始加载
        vscode.postMessage({ command: 'refresh' });
    </script>
</body>
</html>`;
    }
}
