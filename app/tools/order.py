from pydantic import BaseModel, Field


class GetOrderStatusArgs(BaseModel):
    """查询订单状态工具的入参。"""

    order_id: str = Field(min_length=1, description="订单编号")


def get_order_status(args: GetOrderStatusArgs) -> str:
    """返回 mock 订单状态，后续可替换为真实订单服务调用。"""
    return f"订单 {args.order_id} 当前状态：已发货，预计 2 天内送达。"
