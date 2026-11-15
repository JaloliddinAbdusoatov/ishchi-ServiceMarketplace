import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

export function Footer() {
  const { t } = useTranslation();

  return (
    <footer className="border-t bg-card py-10 mt-16">
      <div className="container grid gap-8 md:grid-cols-3">
        <div>
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold">
              I
            </div>
            <span className="text-lg font-bold">{t("brand.name")}</span>
          </div>
          <p className="mt-3 text-sm text-muted-foreground max-w-sm">{t("landing.footerDesc")}</p>
        </div>

        <div className="space-y-2 text-sm">
          <h4 className="font-semibold text-foreground">{t("nav.marketplace")}</h4>
          <ul className="space-y-1.5 text-muted-foreground">
            <li>
              <Link to="/marketplace?tab=orders" className="hover:text-primary">
                {t("nav.browseOrders")}
              </Link>
            </li>
            <li>
              <Link to="/marketplace?tab=workers" className="hover:text-primary">
                {t("nav.findWorkers")}
              </Link>
            </li>
            <li>
              <Link to="/payments" className="hover:text-primary">
                {t("nav.payments")}
              </Link>
            </li>
          </ul>
        </div>

        <div className="space-y-2 text-sm">
          <h4 className="font-semibold text-foreground">{t("brand.name")}</h4>
          <p className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} ISHCHI. {t("landing.footerRights")}
          </p>
        </div>
      </div>
    </footer>
  );
}
