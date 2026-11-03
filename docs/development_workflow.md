# 在本仓库开发和上传 GitHub

远程仓库：<https://github.com/lixiaoming880/agent_test>

## 打开正确目录

在编辑器中打开 `agent_test` 文件夹。当前电脑上的位置是：

```powershell
Set-Location -LiteralPath 'D:\gpt_project\agent_bench_project(0-1)\agent_test'
git status
```

`git status` 应显示当前分支为 `main`，并列出文件变化。不要在外层文件夹执行提交，也不需要再次 `git init` 或克隆仓库。

## 一次小修改的流程

先修改文件，再检查差异，明确选择要提交的文件。例如修改业务规则：

```powershell
git status
git diff -- docs/business_rules.md
git add docs/business_rules.md
git commit -m "docs: clarify refund eligibility rules"
git push origin main
```

`commit` 把选中的变化记入本地历史，`push` 才把提交上传到 GitHub。提交说明写清本次做了什么，尽量一次提交只处理一个主题。

首次上传可能需要 GitHub 登录，请使用 Git 提供的登录流程。不要把账号密码、访问令牌或 API Key 写进仓库或聊天。

如果上传提示远程出现新提交，先查看并同步远程变化；不要用强制推送覆盖远程历史。

## 哪些文件该提交

- 提交：源代码、业务规则、虚构测试数据、脱敏后的实验报告、依赖说明。
- `.gitignore` 已忽略：本地 `.env`、Python 虚拟环境、缓存和个人编辑器配置。
- `.env.example` 可以提交，但只能填示例变量名和占位值。
- 忽略规则不等于内容检查，提交前仍需确认文件中没有真实密钥、个人订单或用户隐私。

## 下一次开发的范围

先实现订单查询和取消两个模拟工具，使用现有测试数据检查：

1. TC01：能读取本人订单状态。
2. TC02：取消后状态和操作记录都正确。
3. TC03：已发货不能取消。
4. TC07：查询他人订单不泄露信息。
5. TC09：不存在的订单不编造结果。

这一步完成后，再接入大模型。当前版本只包含学习材料和数据，尚未实现上述工具。
