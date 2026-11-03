# agent_test：AgentBench-Lite

这是一个关于 Agent 评测的从 0 到 1 搭建的项目，面向 Agent 测试／评测实习作品。第一阶段先把业务、数据和成功标准写清楚，后续再接入大模型和自动化评测。

当前版本：`v0.2`（订单工具阶段，业务规则仍为 `v0.1`）；场景：模拟电商售后；全部用户、订单和规则均为教学用虚构材料。

## 运行订单工具

在仓库根目录使用 Python 3.10 或以上版本运行，无需模型 API 或第三方运行依赖：

```powershell
python -m agent_bench demo
```

该演示在同一个环境中完成查询、取消、再次查询，以及重复取消和权限拒绝。所有变更仅存在本次运行的内存中，原始订单 JSON 不会改变。

单独查询或取消：

```powershell
python -m agent_bench get-order O1001
python -m agent_bench cancel-order O1001
```

每条独立命令都会重新加载初始数据；验证“取消后再查询”请使用 `demo` 或在 Python 中复用同一个 `OrderTools` 实例。详细解释见 [第二次练习](docs/second_exercise.md)。

## 运行测试

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

如果当前 Python 环境已安装 pytest，可直接执行第二条命令。测试验证业务工具行为，不代表已完成自然语言 Agent 评测。

## 先看什么

1. 阅读 [售后业务规则](docs/business_rules.md)，理解哪些行为允许、哪些必须拒绝或追问。
2. 查看 [5 个虚构订单](data/orders.json)，把订单状态与规则对应起来。
3. 打开 [10 条测试用例速览](docs/test_cases.md)，练习判断每条任务的正确行为。
4. 按 [第一次练习](docs/first_exercise.md) 手动执行前几条用例。
5. 对照 [机器可读测试集](data/test_cases.json)，理解输入与评分标准如何保存。

这一阶段不需要 API Key，也不需要付费调用模型。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `docs/business_rules.md` | 模拟售后需求，带规则编号 |
| `data/orders.json` | 固定时钟、当前用户、5 个订单和空操作记录 |
| `docs/test_cases.md` | 10 条用例的中文速览和逐项验收标准 |
| `data/test_cases.json` | 后续批量运行器使用的用例与评分条件 |
| `docs/tool_contracts.md` | 下一阶段实现模拟工具时遵守的输入、输出与权限约定 |
| `docs/first_exercise.md` | 约 60–90 分钟的第一次练习与记录模板 |
| `docs/development_workflow.md` | 在本仓库开发、提交和同步 GitHub 的入门说明 |
| `agent_bench/tools.py` | 查询、取消、独立运行环境与评测快照 |
| `agent_bench/__main__.py` | 命令行操作和完整演示 |
| `tests/test_order_tools.py` | 业务规则、权限、重复操作和状态隔离测试 |
| `docs/second_exercise.md` | 实际运行工具、查看状态变化与测试结果 |

## 从哪里开发

本 README 所在目录就是 Git 仓库根目录。后续代码、数据和报告均放在这个仓库中，执行 Git 命令前先进入该目录。

开始前可以运行 `git status` 检查当前分支和文件变化。提交与上传流程见 [开发与上传说明](docs/development_workflow.md)。

## 第一阶段完成标准

- 能解释“回复成功”和“数据库状态正确”的区别。
- 能判断 10 条用例的预期结果，并指出对应规则。
- 能解释为什么每条用例开始前要重置订单与操作记录。
- 能指出一条只检查回复关键词会误判的用例。
- 能自己补写一条用例，写清输入、初始条件、目标状态和禁止行为。

## 当前边界

当前已实现 `get_order`、`cancel_order` 两个模拟业务工具，并覆盖 TC01、TC02、TC03、TC07、TC09 涉及的工具层需求。尚未接入大模型，也未实现退款工具、批量 Agent 运行器和端到端自动评分器。JSON 中的评分字段仍是后续实现约定。

这 10 条用例是公开的练习／开发集。后续扩展时，另建保留测试集，避免把反复调试过的样例当作独立测试结果。

下一阶段可以把两个工具接入最小模型调用循环，再检查 Agent 能否根据自然语言选择正确工具、填写参数并如实回复。
