"""Fictional company and employee used throughout the demo."""

from shared.config import DEFAULT_EMPLOYEE_ID

COMPANY_NAME = "Harbour Finch Labs"
COMPANY_NAME_ZH = "港雀科技"
DEMO_EMPLOYEE = {
    "id": DEFAULT_EMPLOYEE_ID,
    "name": "Alex Chen",
    "role": "Software Engineer",
    "department": "Engineering",
    "manager": "Maya Wong",
    "buddy": "Jamie Lau",
    "start_day": 1,
    "company": COMPANY_NAME,
    "company_zh": COMPANY_NAME_ZH,
    "is_demo": True,
}
