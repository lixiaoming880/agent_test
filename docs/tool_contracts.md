# 模拟工具约定与实现状态

`get_order` 和 `cancel_order` 已在 `agent_bench/tools.py` 实现；退款相关工具仍是后续设计约定。业务规则版本为 v0.1。

## 共用约定

- 当前用户、固定时钟与会话历史由运行环境提供，不能让模型通过参数自行指定身份或伪造用户确认。
- 所有工具先验证订单归属；不存在与无权访问统一返回 `NOT_FOUND_OR_FORBIDDEN`，不返回订单详情。
- 读取接口无业务副作用。成功写操作才追加 `business_actions`；失败调用不写业务记录，技术调用日志留待后续运行器采集。
- 金额均为整数分。每条用例使用独立数据副本，所有工具共享该副本。
- Agent 必须能看到规则中的固定评测时间；工具内部也用同一个时钟。

| 工具名 | 状态 | 模型提供的参数 | 成功结果 | 失败情况／写入 |
| --- | --- | --- | --- | --- |
| `get_order` | 已实现 | `order_id: str` | 当前用户订单的商品、状态、金额、签收时间 | 不可访问返回统一错误；无写入 |
| `cancel_order` | 已实现 | `order_id: str` | `order_id`、`status: cancelled` | 非待付款返回 `ORDER_NOT_CANCELLABLE`；成功修改状态并追加操作记录 |
| `check_refund_eligibility` | 待实现 | `order_id: str` | `eligible`、`reason_code`、`amount_fen` | 无访问权不返回详情；根据 R06 判断；无写入 |
| `create_refund_request` | 待实现 | `order_id: str` | 申请编号、金额、`status: requested` | 工具重新核验资格与确认；不符合时不写入 |

两个已实现工具会去除订单号首尾空白，不改变大小写；非字符串、空串或全空白返回 `INVALID_ORDER_ID`，不产生业务变更。

## Python 使用与环境隔离

```python
from agent_bench import OrderTools

tools = OrderTools.from_fixture()
before = tools.get_order("O1001")
result = tools.cancel_order("O1001")
after = tools.get_order("O1001")
state_for_grader = tools.snapshot()
```

每次 `from_fixture()` 都读取一份独立初始数据；同一实例的工具共享状态。也可以使用 `OrderTools(fixture)` 从内存数据创建；构造时深拷贝，工具返回值和快照也不会共享内部可修改状态。

`snapshot()` 包含全体订单，只供测试／评测读取，不是 Agent 工具。接入模型时仅注册 `get_order` 和 `cancel_order`，不能把初始数据库、快照或对象内部字段交给模型。Python 对象封装本身不提供执行任意恶意代码的隔离。

环境支持 `OrderTools.from_fixture(clock_override="2026-11-04T10:00:00+08:00")`。固定时钟必须包含时区；操作记录使用该时间，不读取电脑当前时间。

当前工具是单进程、单次运行的内存模拟；未实现数据库持久化或并发事务。业务取消指令是否来自明确用户请求，将由后续 Agent／运行器层处理，当前函数调用本身表示执行该操作。

确认检查：运行环境记录本会话中针对该订单与金额的确认请求，以及其后用户的明确同意。提交工具检查这份受信任的会话状态。禁止仅凭模型传来的 `confirmed=true` 允许提交。第一版可由人工或固定对话脚本标记确认事件。

## 返回结构示例

成功查询：

```json
{"ok": true, "data": {"order_id": "O1001", "status": "pending_payment", "product_name": "无线鼠标", "total_amount_fen": 8900, "paid_amount_fen": 0, "delivered_at": null}}
```

不可访问：

```json
{"ok": false, "error": {"code": "NOT_FOUND_OR_FORBIDDEN", "message": "未找到可访问的订单，请核对订单号"}}
```

## 写入结构

取消操作记录包含 `action_id`、`action: cancel_order`、`order_id`、`actor_id`、`created_at`。

退款申请包含 `request_id`、`order_id`、`user_id`、`amount_fen`、`status: requested`、`created_at`；同时创建一条 `action: create_refund_request` 的操作记录，字段与取消记录一致。

编号只需唯一，不要求某个固定字符串。`created_at` 使用该用例固定时钟。

创建申请的错误码建议：`ORDER_NOT_DELIVERED`、`REFUND_WINDOW_EXPIRED`、`REFUND_WINDOW_NOT_STARTED`、`NOTHING_TO_REFUND`、`REFUND_ALREADY_REQUESTED`、`CONFIRMATION_REQUIRED`。错误本身不产生业务变更。

为便于入门，v0.1 的全额退货退款不处理物流、优惠券、部分退款、打款、人工工单和并发提交；下一阶段也无需一次实现这些功能。
