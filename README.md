# LLM 自动化答案评估与对比工具 (Auto-Eval Agent)

基于 Streamlit 的 Web 端工具，用于批量评估数据质量。通过 LLM 对每行数据进行一致性/准确性判断。

## 功能特性

- 📊 支持 CSV/Excel 文件上传
- 🔄 多线程并发处理，实时进度显示
- 🤖 LLM 自动评估，JSON 格式返回结果
- 📈 自动计算准确率统计
- 📜 历史记录管理（SQLite）
- 💾 结果文件下载

## ⚠️ 重要：Python 版本要求

**如果使用 Python 3.13，可能会遇到编码问题！**

Python 3.13 太新，numpy 等包可能没有预编译的 wheel 包，pip 会自动回退到源码构建，而构建过程在中文路径下会失败。

### 推荐方案

1. **使用 Python 3.11 或 3.12**（推荐）
   - 运行：`使用Python311.bat` 或 `使用Python312.bat`
   - 这会创建新的虚拟环境，使用有完整预编译包支持的 Python 版本

2. **检查当前 Python 版本**
   - 运行：`检查Python版本.bat`
   - 查看系统中有哪些 Python 版本可用

3. **如果必须使用 Python 3.13**
   - 将项目移动到纯英文路径（如 `D:\Projects\AutoEvalTool\`）
   - 或参考 `解决编码问题.md` 和 `解决方案说明.md`

## 安装依赖

```bash
pip install -r requirements.txt
```

**注意：** 如果遇到 `UnicodeDecodeError`，请先运行 `检查Python版本.bat` 诊断问题。

## 运行应用

**方法1：使用 streamlit 命令（推荐）**
```bash
streamlit run app.py
```

**方法2：如果遇到 PATH 问题，使用 Python 模块方式**
```bash
python -m streamlit run app.py
```

> **注意**：如果看到警告说 streamlit.exe 不在 PATH 中，可以使用方法2（`python -m streamlit`），这是最可靠的方式。

## 首次使用：配置 API Key

1. 复制配置模板：
   ```bash
   copy config\summary_generation.cfg.example config\summary_generation.cfg
   ```
2. 编辑 `config/summary_generation.cfg`，将 `YOUR_API_KEY_HERE` 替换为真实的 API Key
3. **重要**：`summary_generation.cfg` 已加入 .gitignore，不会提交到 Git

应用将在浏览器中自动打开，默认地址：http://localhost:8501

## ⚠️ 浏览器要求

**重要：** 本工具需要现代浏览器支持（ES2022）。

### 支持的浏览器版本：
- **Chrome/Edge**: 93+ （推荐最新版）
- **Firefox**: 92+
- **Safari**: 15.4+

如果遇到 `Object.hasOwn is not a function` 错误，说明浏览器版本过旧，请升级浏览器。

详细说明请查看：[浏览器兼容性说明.md](浏览器兼容性说明.md)

## 使用步骤

1. **配置 LLM 参数**（侧边栏）
   - 填写 API Base URL、API Key、Model Name
   - 设置 Temperature、Max Tokens、并发线程数
   - 点击"保存配置"

2. **上传数据文件**
   - 支持 `.csv` 和 `.xlsx` 格式
   - Excel 文件如有多个 Sheet，需选择要处理的 Sheet

3. **字段映射**
   - 选择标准答案列（Reference Column）
   - 选择待评估列（Evaluation Column）
   - 设置结果列名（可选，默认：eval_result、eval_reason）

4. **设置提示词模板**
   - 编辑提示词模板（必须包含 `{reference}` 和 `{candidate}` 变量）
   - 系统会自动追加 JSON 格式要求

5. **开始评估**
   - 点击"开始评估任务"按钮
   - 等待处理完成（可实时查看进度）

6. **查看结果**
   - 查看统计结果（准确率、正确数、错误数等）
   - 查看详细评估结果表格
   - 下载评估结果文件

## 文件结构

```
DemoV3/
├── app.py                  # Streamlit 主应用
├── llm_service.py          # LLM 调用服务
├── utils.py                # 工具函数（JSON解析、准确率计算）
├── database.py             # SQLite 历史记录管理
├── requirements.txt        # 依赖包列表
├── README.md               # 说明文档
└── eval_history.db         # SQLite 数据库（自动创建）
```

## 技术实现

- **JSON 解析鲁棒性**：使用正则表达式从返回文本中提取 JSON 对象，支持 markdown 代码块包裹的情况
- **并发控制**：使用 `ThreadPoolExecutor` 进行多线程处理，通过 `st.progress` 实时更新进度
- **准确率计算**：Accuracy = Correct_Rows / (Correct_Rows + Incorrect_Rows)，不区分大小写判断"正确"/"错误"
- **文件处理**：不修改原文件，生成新的 BytesIO 对象供下载

## 注意事项

- 确保 LLM API 配置正确，具有足够的调用额度
- 并发线程数建议设置为 5-10，过高可能导致 API 限流
- 提示词模板必须包含 `{reference}` 和 `{candidate}` 变量
- 系统会自动在提示词后追加 JSON 格式要求

## 同步到 GitHub

### 安全说明

以下文件已加入 `.gitignore`，**不会**提交到 Git：
- `config/summary_generation.cfg` - 包含 API Key，使用模板 `config/summary_generation.cfg.example`
- `process.log` - 可能包含请求/响应日志
- `eval_history.db` - 用户数据
- `venv/`、`build/`、`dist/` - 构建产物

### 同步步骤

```bash
# 1. 初始化 Git（若尚未初始化）
git init

# 2. 添加远程仓库
git remote add origin https://github.com/你的用户名/仓库名.git

# 3. 添加文件并提交
git add .
git commit -m "feat: LLM 自动化答案评估与对比工具"

# 4. 推送到 GitHub
git push -u origin main
```

### 验证

推送前可运行 `git status` 确认 `config/summary_generation.cfg` 未被追踪。

### 若 config 曾被提交过

若 `config/summary_generation.cfg` 曾包含真实 API Key 且已提交，需先停止追踪：
```bash
git rm --cached config/summary_generation.cfg
git commit -m "chore: 停止追踪敏感配置文件"
```
然后推送。**注意**：历史提交中可能仍包含 Key，建议更换 API Key 或使用新仓库。

## 参考

- LLM 调用和鉴权逻辑参考了 `batch_summary_generator.py` 中的实现
- 支持 HMAC-SHA1 鉴权（可在 `llm_service.py` 中扩展）
