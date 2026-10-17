import { ComingSoon } from "@/components/shared/ComingSoon";
import { getI18n, pageTitle } from "@/lib/i18n/server";
import { NAV_ITEMS } from "@/lib/navigation/modules";

export const generateMetadata = pageTitle("meta.integrations");

export default async function IntegrationsPage() {
  const { t } = await getI18n();
  return (
    <ComingSoon
      icon={NAV_ITEMS.integrations.icon}
      title={t("nav.integrations")}
      description={t("nav.integrationsDescription")}
    />
  );
}
