"""FastAPI dependencies: settings access now; auth, gate and use-case factories later."""

from typing import Annotated

from fastapi import Depends, Request

from app.presentation.api.schemas.base import CamelModel


class AppInfo(CamelModel):
    """Non-secret settings the presentation layer may read."""

    demo_controls: bool


def get_app_info(request: Request) -> AppInfo:
    info: AppInfo = request.app.state.app_info
    return info


AppInfoDep = Annotated[AppInfo, Depends(get_app_info)]
