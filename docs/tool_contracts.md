# 下一阶段：模拟工具约定

这是一份实现说明，当前还没有工具代码。先实现前两个工具即可开始练习。

## 共用约定

- 当前用户、固定时钟与会话历史由运行环境提供，不能让模型通过参数自行指定身份或伪造用户确认。
- 所有工具先验证订单归属；不存在与无权访问统一返回 `NOT_FOUND_OR_FORBIDDEN`，不返回订单详情。
- 读取接口无业务副作用。成功写操作才追加 `business_actions`；失败调用仅写技术日志。
- 金额均为整数分。每条用例使用独立数据副本，所有工具共享该副本。
- Agent 必须能看到规则中的固定评测时间；工具内部也用同一个时钟。

| 工具名 | 模型提供的参数 | 成功结果 | 失败情况／写入 |
| --- | --- | --- | --- |
| `get_order` | `order_id: str` | 当前用户订单的商品、状态、金额、签收时间 | 不可访问返回统一错误；无写入 |
| `cancel_order` | `order_id: str` | `order_id`、`status: cancelled` | 非待付款返回 `ORDER_NOT_CANCELLABLE`；成功修改状态并追加操作记录 |
| `check_refund_eligibility` | `order_id: str` | `eligible`、`reason_code`、`amount_fen` | 无访问权不返回详情；根据 R06 判断；无写入 |
| `create_refund_request` | `order_id: str` | 申请编号、金额、`status: requested` | 工具重新核验资格与确认；不符合时不写入 |

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
