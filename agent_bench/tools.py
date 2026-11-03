"""订单查询与取消；每个实例代表一次独立的模拟运行。"""

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


DEFAULT_FIXTURE_PATH = Path(__file__).resolve().parent.parent / "data" / "orders.json"


class OrderTools:
    """由运行环境创建，把两个业务方法交给 Agent，保留 snapshot 给评测。

    当前身份和时钟从可信初始数据取得，工具参数只包含订单号。
    所有变更只存在当前实例内存中，不会写回初始数据文件。
    """

    def __init__(
        self,
        fixture: dict[str, Any],
        *,
        clock_override: str | None = None,
    ) -> None:
        self._state = deepcopy(fixture)
        self._current_user_id = self._state["current_user_id"]
        if not isinstance(self._current_user_id, str) or not self._current_user_id.strip():
            raise ValueError("初始数据必须包含有效的 current_user_id")

        clock_text = self._state["clock"] if clock_override is None else clock_override
        clock = datetime.fromisoformat(clock_text)
        if clock.utcoffset() is None:
            raise ValueError("评测时钟必须包含时区，例如 2026-11-03T10:00:00+08:00")
        self._state["clock"] = clock.isoformat()

        order_ids = [order["order_id"] for order in self._state["orders"]]
        if len(set(order_ids)) != len(order_ids):
            raise ValueError("初始订单号不能重复")

    @classmethod
    def from_fixture(
        cls,
        fixture_path: str | Path | None = None,
        *,
        clock_override: str | None = None,
    ) -> "OrderTools":
        """读取初始数据；每次调用都获得一份新的独立环境。"""
        path = DEFAULT_FIXTURE_PATH if fixture_path is None else Path(fixture_path)
        with path.open(encoding="utf-8") as fixture_file:
            fixture = json.load(fixture_file)
        return cls(fixture, clock_override=clock_override)

    def get_order(self, order_id: str) -> dict[str, Any]:
        """查询当前用户的订单，不产生业务变更。"""
        normalized_id = self._normalize_order_id(order_id)
        if normalized_id is None:
            return self._invalid_order_id()

        order = self._find_accessible_order(normalized_id)
        if order is None:
            return self._not_found_or_forbidden()

        # 只返回工具约定的字段，不暴露用户归属或整个数据库。
        fields = (
            "order_id",
            "status",
            "product_name",
            "total_amount_fen",
            "paid_amount_fen",
            "delivered_at",
        )
        return {"ok": True, "data": deepcopy({field: order[field] for field in fields})}

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        """取消本人待付款订单，并记录一次成功的业务变更。"""
        normalized_id = self._normalize_order_id(order_id)
        if normalized_id is None:
            return self._invalid_order_id()

        # 必须先检查权限，再判断状态，避免通过错误信息泄露他人订单状态。
        order = self._find_accessible_order(normalized_id)
        if order is None:
            return self._not_found_or_forbidden()
        if order["status"] != "pending_payment":
            return {
                "ok": False,
                "error": {
                    "code": "ORDER_NOT_CANCELLABLE",
                    "message": "仅待付款订单可取消，当前订单不能取消",
                },
            }

        action = {
            "action_id": uuid4().hex,
            "action": "cancel_order",
            "order_id": normalized_id,
            "actor_id": self._current_user_id,
            "created_at": self._state["clock"],
        }
        self._state["business_actions"].append(action)
        order["status"] = "cancelled"
        return {"ok": True, "data": {"order_id": normalized_id, "status": "cancelled"}}

    def snapshot(self) -> dict[str, Any]:
        """供测试／评测检查最终状态；不能注册为 Agent 可调用的工具。"""
        return deepcopy(self._state)

    def _find_accessible_order(self, order_id: str) -> dict[str, Any] | None:
        for order in self._state["orders"]:
            if order["order_id"] == order_id and order["user_id"] == self._current_user_id:
                return order
        return None

    @staticmethod
    def _normalize_order_id(order_id: str) -> str | None:
        if not isinstance(order_id, str) or not order_id.strip():
            return None
        return order_id.strip()

    @staticmethod
    def _invalid_order_id() -> dict[str, Any]:
        return {
            "ok": False,
            "error": {"code": "INVALID_ORDER_ID", "message": "请提供非空的订单号"},
        }

    @staticmethod
    def _not_found_or_forbidden() -> dict[str, Any]:
        return {
            "ok": False,
            "error": {
                "code": "NOT_FOUND_OR_FORBIDDEN",
                "message": "未找到可访问的订单，请核对订单号",
            },
        }
