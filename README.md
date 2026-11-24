# 📚 Momo 收藏工具箱


公开 GitHub 收藏索引。每天自动收集 Star，为收藏生成中文简介、搜索关键词和使用场景，你的电脑可以关机。


## 从这里开始


- [待整理清单](INBOX.md)：尚未写个人笔记的收藏。
- [分类索引](INDEX.md)：按用途浏览；初始分类是关键词规则建议，不是 AI 总结。
- [在线搜索](https://breezymomo.github.io/momo-toolbox/)：按用途浏览收藏，点开一条可读完整简介、使用场景和笔记。搜索会高亮命中的原文，手机上的分类和收藏范围在“筛选”里。
- [离线搜索文件](search.html)：仍可 Download raw file 后用浏览器打开。
- [立即同步 / 查看结果](../../actions/workflows/sync.yml)：点击 **Run workflow**。失败可在运行日志查看原因。
- [个人笔记](notes.json)：你自己的中文说明、使用场景和分类，自动任务不会覆盖。


## 同步范围与时间


每天北京时间 **09:23**（UTC 01:23）同步一次。GitHub 定时任务可能延迟，不保证准点。也可随时手动运行。
第一版读取 `BreezyMomo` **公开可访问的 Star 项目**，不会读取私有仓库收藏。若 GitHub 个人资料被设为私有，可能需要另行配置有适当权限的认证，当前不创建个人令牌。
同步脚本把公开仓库名、README 摘录、GitHub 原简介和 topics 发到 `https://relay.tuyoo.com/v1/chat/completions`。由 `gpt-6.2-sol` 在同一次请求中给出一句中文简介、3～5 个具体关键词和一个有资料依据的使用场景。每条最多取 6,000 个 README 字符，首次输出上限为 512 tokens，格式错误等情况重试时上限为 1,024 tokens。在线和离线搜索均支持关键词、技术名和场景中的文字，多个搜索词可用空格组合。

每个字段优先展示 `notes.json` 中的手写内容。AI 结果按仓库 ID 保存在 `stars.json` 的 `ai_summary`、`ai_tags` 和 `ai_use_when`，已保存字段在补齐其他字段时保留。三项齐全后直接复用，改名或更新 README 也不会重新调用模型。取消 Star 的项目保留历史记录，搜索选择“全部”可找到。

每日同步最多处理 10 项。需要一次性补齐当前收藏时，在 Actions 的 **Run workflow** 勾选 **Fill missing descriptions, keywords and use cases for all current stars**。这个选项只处理缺少字段的当前收藏，并允许已用完重试次数的条目再尝试一次。

## 配置 AI 密钥

在仓库的 **Settings → Secrets and variables → Actions → New repository secret** 添加名为 `AI_API_KEY` 的密钥，值填写中转服务提供的 Key。密钥仅注入只读同步任务中的 API 调用步骤。请求正文只包含生成指令和公开的仓库资料，个人笔记仅用于本地合并显示。提交任务在另一台运行机上校验简介并生成页面。

缺少密钥或服务暂不可用时，收藏照常发布，缺少的字段留到后续同步。单个项目遇到超时或返回内容不合格时，累计尝试最多三次。没有 README 时使用 GitHub 公开简介和 topics；三者都缺失时跳过生成。


## 如何整理


在 GitHub 打开 notes.json，点击编辑，按仓库完整名称或 stars.json 中的数字 id 增加条目。推荐数字 id，项目改名时笔记仍能关联。示例（示意，不是你的真实收藏）：


```json
{
  "123456": {
    "summary": "一句话说明这是什么",
    "use_when": "遇到什么问题时可以用它",
    "categories": ["游戏开发"],
    "tags": ["Unity", "材质"],
    "note": "我的使用体验和注意事项",
    "reviewed": true
  }
}
```


保存后自动刷新索引。`reviewed: true` 表示已整理；未填写时保留待整理状态。分类可以自定义，一个项目可属于多类。JSON 语法错误会让任务失败，不会偷偷覆盖你的笔记。不要在笔记中写密码或访问令牌。


## 文件分工


| 文件 | 用途 | 能否手改 |
|---|---|---|
| notes.json | 人工笔记和分类 | 可以，任务只读 |
| config.json | GitHub 用户名 | 可以 |
| stars.json | 自动同步元数据及历史 | 不建议 |
| INBOX.md / INDEX.md / search.html | 自动生成视图 | 不要，任务会重建 |
| sync_stars.py / summarize_stars.py / test_sync.py | 同步、README 简介和测试 | 开发时修改 |


## 本地使用


基础同步和索引渲染只需 Python 3.11+：


```sh
python -m unittest -v
python sync_stars.py
python sync_stars.py --render-only
```

本地生成中文简介时，通过环境变量提供 `AI_API_KEY`，运行 `python summarize_stars.py`，然后运行 `python sync_stars.py --render-only`。运行 `python summarize_stars.py --check` 可查看有无待生成条目。


收藏抓取失败会使 Actions 标红，`stars.json` 中的 `last_sync` 保留上次成功时间。GitHub Actions 使用仓库自带的临时 GITHUB_TOKEN，抓取和生成简介的任务拥有仓库只读权限，提交任务拥有仓库内容写权限，Pages 部署任务仅拥有 Pages 与临时身份令牌权限。并发任务串行执行，推送若与人工编辑冲突则停止，绝不强制推送。


本仓库和 GitHub Pages 均已公开。这里只放愿意公开的资料，notes.json 中新增的笔记也会公开，请勿填写私人资料、密钥或敏感链接。Pages 仅部署 search.html 的副本 index.html，不打包整个仓库。

同步、生成和部署在同一工作流内完成，不依赖机器人提交触发第二条工作流。公开仓库长期无活动时 GitHub 可能停用定时任务，请查看 Actions 并按提示重新启用。Actions 受 GitHub 账户额度限制，不设置付费预算。Chrome 收藏导入和语义搜索留作后续，不包含在本版。

