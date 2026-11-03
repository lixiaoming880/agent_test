"""在仓库根目录执行 python -m agent_bench 查看使用方法。"""

import argparse
import json
import sys

from .tools import OrderTools


def run_demo() -> dict:
    """在同一个环境中演示查询、取消、重复取消和权限限制。"""
    tools = OrderTools.from_fixture()
    steps = [
        {"step": "查询本人订单", "result": tools.get_order("O1001")},
        {"step": "取消待付款订单", "result": tools.cancel_order("O1001")},
        {"step": "再次查询，验证状态改变", "result": tools.get_order("O1001")},
        {"step": "重复取消，不新增操作记录", "result": tools.cancel_order("O1001")},
        {"step": "拒绝取消已发货订单", "result": tools.cancel_order("O1002")},
        {"step": "拒绝读取他人订单", "result": tools.get_order("O2001")},
        {"step": "查询不存在的订单", "result": tools.get_order("O9999")},
    ]
    snapshot = tools.snapshot()
    return {
        "mode": "isolated_in_memory_demo",
        "steps": steps,
        "business_actions": snapshot["business_actions"],
        "refund_request_count": len(snapshot["refund_requests"]),
        "fixture_file_modified": False,
    }


def main() -> int:
    # Windows 重定向／管道也输出 UTF-8，保持中文 JSON 可被一致读取。
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="AgentBench-Lite：模拟订单工具，无需模型 API")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("demo", help="演示同一次运行中的状态变化与拒绝操作")
    query = commands.add_parser("get-order", help="查询本人订单")
    query.add_argument("order_id", help="例如 O1001")
    cancel = commands.add_parser("cancel-order", help="取消本人待付款订单")
    cancel.add_argument("order_id", help="例如 O1001")
    args = parser.parse_args()

    if args.command == "demo":
        result = run_demo()
        exit_code = 0
    else:
        tools = OrderTools.from_fixture()
        if args.command == "get-order":
            result = tools.get_order(args.order_id)
        else:
            result = tools.cancel_order(args.order_id)
        exit_code = 0 if result["ok"] else 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
