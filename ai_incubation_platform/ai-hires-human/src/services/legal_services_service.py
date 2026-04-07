"""
法律服务支持。

v1.21.0 新增：法律法规支持功能
- 合同模板库（劳务/保密/知识产权）
- 法务咨询（在线咨询/文书审核）
- 权益保护（维权援助/投诉举报）
- 税务规划（个税计算/发票管理）
- 合规检查（任务合规性自动检查）
"""
from __future__ import annotations

import uuid
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from models.legal_services import (
    ContractType,
    ContractParty,
    ContractTemplate,
    GeneratedContract,
    ContractSignRequest,
    LegalConsultationType,
    ConsultationStatus,
    LegalConsultation,
    ConsultationMessage,
    RightsViolationType,
    ComplaintStatus,
    RightsComplaint,
    ComplaintEvidence,
    TaxType,
    TaxBracket,
    TaxCalculationRequest,
    TaxCalculationResult,
    Invoice,
    TaxFiling,
    ComplianceCategory,
    ComplianceRiskLevel,
    ComplianceCheckResult,
    ComplianceRule,
    LawyerProfile,
    ContractTemplateList,
    GeneratedContractResponse,
    LegalConsultationResponse,
    RightsComplaintResponse,
    TaxCalculationResponse,
    ComplianceCheckResponse,
    LegalServicesSummary,
)

from services.worker_profile_service import worker_profile_service

import logging

logger = logging.getLogger(__name__)


