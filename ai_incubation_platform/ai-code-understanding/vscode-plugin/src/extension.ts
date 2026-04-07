/**
 * AI Code Understanding VSCode 插件入口
 *
 * 功能:
 * 1. 全局代码地图展示
 * 2. 任务引导阅读路径
 * 3. 代码解释 (带引用)
 * 4. 符号引用查找
 * 5. 依赖关系分析
 */

import * as vscode from 'vscode';
import axios from 'axios';
import { CodeMapProvider } from './codeMapProvider';
import { TaskGuideProvider } from './taskGuideProvider';
import { ApiService } from './apiService';

let apiService: ApiService;
let codeMapView: vscode.WebviewView | undefined;
let taskGuideView: vscode.WebviewView | undefined;

/**
 * 插件激活入口
 */
export function activate(context: vscode.ExtensionContext) {
    console.log('AI Code Understanding 插件已激活');

    // 初始化 API 服务
    const config = vscode.workspace.getConfiguration('aiCodeUnderstanding');
    const serverUrl = config.get('serverUrl', 'http://localhost:8000');
    apiService = new ApiService(serverUrl);

    // 注册代码地图提供者
    const codeMapProvider = new CodeMapProvider(context.extensionUri, apiService);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('aiCodeMap', codeMapProvider)
    );

    // 注册任务引导提供者
    const taskGuideProvider = new TaskGuideProvider(context.extensionUri, apiService);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('aiTaskGuide', taskGuideProvider)
    );

    // 注册命令
    context.subscriptions.push(
        vscode.commands.registerCommand('aiCodeUnderstanding.showGlobalMap', () => {
            showGlobalMap(codeMapProvider);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('aiCodeUnderstanding.showTaskGuide', () => {
            showTaskGuide(taskGuideProvider);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('aiCodeUnderstanding.indexProject', () => {
            indexProject();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('aiCodeUnderstanding.explainCode', () => {
            explainCode();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('aiCodeUnderstanding.findReadingPath', () => {
            findReadingPath();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('aiCodeUnderstanding.analyzeDependency', () => {
            analyzeDependency();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('aiCodeUnderstanding.showSymbolReferences', () => {
            showSymbolReferences();
        })
    );

    // 自动索引 (如果配置启用)
    const autoIndex = config.get('autoIndex', true);
    if (autoIndex && vscode.workspace.workspaceFolders) {
        indexProject();
    }

    console.log('AI Code Understanding 插件命令已注册');
}

/**
 * 显示全局地图
 */
async function showGlobalMap(provider: CodeMapProvider) {
    const view = await vscode.window.showWebviewViewPanel(
        'aiCodeMap',
        '全局代码地图',
        vscode.ViewColumn.One,
        {
            enableScripts: true,
            retainContextWhenHidden: true
        }
    );
    codeMapView = view;
}

/**
 * 显示任务引导
 */
async function showTaskGuide(provider: TaskGuideProvider) {
    const view = await vscode.window.showWebviewViewPanel(
        'aiTaskGuide',
        '任务引导阅读路径',
        vscode.ViewColumn.Two,
        {
            enableScripts: true,
            retainContextWhenHidden: true
        }
    );
    taskGuideView = view;
}

/**
 * 索引项目
 */
async function indexProject() {
    if (!vscode.workspace.workspaceFolders) {
        vscode.window.showErrorMessage('请先打开一个项目');
        return;
    }

    const workspaceFolder = vscode.workspace.workspaceFolders[0];
    const projectPath = workspaceFolder.uri.fsPath;
    const projectName = workspaceFolder.name;

    vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: '正在索引项目...',
            cancellable: false
        },
        async (progress) => {
            try {
                progress.report({ increment: 0, message: '准备索引...' });

                // 调用索引 API
                const result = await apiService.indexProject(projectName, projectPath);

                progress.report({ increment: 50, message: '索引完成' });

                // 显示结果
                const stats = result.stats || {};
                const message = `索引完成!\n` +
                    `文件数：${stats.total_files || 0}\n` +
                    `代码块：${stats.total_chunks || 0}\n` +
                    `符号数：${stats.total_symbols || 0}`;

                vscode.window.showInformationMessage(message);

                // 刷新视图
                if (codeMapView) {
                    codeMapView.webview.postMessage({ command: 'refresh' });
                }
            } catch (error: any) {
                vscode.window.showErrorMessage(`索引失败：${error.message}`);
            }
        }
    );
}

/**
 * 解释选中的代码
 */
async function explainCode() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('请先选择代码');
        return;
    }

    const selection = editor.selection;
    const selectedText = editor.document.getText(selection);

    if (!selectedText) {
        vscode.window.showErrorMessage('请先选择代码');
        return;
    }

    const filePath = editor.document.fileName;

    vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: '正在解释代码...',
            cancellable: false
        },
        async (progress) => {
            try {
                progress.report({ increment: 0, message: '分析中...' });

                // 调用解释 API
                const result = await apiService.explainCode(
                    selectedText,
                    filePath,
                    editor.document.languageId
                );

                progress.report({ increment: 80, message: '生成解释...' });

                // 显示结果
                const explanation = result.explanation || '无法解释代码';
                const citations = result.citations || [];

                const panel = vscode.window.createWebviewPanel(
                    'codeExplanation',
                    '代码解释',
                    vscode.ViewColumn.Beside,
                    { enableScripts: true }
                );

                panel.webview.html = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: var(--vscode-font-family); padding: 20px; }
        .explanation { white-space: pre-wrap; margin-bottom: 20px; }
        .citation { background: var(--vscode-badge-background);
                    color: var(--vscode-badge-foreground);
                    padding: 2px 6px; border-radius: 3px; font-size: 12px; }
        .confidence { margin-top: 10px; font-weight: bold; }
        .high { color: green; }
        .medium { color: orange; }
        .low { color: red; }
    </style>
</head>
<body>
    <h2>代码解释</h2>
    <div class="explanation">${explanation}</div>
    <h3>引用 (${citations.length})</h3>
    <ul>
        ${citations.map((c: any) => `
            <li>
                <span class="citation">${c.file}:${c.line}</span>
                ${c.content ? `<pre>${c.content}</pre>` : ''}
            </li>
        `).join('')}
    </ul>
    ${result.validation ? `
        <div class="confidence ${
            result.validation.confidence > 0.8 ? 'high' :
            result.validation.confidence > 0.5 ? 'medium' : 'low'
        }">
            置信度：${(result.validation.confidence * 100).toFixed(1)}%
        </div>
    ` : ''}
</body>
</html>
                `;
            } catch (error: any) {
                vscode.window.showErrorMessage(`解释失败：${error.message}`);
            }
        }
    );
}

/**
 * 查找阅读路径
 */
async function findReadingPath() {
    const task = await vscode.window.showInputBox({
        prompt: '请输入任务描述',
        placeHolder: '例如：添加一个新的 API 端点'
    });

    if (!task) {
        return;
    }

    vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: '正在生成阅读路径...',
            cancellable: false
        },
        async (progress) => {
            try {
                progress.report({ increment: 0, message: '分析任务...' });

                const result = await apiService.getTaskGuide(task);

                progress.report({ increment: 80, message: '生成路径...' });

                // 显示结果
                const readingOrder = result.reading_order || [];
                const citations = result.citations || [];

                const panel = vscode.window.createWebviewPanel(
                    'taskGuide',
                    '任务引导阅读路径',
                    vscode.ViewColumn.Two,
                    { enableScripts: true }
                );

                panel.webview.html = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: var(--vscode-font-family); padding: 20px; }
        .task { font-size: 18px; font-weight: bold; margin-bottom: 20px; }
        .step { margin: 10px 0; padding: 10px;
                border-left: 3px solid var(--vscode-progressBar-background); }
        .file { color: var(--vscode-textLink-foreground); cursor: pointer; }
        .reason { color: var(--vscode-descriptionForeground); font-size: 14px; }
    </style>
</head>
<body>
    <h2>任务：${task}</h2>
    <h3>建议阅读顺序</h3>
    <div>
        ${readingOrder.map((item: any, i: number) => `
            <div class="step">
                <strong>${i + 1}. ${item.file}</strong><br>
                <span class="reason">${item.reason}</span>
            </div>
        `).join('')}
    </div>
    <h3>引用文件 (${citations.length})</h3>
    <ul>
        ${citations.map((c: any) => `<li>${c}</li>`).join('')}
    </ul>
</body>
</html>
                `;
            } catch (error: any) {
                vscode.window.showErrorMessage(`生成阅读路径失败：${error.message}`);
            }
        }
    );
}

/**
 * 分析依赖关系
 */
async function analyzeDependency() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('请先打开一个文件');
        return;
    }

    const filePath = editor.document.fileName;

    vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: '正在分析依赖...',
            cancellable: false
        },
        async (progress) => {
            try {
                progress.report({ increment: 0, message: '解析依赖...' });

                const result = await apiService.getDependencyGraph(filePath);

                progress.report({ increment: 80, message: '生成图表...' });

                // 显示结果
                const nodes = result.nodes || {};
                const edges = result.edges || [];

                const panel = vscode.window.createWebviewPanel(
                    'dependencyGraph',
                    '依赖关系图',
                    vscode.ViewColumn.Beside,
                    { enableScripts: true }
                );

                const nodeCount = Object.keys(nodes).length;
                const edgeCount = edges.length;
                const cycleCount = result.cycle_count || 0;

                panel.webview.html = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: var(--vscode-font-family); padding: 20px; }
        .stats { display: flex; gap: 20px; margin-bottom: 20px; }
        .stat { padding: 10px; background: var(--vscode-badge-background);
                color: var(--vscode-badge-foreground); border-radius: 5px; }
        .module { margin: 5px 0; padding: 5px;
                   border-left: 3px solid var(--vscode-progressBar-background); }
        .core { border-left-color: red; }
        .entry { border-left-color: green; }
    </style>
</head>
<body>
    <h2>依赖关系分析</h2>
    <div class="stats">
        <div class="stat">模块数：${nodeCount}</div>
        <div class="stat">依赖边：${edgeCount}</div>
        <div class="stat">循环依赖：${cycleCount}</div>
    </div>
    <h3>核心模块 (被依赖最多)</h3>
    <div>
        ${Object.values(nodes as any[])
            .sort((a, b) => b.in_degree - a.in_degree)
            .slice(0, 10)
            .map((n: any) => `
                <div class="module ${n.node_type === 'core_module' ? 'core' : ''}">
                    ${n.module_name} (入度：${n.in_degree}, 出度：${n.out_degree})
                </div>
            `).join('')}
    </div>
    ${cycleCount > 0 ? `
        <h3>⚠️ 循环依赖警告</h3>
        <p>检测到 ${cycleCount} 个循环依赖，建议重构</p>
    ` : ''}
</body>
</html>
                `;
            } catch (error: any) {
                vscode.window.showErrorMessage(`依赖分析失败：${error.message}`);
            }
        }
    );
}

/**
 * 显示符号引用
 */
async function showSymbolReferences() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('请先打开一个文件');
        return;
    }

    const selection = editor.selection;
    const selectedText = editor.document.getText(selection);

    if (!selectedText) {
        vscode.window.showErrorMessage('请先选择一个符号');
        return;
    }

    vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: `正在查找 "${selectedText}" 的引用...`,
            cancellable: false
        },
        async (progress) => {
            try {
                progress.report({ increment: 0, message: '搜索中...' });

                const result = await apiService.findSymbolReferences(
                    selectedText,
                    editor.document.fileName
                );

                progress.report({ increment: 80, message: '整理结果...' });

                // 显示结果
                const references = result.references || [];

                if (references.length === 0) {
                    vscode.window.showInformationMessage('未找到引用');
                    return;
                }

                // 在侧边栏显示结果
                const panel = vscode.window.createWebviewPanel(
                    'symbolReferences',
                    `符号引用：${selectedText}`,
                    vscode.ViewColumn.Three,
                    { enableScripts: true }
                );

                panel.webview.html = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: var(--vscode-font-family); padding: 20px; }
        .ref { margin: 10px 0; padding: 10px;
               border-left: 3px solid var(--vscode-progressBar-background); }
        .file { color: var(--vscode-textLink-foreground); cursor: pointer; }
        .line { color: var(--vscode-descriptionForeground); font-size: 12px; }
        .code { background: var(--vscode-textBlockQuote-background);
                padding: 5px; margin: 5px 0; font-family: monospace; }
    </style>
</head>
<body>
    <h2>"${selectedText}" 的引用 (${references.length})</h2>
    <div>
        ${references.map((ref: any) => `
            <div class="ref">
                <div class="file">${ref.file}</div>
                <div class="line">第 ${ref.line} 行</div>
                <div class="code">${ref.context}</div>
            </div>
        `).join('')}
    </div>
</body>
</html>
                `;
            } catch (error: any) {
                vscode.window.showErrorMessage(`查找引用失败：${error.message}`);
            }
        }
    );
}

/**
 * 插件停用
 */
export function deactivate() {
    console.log('AI Code Understanding 插件已停用');
}
