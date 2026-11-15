import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { LogIn } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authApi } from "@/services/api";
import { useAuthStore } from "@/stores/authStore";
import { extractApiErrorMessage } from "@/lib/utils";

const schema = z.object({
  phone_number: z.string().regex(/^\+998[0-9]{9}$/, "phoneInvalid"),
  password: z.string().min(1, "requiredField"),
});

type FormValues = z.infer<typeof schema>;

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const setSession = useAuthStore((s) => s.setSession);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { phone_number: "+998", password: "" },
  });

  const onSubmit = async (values: FormValues) => {
    try {
      const res = await authApi.login(values);
      setSession(res.data.user, res.data.tokens);
      toast.success(res.message || t("auth.loginTitle"));
      const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname;
      if (from && from !== "/login") {
        navigate(from, { replace: true });
        return;
      }
      const u = res.data.user;
      if (u.role === "ADMIN") navigate("/admin", { replace: true });
      else if (u.role === "EMPLOYER" && u.is_employer) navigate("/employer", { replace: true });
      else navigate("/worker", { replace: true });
    } catch (err) {
      toast.error(extractApiErrorMessage(err));
    }
  };

  return (
    <div className="container flex min-h-[calc(100vh-12rem)] items-center justify-center py-10">
      <div className="w-full max-w-md">
        <Card className="shadow-lg">
          <CardHeader>
            <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <LogIn className="h-5 w-5" />
            </div>
            <CardTitle className="text-2xl">{t("auth.loginTitle")}</CardTitle>
            <CardDescription>{t("auth.loginSubtitle")}</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <div className="space-y-1.5">
                <Label htmlFor="login-phone">{t("auth.phoneLabel")}</Label>
                <Input
                  id="login-phone"
                  placeholder={t("auth.phonePlaceholder")}
                  {...register("phone_number")}
                />
                {errors.phone_number && (
                  <p className="text-xs text-destructive">
                    {t(`validation.${errors.phone_number.message}`, {
                      defaultValue: errors.phone_number.message || "",
                    })}
                  </p>
                )}
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="login-password">{t("auth.passwordLabel")}</Label>
                  <Link to="/reset-password" className="text-xs text-primary hover:underline">
                    {t("auth.forgotPassword")}
                  </Link>
                </div>
                <Input id="login-password" type="password" {...register("password")} />
                {errors.password && (
                  <p className="text-xs text-destructive">
                    {t(`validation.${errors.password.message}`, {
                      defaultValue: errors.password.message || "",
                    })}
                  </p>
                )}
              </div>

              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? t("common.loading") : t("nav.login")}
              </Button>
            </form>

            <p className="mt-4 text-center text-sm text-muted-foreground">
              {t("auth.noAccount")}{" "}
              <Link to="/register" className="font-medium text-primary hover:underline">
                {t("nav.register")}
              </Link>
            </p>

          </CardContent>
        </Card>
      </div>
    </div>
  );
}
