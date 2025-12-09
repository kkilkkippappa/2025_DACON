from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

class DashboardData(BaseModel):
    title: str
    content: str

@router.get("/")
async def get_dashboard():
    """대시보드 메인 데이터"""
    return {
        "title": "Dashboard",
        "widgets": [
            {"id": 1, "name": "Statistics"},
            {"id": 2, "name": "Charts"},
            {"id": 3, "name": "Recent Activity"}
        ]
    }


@router.post("/update")
async def update_dashboard(data: DashboardData):
    """대시보드 업데이트"""
    return {"message": "Dashboard updated", "data": data}
