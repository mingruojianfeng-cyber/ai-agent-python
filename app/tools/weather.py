from pydantic import BaseModel, Field


class GetWeatherArgs(BaseModel):
    """查询天气工具的入参。"""

    city: str = Field(min_length=1, description="城市名称")


def get_weather(args: GetWeatherArgs) -> str:
    """返回 mock 天气信息，后续可替换为真实天气 API 调用。"""
    return f"{args.city} 今日天气：晴，气温 18-26℃，适合出行。"
