# 第二次练习：运行订单查询与取消工具

目标：理解一个工具怎样把业务规则变成实际操作，以及怎样用状态与操作记录验证行为。预计 45–60 分钟，无需模型 API Key。

## 1. 运行演示

在 `agent_test` 仓库根目录执行：

```powershell
python -m agent_bench demo
```

按顺序查看 `steps` 中的结果：

1. 查询 O1001，状态为 `pending_payment`（待付款）。
2. 取消 O1001，返回 `cancelled`。
3. 再查同一订单，状态已经改变。
4. 重复取消返回 `ORDER_NOT_CANCELLABLE`，不再追加记录。
5. 取消已发货的 O1002 被拒绝。
6. 查他人订单 O2001 与不存在订单 O9999，返回内容相同。

最后的 `business_actions` 应只有一条，`refund_request_count` 应为 0。操作时间固定为 `2026-11-03T10:00:00+08:00`；每次生成的 `action_id` 可以不同。

这是工具演示，不是自然语言 Agent；工具调用在演示代码中写好，模型还没有参与选择工具。

## 2. 单独执行工具

```powershell
python -m agent_bench get-order O1001
python -m agent_bench cancel-order O1001
python -m agent_bench cancel-order O1002
```

前两条返回 `ok: true`，第三条返回 `ok: false`、错误码 `ORDER_NOT_CANCELLABLE`。拒绝操作是业务规则的正常结果。

查询／取消命令的退出码：成功为 0，业务拒绝或无效订单号为 1；演示中的拒绝操作是预期结果，所以整个 `demo` 命令返回 0。

每次启动一条新命令都会从原始 JSON 创建独立环境，因此在单独取消命令结束后，再运行新的查询命令仍看到初始的“待付款”。这正是测试隔离的约定，不是取消工具失效。要观察连续变化，请使用 `demo`，或复用下节的同一个实例。

## 3. 在 Python 中复用环境

在仓库根目录输入 `python`，进入交互环境后依次执行：

```python
from agent_bench import OrderTools

tools = OrderTools.from_fixture()
tools.get_order("O1001")
tools.cancel_order("O1001")
tools.get_order("O1001")

state = tools.snapshot()
state["business_actions"]
state["refund_requests"]
```

比较取消前后 `get_order` 的结果；检查取消记录的订单号、操作人、操作时间是否正确。退出交互环境可输入 `exit()`。

`snapshot()` 用于测试人员读取最终状态，不能作为模型可调用工具或直接放入模型提示词。它包含其他用户的订单。

## 4. 运行测试并阅读断言

如果还没有 pytest，先安装开发依赖：

```powershell
python -m pip install -r requirements-dev.txt
```

然后执行：

```powershell
python -m pytest -q
```

打开 `tests/test_order_tools.py`，分别找到这些检查：

- 查询结果与初始订单一致，而且没有业务写入。
- 取消后只改变指定订单状态，并新增一条正确操作记录。
- 他人订单和不存在订单返回一致，不泄露商品、金额或状态。
- 重复取消不会新增第二条记录。
- 修改返回值、输入数据或快照，不会反向改变工具的内部状态。
- 新建实例仍从初始状态开始，操作时间支持可信环境覆盖。

测试中的 `assert` 表示“这个条件必须成立”。先尝试解释一条状态检查和一条权限检查，再追踪它们调用了什么工具。

## 5. 自己补一个场景

在 Python 交互环境尝试：

```python
tools = OrderTools.from_fixture()
before = tools.snapshot()
result = tools.cancel_order("O2001")
after = tools.snapshot()
result
before == after
```

正确结果：无权访问，且 `before == after` 为 `True`。结合 TC07 思考：如果工具先返回“已签收不能取消”，即使没有改数据，为什么仍然泄露了信息？

完成后，下一阶段才让模型根据用户的话选择这两个工具，并检查模型的工具参数、过程和最终回复。