class LegalServicesService:
    """
    法律服务支持。

    提供以下功能：
    1. 合同模板库：标准合同模板管理、合同生成、电子签署
    2. 法务咨询：在线咨询、合同审核、文书审阅
    3. 权益保护：投诉举报、维权援助、调解仲裁
    4. 税务规划：个税计算、发票管理、税务申报
    5. 合规检查：任务合规性自动检查、风险预警
    """

    def __init__(self) -> None:
        # 合同模板存储
        self._contract_templates: Dict[str, ContractTemplate] = {}
        self._generated_contracts: Dict[str, GeneratedContract] = {}
        self._user_contracts: Dict[str, List[str]] = {}  # user_id -> [contract_ids]

        # 法务咨询存储
        self._legal_consultations: Dict[str, LegalConsultation] = {}
        self._user_consultations: Dict[str, List[str]] = {}  # user_id -> [consultation_ids]
        self._consultation_messages: Dict[str, List[ConsultationMessage]] = {}  # consultation_id -> [messages]

        # 权益保护存储
        self._rights_complaints: Dict[str, RightsComplaint] = {}
        self._user_complaints: Dict[str, List[str]] = {}  # user_id -> [complaint_ids]
        self._complaint_evidence: Dict[str, List[ComplaintEvidence]] = {}  # complaint_id -> [evidence]

        # 税务规划存储
        self._invoices: Dict[str, Invoice] = {}
        self._tax_filings: Dict[str, TaxFiling] = {}
        self._user_invoices: Dict[str, List[str]] = {}  # user_id -> [invoice_ids]
        self._user_tax_filings: Dict[str, List[str]] = {}  # user_id -> [filing_ids]

        # 合规检查存储
        self._compliance_checks: Dict[str, ComplianceCheckResult] = {}
        self._compliance_rules: Dict[str, ComplianceRule] = {}
        self._object_checks: Dict[str, List[str]] = {}  # object_type:object_id -> [check_ids]

        # 律师档案存储
        self._lawyer_profiles: Dict[str, LawyerProfile] = {}

        # 初始化预置数据
        self._init_default_data()

    def _init_default_data(self) -> None:
        """初始化默认数据（合同模板、合规规则、律师档案等）。"""
        self._init_contract_templates()
        self._init_compliance_rules()
        self._init_lawyer_profiles()

    def _init_contract_templates(self) -> None:
        """初始化合同模板。"""
        # 劳务合同模板
        labor_template = ContractTemplate(
            template_id="tmpl_labor_001",
            name="标准劳务合同",
            contract_type=ContractType.LABOR,
            description="适用于临时性、辅助性、替代性工作的标准劳务合同",
            content="""# 劳务合同

甲方（雇主）：{employer_name}
身份证号/统一社会信用代码：{employer_id}
联系地址：{employer_address}

乙方（工人）：{worker_name}
身份证号：{worker_id}
联系地址：{worker_address}

## 第一条 工作内容
1. 乙方同意根据甲方工作需要，从事 {job_description} 工作。
2. 乙方应按照甲方要求，按时、按质、按量完成工作任务。

## 第二条 合同期限
本合同有效期自 {start_date} 至 {end_date}。

## 第三条 劳务报酬
1. 劳务报酬标准：{payment_amount} 元（税前）。
2. 支付方式：{payment_method}。
3. 支付时间：{payment_time}。

## 第四条 工作时间和休息休假
1. 工作时间：{work_hours}。
2. 休息休假：{rest_days}。

## 第五条 社会保险
甲乙双方按照国家和地方有关规定参加社会保险。

## 第六条 劳动保护和劳动条件
甲方为乙方提供必要的劳动条件和劳动保护用品。

## 第七条 合同的变更、解除和终止
1. 经甲乙双方协商一致，可以变更或解除本合同。
2. 合同期满或约定的终止条件出现，本合同终止。

## 第八条 违约责任
任何一方违反本合同约定，应承担违约责任，赔偿对方因此遭受的损失。

## 第九条 争议解决
因履行本合同发生的争议，由双方协商解决；协商不成的，可向甲方所在地人民法院提起诉讼。

## 第十条 其他约定
{other_terms}

甲方（签字）：____________    乙方（签字）：____________
签订日期：{sign_date}
""",
            applicable_scenarios=[
                "临时性工作",
                "兼职工作",
                "项目制工作",
                "短期劳务"
            ],
            required_variables=[
                "employer_name", "employer_id", "employer_address",
                "worker_name", "worker_id", "worker_address",
                "job_description", "start_date", "end_date",
                "payment_amount", "payment_method", "payment_time"
            ],
            optional_variables=[
                "work_hours", "rest_days", "other_terms"
            ],
            jurisdictions=["CN"],
            version="1.0",
            is_active=True,
            usage_count=0,
            created_at=datetime.now(),
        )
        self._contract_templates["tmpl_labor_001"] = labor_template

        # 保密协议模板
        nda_template = ContractTemplate(
            template_id="tmpl_nda_001",
            name="保密协议",
            contract_type=ContractType.NDA,
            description="保护商业秘密和知识产权的保密协议",
            content="""# 保密协议

甲方（披露方）：{discloser_name}
地址：{discloser_address}

乙方（接收方）：{recipient_name}
地址：{recipient_address}

## 鉴于
甲乙双方正在进行 {cooperation_purpose} 的合作洽谈/合作，在此过程中，甲方可能向乙方披露某些保密信息。
为保护甲方的合法权益，双方经友好协商，达成如下协议：

## 第一条 保密信息的定义
本协议所称保密信息，是指甲方以口头、书面或其他形式向乙方披露的、不为公众所知悉、能为甲方带来经济利益、具有实用性并经甲方采取保密措施的技术信息和经营信息，包括但不限于：
1. 技术信息：{technical_info_scope}
2. 经营信息：{business_info_scope}
3. 其他信息：{other_info_scope}

## 第二条 保密义务
1. 乙方应对保密信息严格保密，未经甲方书面同意，不得向任何第三方披露。
2. 乙方应采取合理的保密措施，防止保密信息泄露。
3. 乙方只能将保密信息用于 {permitted_use} 目的。

## 第三条 保密期限
本协议项下的保密义务自本协议签订之日起生效，至保密信息公开披露之日止，但最短不少于 {confidentiality_period} 年。

## 第四条 知识产权
1. 甲方披露保密信息，不构成任何知识产权的许可或转让。
2. 乙方基于保密信息所产生的任何成果，其知识产权归 {ip_owner} 所有。

## 第五条 违约责任
乙方违反本协议约定，应向甲方支付违约金 {penalty_amount} 元；违约金不足以弥补甲方损失的，乙方还应赔偿甲方的实际损失。

## 第六条 争议解决
因本协议引起的或与本协议有关的任何争议，由双方协商解决；协商不成的，提交 {dispute_resolution}。

## 第七条 其他
{other_terms}

甲方（盖章）：____________    乙方（盖章）：____________
授权代表（签字）：________    授权代表（签字）：________
签订日期：{sign_date}
""",
            applicable_scenarios=[
                "商业合作洽谈",
                "技术交流",
                "供应商合作",
                "员工入职"
            ],
            required_variables=[
                "discloser_name", "discloser_address",
                "recipient_name", "recipient_address",
                "cooperation_purpose",
                "permitted_use", "confidentiality_period",
                "ip_owner", "penalty_amount", "dispute_resolution"
            ],
            optional_variables=[
                "technical_info_scope", "business_info_scope",
                "other_info_scope", "other_terms"
            ],
            jurisdictions=["CN"],
            version="1.0",
            is_active=True,
            usage_count=0,
            created_at=datetime.now(),
        )
        self._contract_templates["tmpl_nda_001"] = nda_template

        # 知识产权转让协议模板
        ip_template = ContractTemplate(
            template_id="tmpl_ip_001",
            name="知识产权转让协议",
            contract_type=ContractType.IP_ASSIGNMENT,
            description="用于转让专利、商标、著作权等知识产权",
            content="""# 知识产权转让协议

甲方（转让方）：{transferor_name}
地址：{transferor_address}
法定代表人：{transferor_legal_rep}

乙方（受让方）：{transferee_name}
地址：{transferee_address}
法定代表人：{transferee_legal_rep}

## 第一条 转让标的
1. 甲方同意将其拥有的以下知识产权转让给乙方：
   - 知识产权名称：{ip_name}
   - 知识产权类型：{ip_type}
   - 登记号/申请号：{ip_registration_number}
   - 权利范围：{ip_scope}

## 第二条 转让方式
本次转让为 {transfer_type} 转让（独占/排他/普通）。

## 第三条 转让价格及支付方式
1. 转让价格：{transfer_price} 元（税前）。
2. 支付方式：{payment_method}。
3. 支付时间：{payment_schedule}。

## 第四条 权利保证
1. 甲方保证其为转让知识产权的合法权利人。
2. 甲方保证转让知识产权不存在任何权利瑕疵。
3. 甲方保证转让知识产权未侵犯任何第三方的合法权益。

## 第五条 资料交付
甲方应于本合同生效后 {delivery_days} 日内，将与转让知识产权有关的全部资料交付乙方。

## 第六条 协助义务
甲方应协助乙方办理转让知识产权的权利人变更手续。

## 第七条 违约责任
任何一方违反本合同约定，应承担违约责任，赔偿对方因此遭受的全部损失。

## 第八条 争议解决
因本合同引起的或与本合同有关的任何争议，提交 {dispute_resolution}。

## 第九条 其他
{other_terms}

甲方（盖章）：____________    乙方（盖章）：____________
授权代表（签字）：________    授权代表（签字）：________
签订日期：{sign_date}
""",
            applicable_scenarios=[
                "专利转让",
                "商标转让",
                "著作权转让",
                "技术成果转让"
            ],
            required_variables=[
                "transferor_name", "transferor_address", "transferor_legal_rep",
                "transferee_name", "transferee_address", "transferee_legal_rep",
                "ip_name", "ip_type", "ip_registration_number", "ip_scope",
                "transfer_type", "transfer_price", "payment_method", "payment_schedule",
                "delivery_days", "dispute_resolution"
            ],
            optional_variables=[
                "other_terms"
            ],
            jurisdictions=["CN"],
            version="1.0",
            is_active=True,
            usage_count=0,
            created_at=datetime.now(),
        )
        self._contract_templates["tmpl_ip_001"] = ip_template

    def _init_compliance_rules(self) -> None:
        """初始化合规规则。"""
        # 劳动法合规规则
        labor_rules = [
            ComplianceRule(
                rule_id="rule_labor_001",
                name="最低工资标准检查",
                description="检查任务报酬是否低于当地最低工资标准",
                category=ComplianceCategory.LABOR_LAW,
                jurisdictions=["CN"],
                rule_expression="reward_amount >= min_wage * work_hours",
                violation_condition="reward_amount < min_wage * work_hours",
                default_risk_level=ComplianceRiskLevel.HIGH,
                suggestion_template="建议将报酬调整为不低于每小时 {min_wage} 元，总计不低于 {required_amount} 元",
                regulation_reference="《劳动法》第四十八条、《最低工资规定》",
                is_active=True,
                created_at=datetime.now(),
            ),
            ComplianceRule(
                rule_id="rule_labor_002",
                name="工作时间合规检查",
                description="检查任务工作时间是否符合劳动法规定",
                category=ComplianceCategory.LABOR_LAW,
                jurisdictions=["CN"],
                rule_expression="work_hours <= 8 and overtime_hours <= 3",
                violation_condition="work_hours > 8 or overtime_hours > 3",
                default_risk_level=ComplianceRiskLevel.MEDIUM,
                suggestion_template="建议将每日工作时间控制在 8 小时以内，加班不超过 3 小时",
                regulation_reference="《劳动法》第三十六条、第四十一条",
                is_active=True,
                created_at=datetime.now(),
            ),
        ]
        for rule in labor_rules:
            self._compliance_rules[rule.rule_id] = rule

        # 税法合规规则
        tax_rules = [
            ComplianceRule(
                rule_id="rule_tax_001",
                name="个人所得税代扣代缴检查",
                description="检查是否按规定代扣代缴个人所得税",
                category=ComplianceCategory.TAX_LAW,
                jurisdictions=["CN"],
                rule_expression="tax_withheld >= calculate_tax(reward_amount)",
                violation_condition="tax_withheld < calculate_tax(reward_amount)",
                default_risk_level=ComplianceRiskLevel.HIGH,
                suggestion_template="建议按规定代扣代缴个人所得税，金额为 {tax_amount} 元",
                regulation_reference="《个人所得税法》第九条、第十条",
                is_active=True,
                created_at=datetime.now(),
            ),
        ]
        for rule in tax_rules:
            self._compliance_rules[rule.rule_id] = rule

        # 知识产权合规规则
        ip_rules = [
            ComplianceRule(
                rule_id="rule_ip_001",
                name="知识产权归属检查",
                description="检查任务交付物的知识产权归属是否明确",
                category=ComplianceCategory.IP_LAW,
                jurisdictions=["CN"],
                rule_expression="'ip_ownership' in acceptance_criteria",
                violation_condition="'ip_ownership' not in acceptance_criteria",
                default_risk_level=ComplianceRiskLevel.MEDIUM,
                suggestion_template="建议在任务要求中明确交付物的知识产权归属",
                regulation_reference="《著作权法》第十九条、《专利法》第八条",
                is_active=True,
                created_at=datetime.now(),
            ),
        ]
        for rule in ip_rules:
            self._compliance_rules[rule.rule_id] = rule

        # 数据隐私合规规则
        privacy_rules = [
            ComplianceRule(
                rule_id="rule_privacy_001",
                name="个人信息保护检查",
                description="检查任务是否涉及违规收集个人信息",
                category=ComplianceCategory.DATA_PRIVACY,
                jurisdictions=["CN"],
                rule_expression="not requires_personal_info or has_privacy_policy",
                violation_condition="requires_personal_info and not has_privacy_policy",
                default_risk_level=ComplianceRiskLevel.CRITICAL,
                suggestion_template="涉及个人信息收集的任务，必须提供隐私政策并获得用户同意",
                regulation_reference="《个人信息保护法》《数据安全法》",
                is_active=True,
                created_at=datetime.now(),
            ),
        ]
        for rule in privacy_rules:
            self._compliance_rules[rule.rule_id] = rule

    def _init_lawyer_profiles(self) -> None:
        """初始化律师档案。"""
        lawyers = [
            LawyerProfile(
                lawyer_id="lawyer_001",
                name="张律师",
                title="合伙人律师",
                law_firm="某某律师事务所",
                practice_areas=["劳动法", "合同法", "知识产权"],
                license_number="110123456789",
                license_jurisdiction="CN-BJ",
                years_of_experience=10,
                bio="张律师毕业于北京大学法学院，专注于劳动法、合同法和知识产权领域，拥有丰富的实务经验。",
                rating=4.9,
                total_consultations=500,
                total_cases=200,
                consultation_fee_per_hour=500.0,
                is_available_for_consultation=True,
                served_jurisdictions=["CN", "CN-BJ", "CN-SH"],
                created_at=datetime.now(),
            ),
            LawyerProfile(
                lawyer_id="lawyer_002",
                name="李律师",
                title="专职律师",
                law_firm="某某律师事务所",
                practice_areas=["税法", "公司法", "商事仲裁"],
                license_number="110987654321",
                license_jurisdiction="CN-SH",
                years_of_experience=8,
                bio="李律师毕业于复旦大学法学院，专注于税法、公司法和商事仲裁领域。",
                rating=4.8,
                total_consultations=300,
                total_cases=150,
                consultation_fee_per_hour=400.0,
                is_available_for_consultation=True,
                served_jurisdictions=["CN", "CN-SH", "CN-GZ"],
                created_at=datetime.now(),
            ),
        ]
        for lawyer in lawyers:
            self._lawyer_profiles[lawyer.lawyer_id] = lawyer

    # ========== 合同模板库相关方法 ==========

    def list_templates(
        self,
        contract_type: Optional[ContractType] = None,
        jurisdiction: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> ContractTemplateList:
        """获取合同模板列表。"""
        templates = list(self._contract_templates.values())

        # 筛选
        if contract_type:
            templates = [t for t in templates if t.contract_type == contract_type]
        if jurisdiction:
            templates = [t for t in templates if jurisdiction in t.jurisdictions]
        templates = [t for t in templates if t.is_active]

        total = len(templates)
        templates = templates[skip:skip + limit]

        return ContractTemplateList(
            templates=templates,
            total=total,
            skip=skip,
            limit=limit,
        )

    def get_template(self, template_id: str) -> Optional[ContractTemplate]:
        """获取合同模板详情。"""
        return self._contract_templates.get(template_id)

    def generate_contract(
        self,
        template_id: str,
        employer_id: str,
        worker_id: str,
        variables: Dict[str, str],
        task_id: Optional[str] = None,
        contract_value: float = 0.0,
        jurisdiction: str = "CN",
    ) -> GeneratedContract:
        """根据模板生成合同。"""
        template = self._contract_templates.get(template_id)
        if not template:
            raise ValueError(f"合同模板不存在：{template_id}")

        # 检查必填变量
        missing_vars = [v for v in template.required_variables if v not in variables]
        if missing_vars:
            raise ValueError(f"缺少必填变量：{', '.join(missing_vars)}")

        # 替换变量生成合同内容
        content = template.content
        for key, value in variables.items():
            content = content.replace("{" + key + "}", value)

        # 添加可选变量
        for key, value in variables.items():
            if key in template.optional_variables:
                content = content.replace("{" + key + "}", value)

        contract_id = f"contract_{uuid.uuid4().hex[:12]}"
        contract = GeneratedContract(
            contract_id=contract_id,
            template_id=template_id,
            contract_type=template.contract_type,
            employer_id=employer_id,
            worker_id=worker_id,
            task_id=task_id,
            content=content,
            contract_value=contract_value,
            currency="CNY",
            status="draft",
            jurisdiction=jurisdiction,
            created_at=datetime.now(),
        )

        self._generated_contracts[contract_id] = contract

        # 更新用户合同列表
        if employer_id not in self._user_contracts:
            self._user_contracts[employer_id] = []
        self._user_contracts[employer_id].append(contract_id)

        if worker_id not in self._user_contracts:
            self._user_contracts[worker_id] = []
        self._user_contracts[worker_id].append(contract_id)

        # 更新模板使用次数
        template.usage_count += 1

        logger.info(f"生成合同：{contract_id}, 模板：{template_id}, 雇主：{employer_id}, 工人：{worker_id}")
        return contract

    def get_contract(self, contract_id: str) -> Optional[GeneratedContract]:
        """获取合同详情。"""
        return self._generated_contracts.get(contract_id)

    def sign_contract(self, contract_id: str, party: ContractParty) -> bool:
        """签署合同。"""
        contract = self._generated_contracts.get(contract_id)
        if not contract:
            raise ValueError(f"合同不存在：{contract_id}")

        if party == ContractParty.EMPLOYER:
            contract.employer_signed_at = datetime.now()
        elif party == ContractParty.WORKER:
            contract.worker_signed_at = datetime.now()

        # 检查是否双方都已签署
        if contract.employer_signed_at and contract.worker_signed_at:
            contract.status = "active"

        logger.info(f"合同 {contract_id} 被 {party} 签署")
        return True

    def get_user_contracts(
        self,
        user_id: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[GeneratedContract]:
        """获取用户的合同列表。"""
        contract_ids = self._user_contracts.get(user_id, [])
        contracts = [self._generated_contracts[cid] for cid in contract_ids if cid in self._generated_contracts]

        if status:
            contracts = [c for c in contracts if c.status == status]

        return contracts[skip:skip + limit]

    # ========== 法务咨询相关方法 ==========

    def create_consultation(
        self,
        user_id: str,
        user_type: str,
        consultation_type: LegalConsultationType,
        title: str,
        description: str,
        attachments: Optional[List[str]] = None,
        related_task_id: Optional[str] = None,
        related_contract_id: Optional[str] = None,
        priority: str = "normal",
    ) -> LegalConsultation:
        """创建法律咨询。"""
        consultation_id = f"consult_{uuid.uuid4().hex[:12]}"

        # 根据咨询类型自动匹配律师
        assigned_lawyer = self._match_lawyer_for_consultation(consultation_type)

        consultation = LegalConsultation(
            consultation_id=consultation_id,
            user_id=user_id,
            user_type=user_type,
            consultation_type=consultation_type,
            title=title,
            description=description,
            attachments=attachments or [],
            related_task_id=related_task_id,
            related_contract_id=related_contract_id,
            status=ConsultationStatus.PENDING,
            priority=priority,
            assigned_lawyer_id=assigned_lawyer.lawyer_id if assigned_lawyer else None,
            assigned_lawyer_name=assigned_lawyer.name if assigned_lawyer else None,
            created_at=datetime.now(),
        )

        self._legal_consultations[consultation_id] = consultation

        # 更新用户咨询列表
        if user_id not in self._user_consultations:
            self._user_consultations[user_id] = []
        self._user_consultations[user_id].append(consultation_id)

        logger.info(f"创建法律咨询：{consultation_id}, 用户：{user_id}, 类型：{consultation_type}")
        return consultation

    def _match_lawyer_for_consultation(self, consultation_type: LegalConsultationType) -> Optional[LawyerProfile]:
        """为咨询匹配律师。"""
        # 咨询类型到专业领域的映射
        type_to_practice = {
            LegalConsultationType.CONTRACT_REVIEW: "合同法",
            LegalConsultationType.DISPUTE_ADVICE: "仲裁",
            LegalConsultationType.COMPLIANCE_CHECK: "公司法",
            LegalConsultationType.IP_ADVICE: "知识产权",
            LegalConsultationType.TAX_ADVICE: "税法",
            LegalConsultationType.LABOR_LAW: "劳动法",
        }

        required_practice = type_to_practice.get(consultation_type)
        if not required_practice:
            return None

        # 查找匹配的律师
        for lawyer in self._lawyer_profiles.values():
            if lawyer.is_available_for_consultation and required_practice in lawyer.practice_areas:
                return lawyer

        return None

    def get_consultation(self, consultation_id: str) -> Optional[LegalConsultation]:
        """获取咨询详情。"""
        return self._legal_consultations.get(consultation_id)

    def submit_consultation_response(
        self,
        consultation_id: str,
        lawyer_response: str,
        lawyer_id: str,
    ) -> bool:
        """提交咨询回复。"""
        consultation = self._legal_consultations.get(consultation_id)
        if not consultation:
            raise ValueError(f"咨询不存在：{consultation_id}")

        consultation.lawyer_response = lawyer_response
        consultation.response_at = datetime.now()
        consultation.status = ConsultationStatus.COMPLETED

        logger.info(f"提交咨询回复：{consultation_id}, 律师：{lawyer_id}")
        return True

    def add_consultation_message(
        self,
        consultation_id: str,
        sender_id: str,
        sender_type: str,
        content: str,
        attachments: Optional[List[str]] = None,
    ) -> ConsultationMessage:
        """添加咨询消息。"""
        consultation = self._legal_consultations.get(consultation_id)
        if not consultation:
            raise ValueError(f"咨询不存在：{consultation_id}")

        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        message = ConsultationMessage(
            message_id=message_id,
            consultation_id=consultation_id,
            sender_id=sender_id,
            sender_type=sender_type,
            content=content,
            attachments=attachments or [],
            created_at=datetime.now(),
        )

        if consultation_id not in self._consultation_messages:
            self._consultation_messages[consultation_id] = []
        self._consultation_messages[consultation_id].append(message)

        return message

    def get_consultation_messages(
        self,
        consultation_id: str,
    ) -> List[ConsultationMessage]:
        """获取咨询消息列表。"""
        return self._consultation_messages.get(consultation_id, [])

    def get_user_consultations(
        self,
        user_id: str,
        status: Optional[ConsultationStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[LegalConsultation]:
        """获取用户的咨询列表。"""
        consultation_ids = self._user_consultations.get(user_id, [])
        consultations = [self._legal_consultations[cid] for cid in consultation_ids if cid in self._legal_consultations]

        if status:
            consultations = [c for c in consultations if c.status == status]

        return consultations[skip:skip + limit]

    # ========== 权益保护相关方法 ==========

    def create_complaint(
        self,
        complainant_id: str,
        complainant_type: str,
        respondent_id: str,
        respondent_type: str,
        violation_type: RightsViolationType,
        title: str,
        description: str,
        detailed_statement: str = "",
        evidence: Optional[List[Dict]] = None,
        demands: Optional[List[str]] = None,
        involved_amount: Optional[float] = None,
        related_task_id: Optional[str] = None,
        related_contract_id: Optional[str] = None,
    ) -> RightsComplaint:
        """创建权益投诉。"""
        complaint_id = f"complaint_{uuid.uuid4().hex[:12]}"

        complaint = RightsComplaint(
            complaint_id=complaint_id,
            complainant_id=complainant_id,
            complainant_type=complainant_type,
            respondent_id=respondent_id,
            respondent_type=respondent_type,
            violation_type=violation_type,
            title=title,
            description=description,
            detailed_statement=detailed_statement,
            evidence=evidence or [],
            demands=demands or [],
            involved_amount=involved_amount,
            currency="CNY",
            related_task_id=related_task_id,
            related_contract_id=related_contract_id,
            status=ComplaintStatus.UNDER_REVIEW,
            progress=10,
            current_stage="under_review",
            created_at=datetime.now(),
        )

        self._rights_complaints[complaint_id] = complaint

        # 更新用户投诉列表
        if complainant_id not in self._user_complaints:
            self._user_complaints[complainant_id] = []
        self._user_complaints[complainant_id].append(complaint_id)

        logger.info(f"创建权益投诉：{complaint_id}, 投诉人：{complainant_id}, 被投诉人：{respondent_id}")
        return complaint

    def get_complaint(self, complaint_id: str) -> Optional[RightsComplaint]:
        """获取投诉详情。"""
        return self._rights_complaints.get(complaint_id)

    def update_complaint_status(
        self,
        complaint_id: str,
        status: ComplaintStatus,
        progress: Optional[int] = None,
        current_stage: Optional[str] = None,
    ) -> bool:
        """更新投诉状态。"""
        complaint = self._rights_complaints.get(complaint_id)
        if not complaint:
            raise ValueError(f"投诉不存在：{complaint_id}")

        complaint.status = status
        if progress is not None:
            complaint.progress = progress
        if current_stage is not None:
            complaint.current_stage = current_stage

        logger.info(f"更新投诉状态：{complaint_id}, 状态：{status}, 进度：{progress}")
        return True

    def assign_mediator(
        self,
        complaint_id: str,
        mediator_id: str,
        mediator_name: str,
    ) -> bool:
        """指派调解员。"""
        complaint = self._rights_complaints.get(complaint_id)
        if not complaint:
            raise ValueError(f"投诉不存在：{complaint_id}")

        complaint.assigned_mediator_id = mediator_id
        complaint.assigned_mediator_name = mediator_name
        complaint.status = ComplaintStatus.MEDIATION
        complaint.progress = 50
        complaint.current_stage = "mediation"

        logger.info(f"指派调解员：{complaint_id}, 调解员：{mediator_name}")
        return True

    def resolve_complaint(
        self,
        complaint_id: str,
        resolution_summary: str,
        compensation_amount: Optional[float] = None,
        penalty_amount: Optional[float] = None,
    ) -> bool:
        """解决投诉。"""
        complaint = self._rights_complaints.get(complaint_id)
        if not complaint:
            raise ValueError(f"投诉不存在：{complaint_id}")

        complaint.resolution_summary = resolution_summary
        complaint.compensation_amount = compensation_amount
        complaint.penalty_amount = penalty_amount
        complaint.resolution_date = datetime.now()
        complaint.status = ComplaintStatus.RESOLVED
        complaint.progress = 100
        complaint.current_stage = "resolved"

        logger.info(f"解决投诉：{complaint_id}, 摘要：{resolution_summary}")
        return True

    def add_complaint_evidence(
        self,
        complaint_id: str,
        evidence_type: str,
        file_url: str,
        file_name: str,
        description: str = "",
        submitted_by: Optional[str] = None,
    ) -> ComplaintEvidence:
        """添加投诉证据。"""
        complaint = self._rights_complaints.get(complaint_id)
        if not complaint:
            raise ValueError(f"投诉不存在：{complaint_id}")

        evidence_id = f"evidence_{uuid.uuid4().hex[:8]}"
        evidence = ComplaintEvidence(
            evidence_id=evidence_id,
            complaint_id=complaint_id,
            evidence_type=evidence_type,
            file_url=file_url,
            file_name=file_name,
            file_size=None,
            description=description,
            submitted_by=submitted_by or complaint.complainant_id,
            submitted_at=datetime.now(),
        )

        if complaint_id not in self._complaint_evidence:
            self._complaint_evidence[complaint_id] = []
        self._complaint_evidence[complaint_id].append(evidence)

        # 更新投诉的证据列表
        complaint.evidence.append({
            "evidence_id": evidence_id,
            "evidence_type": evidence_type,
            "file_name": file_name,
            "description": description,
        })

        return evidence

    def get_user_complaints(
        self,
        user_id: str,
        status: Optional[ComplaintStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[RightsComplaint]:
        """获取用户的投诉列表。"""
        complaint_ids = self._user_complaints.get(user_id, [])
        complaints = [self._rights_complaints[cid] for cid in complaint_ids if cid in self._rights_complaints]

        if status:
            complaints = [c for c in complaints if c.status == status]

        return complaints[skip:skip + limit]

    # ========== 税务规划相关方法 ==========

    def calculate_tax(self, request: TaxCalculationRequest) -> TaxCalculationResult:
        """计算个人所得税。"""
        # 中国个人所得税税率表（综合所得）
        tax_brackets = [
            TaxBracket(min_amount=0, max_amount=36000, rate=0.03, quick_deduction=0),
            TaxBracket(min_amount=36000, max_amount=144000, rate=0.10, quick_deduction=2520),
            TaxBracket(min_amount=144000, max_amount=300000, rate=0.20, quick_deduction=16920),
            TaxBracket(min_amount=300000, max_amount=420000, rate=0.25, quick_deduction=31920),
            TaxBracket(min_amount=420000, max_amount=660000, rate=0.30, quick_deduction=52920),
            TaxBracket(min_amount=660000, max_amount=960000, rate=0.35, quick_deduction=85920),
            TaxBracket(min_amount=960000, max_amount=None, rate=0.45, quick_deduction=181920),
        ]

        # 计算应纳税所得额
        gross_income = request.income

        # 减除费用（基本减除费用 5000 元/月）
        basic_deduction = 5000 * 12  # 年度基本减除费用

        # 专项扣除（社保、公积金等）
        special_deductions = sum(d.get("amount", 0) for d in request.deductions if d.get("type") == "social_insurance")

        # 专项附加扣除
        additional_deductions = sum(d.get("amount", 0) for d in request.deductions if d.get("type") == "additional")

        taxable_income = max(0, gross_income - basic_deduction - special_deductions - additional_deductions)

        # 查找适用税率
        applicable_bracket = tax_brackets[0]
        for bracket in tax_brackets:
            if bracket.max_amount is None or taxable_income < bracket.max_amount:
                if taxable_income >= bracket.min_amount:
                    applicable_bracket = bracket
                    break

        # 计算应纳税额
        tax_amount = taxable_income * applicable_bracket.rate - applicable_bracket.quick_deduction
        tax_amount = max(0, tax_amount)  # 确保不为负数

        net_income = gross_income - tax_amount
        effective_tax_rate = tax_amount / gross_income if gross_income > 0 else 0

        result = TaxCalculationResult(
            gross_income=gross_income,
            taxable_income=taxable_income,
            tax_amount=tax_amount,
            net_income=net_income,
            effective_tax_rate=effective_tax_rate,
            tax_breakdown=[
                {
                    "tax_type": "individual_income_tax",
                    "taxable_income": taxable_income,
                    "rate": applicable_bracket.rate,
                    "quick_deduction": applicable_bracket.quick_deduction,
                    "tax_amount": tax_amount,
                }
            ],
            calculation_details={
                "basic_deduction": basic_deduction,
                "special_deductions": special_deductions,
                "additional_deductions": additional_deductions,
                "applicable_rate": applicable_bracket.rate,
            },
            deductions_applied=request.deductions,
        )

        return result

    def create_invoice(
        self,
        seller_name: str,
        seller_tax_id: str,
        seller_address: str,
        seller_phone: str,
        seller_bank_account: str,
        buyer_name: str,
        buyer_tax_id: str,
        buyer_address: str,
        buyer_phone: str,
        buyer_bank_account: str,
        item_name: str,
        amount: float,
        tax_rate: float = 0.03,
        invoice_type: str = "electronic",
        related_task_id: Optional[str] = None,
        related_contract_id: Optional[str] = None,
    ) -> Invoice:
        """创建发票。"""
        invoice_id = f"invoice_{uuid.uuid4().hex[:12]}"
        invoice_number = f"INV{datetime.now().strftime('%Y%m%d%H%M%S')}"
        invoice_code = "011002100111"  # 示例发票代码

        tax_amount = amount * tax_rate
        total_amount = amount + tax_amount

        invoice = Invoice(
            invoice_id=invoice_id,
            invoice_number=invoice_number,
            invoice_code=invoice_code,
            seller_name=seller_name,
            seller_tax_id=seller_tax_id,
            seller_address=seller_address,
            seller_phone=seller_phone,
            seller_bank_account=seller_bank_account,
            buyer_name=buyer_name,
            buyer_tax_id=buyer_tax_id,
            buyer_address=buyer_address,
            buyer_phone=buyer_phone,
            buyer_bank_account=buyer_bank_account,
            invoice_type=invoice_type,
            item_name=item_name,
            amount=amount,
            tax_amount=tax_amount,
            total_amount=total_amount,
            status="draft",
            related_task_id=related_task_id,
            related_contract_id=related_contract_id,
            issue_date=datetime.now(),
            created_at=datetime.now(),
        )

        self._invoices[invoice_id] = invoice

        # 更新用户发票列表
        if seller_name not in self._user_invoices:
            self._user_invoices[seller_name] = []
        self._user_invoices[seller_name].append(invoice_id)

        return invoice

    def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """获取发票详情。"""
        return self._invoices.get(invoice_id)

    def issue_invoice(self, invoice_id: str) -> bool:
        """开具发票。"""
        invoice = self._invoices.get(invoice_id)
        if not invoice:
            raise ValueError(f"发票不存在：{invoice_id}")

        invoice.status = "issued"

        logger.info(f"开具发票：{invoice_id}")
        return True

    def create_tax_filing(
        self,
        taxpayer_id: str,
        taxpayer_type: str,
        period_start: datetime,
        period_end: datetime,
        total_income: float,
        taxable_income: float,
        tax_payable: float,
    ) -> TaxFiling:
        """创建税务申报。"""
        filing_id = f"filing_{uuid.uuid4().hex[:12]}"

        filing = TaxFiling(
            filing_id=filing_id,
            taxpayer_id=taxpayer_id,
            taxpayer_type=taxpayer_type,
            period_start=period_start,
            period_end=period_end,
            total_income=total_income,
            taxable_income=taxable_income,
            tax_payable=tax_payable,
            tax_paid=0,
            tax_refund=0,
            status="draft",
            created_at=datetime.now(),
        )

        self._tax_filings[filing_id] = filing

        if taxpayer_id not in self._user_tax_filings:
            self._user_tax_filings[taxpayer_id] = []
        self._user_tax_filings[taxpayer_id].append(filing_id)

        return filing

    # ========== 合规检查相关方法 ==========

    def check_compliance(
        self,
        object_type: str,
        object_id: str,
        object_data: Dict,
    ) -> ComplianceCheckResult:
        """执行合规检查。"""
        check_id = f"check_{uuid.uuid4().hex[:12]}"

        issues = []
        recommendations = []
        regulations_referenced = []
        categories_checked = set()

        # 根据对象类型执行不同的检查
        if object_type == "task":
            issues, recommendations, regulations_referenced, categories_checked = self._check_task_compliance(object_data)
        elif object_type == "contract":
            issues, recommendations, regulations_referenced, categories_checked = self._check_contract_compliance(object_data)
        elif object_type == "user":
            issues, recommendations, regulations_referenced, categories_checked = self._check_user_compliance(object_data)

        # 确定整体风险等级
        risk_level_scores = {
            ComplianceRiskLevel.LOW: 1,
            ComplianceRiskLevel.MEDIUM: 2,
            ComplianceRiskLevel.HIGH: 3,
            ComplianceRiskLevel.CRITICAL: 4,
        }

        max_risk = ComplianceRiskLevel.LOW
        for issue in issues:
            issue_risk = issue.get("risk_level", "low")
            if risk_level_scores.get(issue_risk, 1) > risk_level_scores.get(max_risk, 1):
                max_risk = issue_risk

        overall_status = "compliant" if not issues else "non_compliant"
        if any(i.get("severity") == "medium" for i in issues):
            overall_status = "needs_review"

        result = ComplianceCheckResult(
            check_id=check_id,
            object_type=object_type,
            object_id=object_id,
            categories_checked=list(categories_checked),
            overall_status=overall_status,
            overall_risk_level=max_risk,
            issues=issues,
            recommendations=recommendations,
            regulations_referenced=regulations_referenced,
            summary=self._generate_compliance_summary(issues, recommendations),
            checked_at=datetime.now(),
            checked_by="system",
        )

        self._compliance_checks[check_id] = result

        key = f"{object_type}:{object_id}"
        if key not in self._object_checks:
            self._object_checks[key] = []
        self._object_checks[key].append(check_id)

        logger.info(f"执行合规检查：{object_type}:{object_id}, 结果：{overall_status}, 问题数：{len(issues)}")
        return result

    def _check_task_compliance(
        self,
        task_data: Dict,
    ) -> Tuple[List[Dict], List[str], List[str], set]:
        """检查任务合规性。"""
        issues = []
        recommendations = []
        regulations_referenced = []
        categories_checked = set()

        reward_amount = task_data.get("reward_amount", 0)
        work_hours = task_data.get("estimated_hours", 8)
        acceptance_criteria = task_data.get("acceptance_criteria", [])
        requires_personal_info = task_data.get("requires_personal_info", False)

        # 最低工资标准检查（假设最低时薪 20 元）
        min_wage = 20
        if reward_amount < min_wage * work_hours:
            issues.append({
                "category": ComplianceCategory.LABOR_LAW.value,
                "severity": "high",
                "risk_level": ComplianceRiskLevel.HIGH.value,
                "description": f"任务报酬 ({reward_amount}元) 低于最低工资标准 ({min_wage * work_hours}元)",
                "suggestion": f"建议将报酬调整为不低于 {min_wage * work_hours} 元",
                "regulation_reference": "《劳动法》第四十八条",
            })
            regulations_referenced.append("《劳动法》第四十八条")
        categories_checked.add(ComplianceCategory.LABOR_LAW)

        # 工作时间检查
        if work_hours > 8:
            issues.append({
                "category": ComplianceCategory.LABOR_LAW.value,
                "severity": "medium",
                "risk_level": ComplianceRiskLevel.MEDIUM.value,
                "description": f"任务预计工作时间 ({work_hours}小时) 超过法定每日工作时间",
                "suggestion": "建议将任务拆分为多个子任务，或明确说明加班安排",
                "regulation_reference": "《劳动法》第三十六条",
            })
            regulations_referenced.append("《劳动法》第三十六条")

        # 知识产权归属检查
        ip_ownership_defined = any("知识产权" in str(c) or "IP" in str(c) for c in acceptance_criteria)
        if not ip_ownership_defined:
            issues.append({
                "category": ComplianceCategory.IP_LAW.value,
                "severity": "medium",
                "risk_level": ComplianceRiskLevel.MEDIUM.value,
                "description": "任务验收标准未明确知识产权归属",
                "suggestion": "建议在验收标准中明确交付物的知识产权归属",
                "regulation_reference": "《著作权法》第十九条",
            })
            regulations_referenced.append("《著作权法》第十九条")
        categories_checked.add(ComplianceCategory.IP_LAW)

        # 个人信息保护检查
        if requires_personal_info:
            has_privacy_policy = task_data.get("has_privacy_policy", False)
            if not has_privacy_policy:
                issues.append({
                    "category": ComplianceCategory.DATA_PRIVACY.value,
                    "severity": "critical",
                    "risk_level": ComplianceRiskLevel.CRITICAL.value,
                    "description": "任务涉及个人信息收集但未提供隐私政策",
                    "suggestion": "必须提供隐私政策并获得用户同意后方可收集个人信息",
                    "regulation_reference": "《个人信息保护法》第十三条",
                })
                regulations_referenced.append("《个人信息保护法》第十三条")
            categories_checked.add(ComplianceCategory.DATA_PRIVACY)

        # 生成建议
        if not issues:
            recommendations.append("任务符合相关法律法规要求")

        return issues, recommendations, regulations_referenced, categories_checked

    def _check_contract_compliance(
        self,
        contract_data: Dict,
    ) -> Tuple[List[Dict], List[str], List[str], set]:
        """检查合同合规性。"""
        issues = []
        recommendations = []
        regulations_referenced = []
        categories_checked = set()

        content = contract_data.get("content", "")

        # 检查必要条款
        required_clauses = ["工作内容", "报酬", "期限", "争议解决"]
        for clause in required_clauses:
            if clause not in content:
                issues.append({
                    "category": ComplianceCategory.LABOR_LAW.value,
                    "severity": "medium",
                    "risk_level": ComplianceRiskLevel.MEDIUM.value,
                    "description": f"合同缺少必要条款：{clause}",
                    "suggestion": f"建议在合同中添加{clause}相关条款",
                    "regulation_reference": "《劳动合同法》第十七条",
                })
                regulations_referenced.append("《劳动合同法》第十七条")
        categories_checked.add(ComplianceCategory.LABOR_LAW)

        # 检查不公平条款
        unfair_terms = ["免除甲方责任", "乙方放弃权利", "无限期保密"]
        for term in unfair_terms:
            if term in content:
                issues.append({
                    "category": ComplianceCategory.LABOR_LAW.value,
                    "severity": "high",
                    "risk_level": ComplianceRiskLevel.HIGH.value,
                    "description": f"合同可能包含不公平条款：{term}",
                    "suggestion": "建议审查并修改可能不公平的条款",
                    "regulation_reference": "《民法典》第四百九十七条",
                })
                regulations_referenced.append("《民法典》第四百九十七条")

        return issues, recommendations, regulations_referenced, categories_checked

    def _check_user_compliance(
        self,
        user_data: Dict,
    ) -> Tuple[List[Dict], List[str], List[str], set]:
        """检查用户合规性。"""
        issues = []
        recommendations = []
        regulations_referenced = []
        categories_checked = set()

        # 检查实名认证
        if not user_data.get("is_verified", False):
            issues.append({
                "category": ComplianceCategory.ANTI_FRAUD.value,
                "severity": "medium",
                "risk_level": ComplianceRiskLevel.MEDIUM.value,
                "description": "用户未完成实名认证",
                "suggestion": "建议完成实名认证以提高账号安全性",
                "regulation_reference": "《网络安全法》第二十四条",
            })
            regulations_referenced.append("《网络安全法》第二十四条")
        categories_checked.add(ComplianceCategory.ANTI_FRAUD)

        return issues, recommendations, regulations_referenced, categories_checked

    def _generate_compliance_summary(
        self,
        issues: List[Dict],
        recommendations: List[str],
    ) -> str:
        """生成合规检查摘要。"""
        if not issues:
            return "合规检查通过，未发现违规问题。"

        critical_count = sum(1 for i in issues if i.get("severity") == "critical")
        high_count = sum(1 for i in issues if i.get("severity") == "high")
        medium_count = sum(1 for i in issues if i.get("severity") == "medium")
        low_count = sum(1 for i in issues if i.get("severity") == "low")

        summary_parts = [f"发现 {len(issues)} 个合规问题："]
        if critical_count:
            summary_parts.append(f"- 严重问题：{critical_count}个")
        if high_count:
            summary_parts.append(f"- 高风险问题：{high_count}个")
        if medium_count:
            summary_parts.append(f"- 中风险问题：{medium_count}个")
        if low_count:
            summary_parts.append(f"- 低风险问题：{low_count}个")

        return " ".join(summary_parts)

    def get_compliance_check(self, check_id: str) -> Optional[ComplianceCheckResult]:
        """获取合规检查结果。"""
        return self._compliance_checks.get(check_id)

    def get_object_compliance_checks(
        self,
        object_type: str,
        object_id: str,
    ) -> List[ComplianceCheckResult]:
        """获取对象的合规检查历史。"""
        key = f"{object_type}:{object_id}"
        check_ids = self._object_checks.get(key, [])
        return [self._compliance_checks[cid] for cid in check_ids if cid in self._compliance_checks]

    def get_lawyer_profile(self, lawyer_id: str) -> Optional[LawyerProfile]:
        """获取律师档案。"""
        return self._lawyer_profiles.get(lawyer_id)

    def list_lawyers(
        self,
        practice_area: Optional[str] = None,
        jurisdiction: Optional[str] = None,
    ) -> List[LawyerProfile]:
        """获取律师列表。"""
        lawyers = list(self._lawyer_profiles.values())

        if practice_area:
            lawyers = [l for l in lawyers if practice_area in l.practice_areas]
        if jurisdiction:
            lawyers = [l for l in lawyers if jurisdiction in l.served_jurisdictions]

        return lawyers

    def get_user_summary(self, user_id: str) -> LegalServicesSummary:
        """获取用户法律服务摘要。"""
        # 统计合同
        user_contract_ids = self._user_contracts.get(user_id, [])
        active_contracts = len([c for c in user_contract_ids if self._generated_contracts.get(c) and self._generated_contracts[c].status == "active"])

        # 统计咨询
        user_consultation_ids = self._user_consultations.get(user_id, [])
        active_consultations = len([c for c in user_consultation_ids if self._legal_consultations.get(c) and self._legal_consultations[c].status in [ConsultationStatus.PENDING, ConsultationStatus.IN_PROGRESS]])

        # 统计投诉
        user_complaint_ids = self._user_complaints.get(user_id, [])
        active_complaints = len([c for c in user_complaint_ids if self._rights_complaints.get(c) and self._rights_complaints[c].status in [ComplaintStatus.UNDER_REVIEW, ComplaintStatus.INVESTIGATING, ComplaintStatus.MEDIATION]])

        # 统计发票
        user_invoice_ids = self._user_invoices.get(user_id, [])
        pending_invoices = len([i for i in user_invoice_ids if self._invoices.get(i) and self._invoices[i].status == "draft"])

        # 统计合规问题
        all_checks = []
        for checks in self._object_checks.values():
            all_checks.extend(checks)
        compliance_issues = sum(1 for cid in all_checks if self._compliance_checks.get(cid) and self._compliance_checks[cid].overall_status == "non_compliant")

        return LegalServicesSummary(
            user_id=user_id,
            active_contracts=active_contracts,
            active_consultations=active_consultations,
            active_complaints=active_complaints,
            total_tax_paid=0.0,  # 实际应从数据库统计
            pending_invoices=pending_invoices,
            compliance_issues=compliance_issues,
        )


# 创建全局服务实例
legal_services_service = LegalServicesService()
