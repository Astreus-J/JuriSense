import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreatePolicyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


class PolicyVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    policy_id: uuid.UUID
    version_number: int
    status: str
    is_current: bool
    published_at: datetime | None
    published_by: uuid.UUID | None
    created_at: datetime


class CreatePolicyResponse(BaseModel):
    policy: PolicyResponse
    initial_version: PolicyVersionResponse


class CreateRuleRequest(BaseModel):
    """`yaml` is the rule document exactly as a policy author would write it
    (docs/03-domain/policy-engine.md's `rule:`/`when:`/`result:`/`severity`/
    `approver_role` grammar) -- never a pre-parsed JSON body, per ADR-004 ("Policy
    authors interact with YAML... not raw CEL/JSONLogic")."""

    yaml: str = Field(min_length=1)


class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    policy_version_id: uuid.UUID
    rule_key: str
    name: str
    when: dict[str, Any]
    result_status: str
    severity: str
    approver_role: str | None
    compiled_presence_cel: str
    compiled_condition_cel: str
    is_frozen: bool
    created_at: datetime
    updated_at: datetime


class SimulateRequest(BaseModel):
    contract_version_ids: list[uuid.UUID] = Field(min_length=1)


class RuleEvaluationResponse(BaseModel):
    rule_id: str
    rule_key: str
    rule_name: str
    outcome: str
    severity: str
    approver_role: str | None
    rationale: str


class AggregatePreviewResponse(BaseModel):
    status: str
    required_approver_roles: list[str]


class ContractSimulationResultResponse(BaseModel):
    contract_version_id: str
    rule_evaluations: list[RuleEvaluationResponse]
    aggregate: AggregatePreviewResponse


class SimulationResponse(BaseModel):
    policy_id: str
    policy_version_id: str
    version_number: int
    version_status: str
    contract_results: list[ContractSimulationResultResponse]
