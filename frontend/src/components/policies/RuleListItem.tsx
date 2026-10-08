"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { RuleForm } from "./RuleForm";
import { RuleResultBadge } from "./RuleResultBadge";
import { SeverityBadge } from "./SeverityBadge";
import { buildRuleYamlDraft } from "@/lib/policies/ruleYaml";
import { describeWhen } from "@/lib/policies/types";
import type { Rule } from "@/lib/policies/types";

interface RuleListItemProps {
  policyId: string;
  versionId: string;
  rule: Rule;
  /** Whether this rule can be edited at all — `canUpdate` AND the owning version is still
   * a draft (BR-POL-001: a published version's rules are frozen). */
  canEdit: boolean;
}

/**
 * One Rule, rendered as a read-only card by default with an inline "Edit rule" toggle that
 * swaps it for `RuleForm` pre-filled via `buildRuleYamlDraft` — a Client Component (not a
 * Server Component passing a raw icon down, per `SupplierStatusBadge`'s note on that
 * boundary) specifically because the edit toggle is local, ephemeral UI state that has no
 * business being a URL param or a server round-trip.
 */
export function RuleListItem({ policyId, versionId, rule, canEdit }: RuleListItemProps) {
  const [editing, setEditing] = useState(false);

  if (editing) {
    return (
      <RuleForm
        policyId={policyId}
        versionId={versionId}
        mode="edit"
        ruleId={rule.id}
        initialYaml={buildRuleYamlDraft(rule)}
        onCancel={() => setEditing(false)}
        onSuccess={() => setEditing(false)}
      />
    );
  }

  return (
    <li className="space-y-3 rounded-xl border border-border bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-xs text-foreground-muted">{rule.ruleKey}</p>
          <h3 className="text-sm font-semibold text-foreground">{rule.name}</h3>
        </div>
        <div className="flex items-center gap-2">
          <RuleResultBadge status={rule.resultStatus} />
          <SeverityBadge severity={rule.severity} />
        </div>
      </div>

      <p className="rounded-md bg-surface-muted px-3 py-2 font-mono text-xs text-foreground-muted">
        WHEN {describeWhen(rule.when)}
      </p>

      {rule.approverRole && (
        <p className="text-xs text-foreground-muted">
          Required approver role: <span className="font-medium text-foreground">{rule.approverRole}</span>
        </p>
      )}

      {canEdit && (
        <div className="flex justify-end">
          <Button type="button" variant="secondary" onClick={() => setEditing(true)}>
            Edit rule
          </Button>
        </div>
      )}
    </li>
  );
}
