"use client";

import { useState } from "react";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { useI18n } from "@/lib/i18n/client";
import { RuleForm } from "./RuleForm";

interface AddRuleControlProps {
  policyId: string;
  versionId: string;
}

/**
 * Collapsed by default (progressive disclosure) — a dedicated page section for authoring
 * one rule at a time, not a modal, since the YAML textarea benefits from full page width
 * and this screen has no competing content below the rule list. Rendered next to the
 * "Rules" heading, in a `flex-wrap` row (see the caller) — `basis-full` forces the
 * expanded form onto its own line instead of being squeezed into a flex item next to the
 * heading.
 */
export function AddRuleControl({ policyId, versionId }: AddRuleControlProps) {
  const { t } = useI18n();
  const [showForm, setShowForm] = useState(false);

  if (showForm) {
    return (
      <div className="basis-full">
        <RuleForm
          policyId={policyId}
          versionId={versionId}
          mode="create"
          onCancel={() => setShowForm(false)}
          onSuccess={() => setShowForm(false)}
        />
      </div>
    );
  }

  return (
    <Button type="button" variant="secondary" onClick={() => setShowForm(true)}>
      <Plus className="size-4" aria-hidden="true" />
      {t("policies.rule.add")}
    </Button>
  );
}
