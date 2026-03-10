LLM 自动化答案评估与对比工具 (Auto-Eval Agent)
1. 项目概述
开发一个基于 Python + Streamlit 的 Web 端工具。该工具用于批量评估数据质量。用户上传 CSV/Excel 文件，指定“标准答案列”和“待评估列”，工具通过多线程调用 LLM 对每行数据进行一致性/准确性判断。
核心特性：LLM 以 JSON 格式返回结构化数据（结果+原因），程序解析后分别存储，并自动计算准确率。

2. 技术栈推荐
- 前端/框架: Streamlit
- 数据处理: Pandas, Openpyxl
- 并发/网络: concurrent.futures.ThreadPoolExecutor, tenacity (重试机制)
- 数据存储: SQLite (历史记录)
- 模型交互: openai (官方库) 或 requests (通用 API 调用)
  
3. 功能需求详细说明

3.1 侧边栏：全局配置 (System Configuration)
侧边栏用于配置 LLM 连接参数，配置需支持本地持久化保存。
- API Base URL: 字符串输入 (例如 https://api.deepseek.com/v1)
- API Key: 密码形式输入
- Model Name: 字符串输入 (例如 gpt-4o, deepseek-chat)
- Temperature: 滑动条 (0.0 - 1.0，默认为 0，以保证评估的一致性)
- Max Tokens: 数字 (默认 512，防止输出截断)
- 并发线程数: 数字 (默认 5，最大 20)
  
3.2 主界面：任务配置 (Task Setup)

步骤 1: 数据加载
- 支持文件格式：.csv, .xlsx。
- Excel 多 Sheet 处理：上传 .xlsx 后，自动读取所有 Sheet 名称，提供下拉框供用户选择要处理的 Sheet。
- 数据预览：展示所选 Sheet 的前 5 行数据。
  
步骤 2: 字段映射 (Column Mapping)
提供两个明确的下拉框：
1. 选择标准答案列 (Reference Column)：作为真值基准。
2. 选择待评估列 (Evaluation Column)：作为需要 LLM 评判的内容。
3. 结果输出列名设置：
  - Result 列名 (默认: eval_result)
  - Reason 列名 (默认: eval_reason)
    
步骤 3: 提示词模板 (Prompt Template)
- 提供默认模板，支持编辑。
- 必须包含的变量：{reference} (标准答案) 和 {candidate} (待评估内容)。
- 强制约束：系统需在 Prompt 后台强制追加“请务必以 JSON 格式输出”的系统指令，确保返回格式如下：
{
    "result": "正确",  // 或 "错误"
    "reason": "简短的判定理由"
}
  
3.3 核心处理逻辑 (Core Logic)

1. 执行流程
1. 用户点击“开始评估”。
2. 程序初始化 result 和 reason 空列。
3. 使用线程池并发处理每一行数据。
4. 构建 Prompt：将该行的“标准答案”和“待评估内容”填入模板。
  
2. LLM 交互与解析 (关键逻辑)
- 调用：发送请求。
- 解析：
  - 获取 LLM 返回的文本。
  - JSON 提取：使用正则表达式或 JSON parser 提取返回内容中的 JSON 对象。
  - 容错处理：如果 LLM 返回的不是合法 JSON，记录 Result 为 "Error"，Reason 为 "JSON 解析失败"。
- 回填：将解析出的 result 填入结果列，reason 填入原因列。
  
3. 准确率统计
- 任务结束后，遍历 result 列。
- 逻辑：
  - Correct Count = 值为 "正确" (忽略大小写) 的行数。
  - Error Count = 值为 "错误" (忽略大小写) 的行数。
  - Total Valid = Correct Count + Error Count。
  - 准确率 (Accuracy) = Correct Count / Total Valid。
  - (注：解析失败或 API 报错的行不计入分母，或者在统计时单独列出)
    
4. 结果存储
- 将统计结果（准确率、正确数、错误数）追加写入到 DataFrame 的最后几行，或者在 Excel 中新建一个 summary sheet。
- 生成最终 Excel 文件供下载。
  
3.4 历史记录 (Audit Logs)
在页面底部或独立 Tab 页展示。
- 记录时机：任务完成后写入 SQLite。
- Schema：
  - Time: 执行时间
  - File: 文件名
  - Columns: "Ref: [列A] vs Eval: [列B]"
  - Model: 模型名
  - Records: 总记录数
  - Accuracy: 最终准确率 (百分比)
  - Prompt: 当时使用的 Prompt 快照
    
4. 界面交互示意

+---------------------+---------------------------------------------------------+
| [侧边栏配置]        |                                                         |
| Base URL: [...]     |  Step 1: 上传文件                                       |
| API Key: [***]      |  [ 拖拽上传 Excel/CSV ]                                 |
| Model: [gpt-4]      |  选择 Sheet: [ Sheet1 v ]                               |
|                     |                                                         |
| [保存配置]          |  Step 2: 映射列                                         |
|                     |  [标准答案列 (基准) v]  VS  [待评估列 (候选) v]         |
|                     |                                                         |
|                     |  Step 3: 提示词设置                                     |
|                     |  [编辑器: 请判断 {candidate} 是否符合 {reference}...]   |
|                     |  *系统将强制要求 JSON 输出*                             |
|                     |                                                         |
|                     |  [ ▶ 开始评估任务 ]                                     |
|                     |                                                         |
|                     |  ----------------------------------------------------   |
|                     |  进度: [|||||||||||| 60% ]  (正在处理第 60/100 条)    |
|                     |  ----------------------------------------------------   |
|                     |                                                         |
|                     |  [评估完成!]                                            |
|                     |  统计结果: 准确率 85.0% (正确: 85, 错误: 15)            |
|                     |  [ 📥 下载评估结果.xlsx ]                               |
|                     |                                                         |
|                     |  [历史记录表格...]                                      |
+---------------------+---------------------------------------------------------+
