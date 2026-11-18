# 📚 Momo 收藏工具箱


公开 GitHub 收藏索引。你继续点 Star，这里每天自动收集，不需要开启电脑，也不调用 AI 模型。


## 从这里开始


- [待整理清单](INBOX.md)：尚未写个人笔记的收藏。
- [分类索引](INDEX.md)：按用途浏览；初始分类是关键词规则建议，不是 AI 总结。
- [在线搜索](https://breezymomo.github.io/momo-toolbox/)：直接打开，搜索关键词、筛选分类和待整理状态。每日同步后自动更新，无需下载。
- [离线搜索文件](search.html)：仍可 Download raw file 后用浏览器打开。
- [立即同步 / 查看结果](../../actions/workflows/sync.yml)：点击 **Run workflow**。失败可在运行日志查看原因。
- [个人笔记](notes.json)：你自己的中文说明、使用场景和分类，自动任务不会覆盖。


## 同步范围与时间


每天北京时间 **09:23**（UTC 01:23）同步一次。GitHub 定时任务可能延迟，不保证准点。也可随时手动运行。
第一版读取 `BreezyMomo` **公开可访问的 Star 项目**，不会读取私有仓库收藏。若 GitHub 个人资料被设为私有，可能需要另行配置有适当权限的认证，当前不创建个人令牌。
只保存项目元数据，不下载代码，不运行收藏项目的代码。取消 Star、项目删除或不再可见时保留历史记录和笔记，但从当前收藏隐藏；搜索选择“全部”可找到。


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
| sync_stars.py / test_sync.py | 同步实现和测试 | 开发时修改 |


## 本地使用


Python 3.11+，无需额外依赖：


```sh
python -m unittest -v
python sync_stars.py
python sync_stars.py --render-only
```


同步失败会使 Actions 标红，`stars.json` 中的 `last_sync` 保留上次成功时间。GitHub Actions 使用仓库自带的临时 GITHUB_TOKEN，同步任务只给本仓库内容写权限，发布任务仅给 Pages 与临时身份令牌权限，不保存个人密钥。并发任务串行执行，推送若与人工编辑冲突则停止，绝不强制推送。


本仓库和 GitHub Pages 均已公开。这里只放愿意公开的资料，notes.json 中新增的笔记也会公开，请勿填写私人资料、密钥或敏感链接。Pages 仅部署 search.html 的副本 index.html，不打包整个仓库。

同步、生成和部署在同一工作流内完成，不依赖机器人提交触发第二条工作流。公开仓库长期无活动时 GitHub 可能停用定时任务，请查看 Actions 并按提示重新启用。Actions 受 GitHub 账户额度限制，不设置付费预算。Chrome 收藏导入、AI 中文总结和语义搜索留作后续，不包含在本版。

