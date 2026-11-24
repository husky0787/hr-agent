"""Recognize documented policy topics without another language-model request."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata
from typing import Iterable

from shared.config import SEED_DATA_DIR
from shared.documents import DOCUMENT_TITLES

# Headings are the source of truth. Aliases only recognize how visitors ask about them.
ALIASES: dict[str, tuple[str, ...]] = {
    "公司及團隊": ("公司介紹", "公司背景", "團隊介紹", "主管", "company introduction", "company overview", "team", "manager"),
    "公司有薪年假": ("年假", "有薪年假", "带薪年假", "annual leave", "paid annual leave", "PTO", "vacation"),
    "未放取年假及結轉": ("年假結轉", "年假结转", "結轉", "结转", "未放年假", "carryover", "carry over", "unused annual leave"),
    "病假及醫生證明書": ("病假", "醫生紙", "医生证明", "醫生證明", "sick leave", "medical certificate", "doctor's note"),
    "事假及其他假期": ("事假", "婚假", "恩恤假", "喪假", "丧假", "personal leave", "marriage leave", "bereavement leave", "unpaid leave"),
    "出糧日期及糧單": ("出糧", "出粮", "糧單", "粮单", "發薪", "发薪", "payroll", "payday", "pay day", "payslip", "salary payment"),
    "更改出糧戶口": ("出糧戶口", "出粮户口", "銀行戶口", "银行账户", "bank account", "bank details"),
    "工作時間、午膳及遲到": ("工作時間", "工作时间", "上下班", "午膳", "遲到", "迟到", "working hours", "office hours", "lunch", "late for work"),
    "加班及補假": ("加班", "補假", "补假", "overtime", "time off in lieu", "compensatory leave"),
    "公司假期日曆": ("假期日曆", "假期日历", "公眾假期", "公众假期", "法定假日", "holiday calendar", "public holidays", "statutory holidays"),
    "試用期及轉正": ("試用期", "试用期", "轉正", "转正", "probation", "confirmation of employment"),
    "離職及工作交接": ("離職", "离职", "辭職", "辞职", "通知期", "resignation", "notice period", "handover", "offboarding"),
    "行為守則": ("行為守則", "行为守则", "歧視", "歧视", "騷擾", "骚扰", "利益衝突", "code of conduct", "harassment", "discrimination", "conflict of interest"),
    "醫療保險登記": ("醫療保險", "医疗保险", "醫保登記", "医保登记", "medical insurance", "health insurance", "medical enrollment", "medical enrolment", "insurance registration"),
    "醫療保障及索償": ("醫療保障", "医疗保障", "醫療索償", "医疗索赔", "牙科", "眼科", "門診", "门诊", "住院", "medical coverage", "medical claims", "dental", "optical", "outpatient", "hospitalization"),
    "強積金登記及供款紀錄": ("強積金", "强积金", "供款紀錄", "供款记录", "MPF", "pension", "retirement contributions"),
    "報稅文件": ("報稅", "报税", "稅務文件", "税务文件", "tax documents", "tax forms", "tax filing"),
    "產假": ("產假", "产假", "maternity", "maternity leave"),
    "侍產假": ("侍產假", "侍产假", "陪產假", "陪产假", "paternity", "paternity leave"),
    "健康津貼": ("健康津貼", "健康津贴", "健身津貼", "健身津贴", "wellness", "wellness stipend", "wellness allowance", "fitness allowance"),
    "開支報銷貨幣及收據": ("報銷", "报销", "開支", "开支", "收據", "收据", "expense claims", "expense reimbursement", "reimbursement currency", "receipts", "expenses"),
    "差旅、交通及餐飲開支": ("差旅", "交通費", "交通费", "餐飲", "餐饮", "客戶餐飲", "business travel", "transport expenses", "client meals", "meal expenses"),
    "報銷審批及付款": ("報銷流程", "报销流程", "報銷審批", "报销审批", "報銷付款", "报销付款", "reimbursement process", "expense approval", "reimbursement payment", "lost receipt", "遺失收據", "遗失收据"),
    "工作電腦": ("電腦", "电脑", "工作裝置", "工作设备", "laptop", "computer", "MacBook", "Dell XPS", "device collection"),
    "VPN 設定": ("VPN", "虛擬專用網絡", "虚拟专用网络", "Cisco AnyConnect"),
    "Slack 設定": ("Slack", "工作區", "workspace", "channels", "頻道", "频道"),
    "磁碟加密": ("磁碟加密", "磁盘加密", "全碟加密", "全盘加密", "disk encryption", "FileVault", "BitLocker"),
    "雙重認證": ("雙重認證", "双重认证", "雙因素", "双因素", "two-factor", "two factor", "2FA", "MFA"),
    "密碼管理": ("密碼", "密码", "password", "1Password", "recovery codes", "復原碼", "恢复码"),
    "個人資料及機密文件": ("個人資料", "个人资料", "機密文件", "机密文件", "私隱", "隐私", "personal data", "confidential documents", "privacy"),
    "可疑電郵、裝置遺失及保安事故": ("可疑電郵", "可疑邮件", "裝置遺失", "设备遗失", "保安事故", "安全事故", "phishing", "lost device", "security incident", "suspicious email"),
    "開發環境及系統權限": ("開發環境", "开发环境", "系統權限", "系统权限", "GitHub", "Developer Access", "development environment", "system access"),
    "IT 支援聯絡方式": ("IT 支援", "IT支持", "IT support", "helpdesk", "help desk", "IT 工單", "IT工单"),
    "第一星期：完成基本入職安排": ("第一天", "首日", "第一星期", "第一周", "first day", "first week", "day one", "onboarding buddy", "入職夥伴", "入职伙伴"),
    "第二星期：熟習團隊及工作流程": ("第二星期", "第二周", "second week", "week two", "week 2"),
    "第三星期：參與實際工作": ("第三星期", "第三周", "third week", "week three", "week 3"),
    "第四星期：檢視首月進度": ("第四星期", "第四周", "首月進度", "首月进度", "fourth week", "week four", "week 4", "first month review"),
    "工程團隊專屬安排": ("工程團隊", "工程团队", "工程部", "engineering onboarding", "engineering team", "code review", "程式碼審查", "代码审查"),
    "入職文件提交方式": ("入職文件", "入职文件", "人事文件", "人事表格", "安全文件區", "安全文件区", "onboarding documents", "onboarding forms"),
    "入職期間遇到問題": ("入職問題", "入职问题", "入職聯絡", "入职联系", "onboarding contacts", "onboarding help", "who to contact"),
}


@dataclass(frozen=True)
class Topic:
    source: str
    heading: str
    aliases: tuple[str, ...]

    @property
    def query(self) -> str:
        return f"{self.heading}的政策內容及適用安排"


def inventory(seed_dir: Path = SEED_DATA_DIR, filenames: Iterable[str] | None = None) -> list[Topic]:
    topics = []
    root = Path(seed_dir).resolve()
    for filename in filenames if filenames is not None else DOCUMENT_TITLES:
        path = (root / filename).resolve()
        if path.parent != root or not path.is_file():
            continue
        for heading in re.findall(r"^##\s+(.+)$", path.read_text(encoding="utf-8"), re.M):
            heading = heading.strip()
            topics.append(Topic(filename, heading, tuple(dict.fromkeys((heading, *ALIASES.get(heading, ()))))))
    return topics


def _normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def detect_topics(query: str, seed_dir: Path = SEED_DATA_DIR, filenames: Iterable[str] | None = None) -> list[Topic]:
    text = _normalize(query)
    candidates = []
    for topic in inventory(seed_dir, filenames):
        for alias in topic.aliases:
            alias = _normalize(alias)
            # English abbreviations must not match substrings inside unrelated words.
            pattern = (r"(?<![a-z0-9])" if re.match(r"[a-z0-9]", alias) else "") + re.escape(alias)
            if re.search(r"[a-z0-9]$", alias):
                pattern += r"(?![a-z0-9])"
            for match in re.finditer(pattern, text):
                candidates.append((match.start(), match.end(), topic))
    # Prefer full phrases: 侍產假 must not also recognize the nested 產假.
    accepted = []
    for start, end, topic in sorted(candidates, key=lambda row: (-(row[1] - row[0]), row[0])):
        if not any(start < previous_end and end > previous_start for previous_start, previous_end, _ in accepted):
            accepted.append((start, end, topic))
    found = []
    for _, _, topic in sorted(accepted, key=lambda row: row[0]):
        if topic not in found:
            found.append(topic)
    return found
