import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { UserPlus } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { authApi } from "@/services/api";
import { useAuthStore } from "@/stores/authStore";
import { extractApiErrorMessage } from "@/lib/utils";

const schema = z
  .object({
    phone_number: z.string().regex(/^\+998[0-9]{9}$/, "phoneInvalid"),
    full_name: z.string().trim().min(2, "requiredField"),
    email: z.string().trim().email("emailInvalid").optional().or(z.literal("")),
    password: z.string().min(8, "passwordMin"),
    confirm_password: z.string(),
    role: z.enum(["WORKER", "EMPLOYER"]),
    employer_type: z.enum(["INDIVIDUAL", "COMPANY"]).default("INDIVIDUAL"),
    company_name: z.string().optional(),
    location: z.string().optional(),
    district: z.string().optional(),
    dual_role: z.boolean().default(false),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "passwordMatch",
    path: ["confirm_password"],
  });

type FormValues = z.infer<typeof schema>;

export function RegisterPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const setSession = useAuthStore((s) => s.setSession);

  const {
    register,
    watch,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.input<typeof schema>, unknown, FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      phone_number: "+998",
      role: "WORKER",
      employer_type: "INDIVIDUAL",
      dual_role: false,
      location: "Toshkent",
    },
  });

  const role = watch("role");
  const employerType = watch("employer_type");
  const dualRole = watch("dual_role");

  const onSubmit = async (values: FormValues) => {
    try {
      const res = await authApi.register({
        phone_number: values.phone_number,
        password: values.password,
        full_name: values.full_name,
        role: values.role,
        email: values.email || null,
        enable_worker: values.dual_role ? true : values.role === "WORKER",
        enable_employer: values.dual_role ? true : values.role === "EMPLOYER",
        employer_type: values.employer_type,
        company_name: values.company_name || "",
        location: values.location || "",
        district: values.district || "",
      });
      setSession(res.data.user, res.data.tokens);
      toast.success(t("auth.registerSuccess"));
      navigate(res.data.user.role === "EMPLOYER" ? "/employer" : "/worker", { replace: true });
    } catch (err) {
      toast.error(extractApiErrorMessage(err));
    }
  };

  return (
    <div className="container flex min-h-[calc(100vh-10rem)] items-center justify-center py-10">
      <div className="w-full max-w-lg">
        <Card className="shadow-lg">
          <CardHeader>
            <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <UserPlus className="h-5 w-5" />
            </div>
            <CardTitle className="text-2xl">{t("auth.registerTitle")}</CardTitle>
            <CardDescription>{t("auth.registerSubtitle")}</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="reg-name">{t("auth.fullNameLabel")}</Label>
                  <Input id="reg-name" {...register("full_name")} />
                  {errors.full_name && (
                    <p className="text-xs text-destructive">
                      {t(`validation.${errors.full_name.message}`, {
                        defaultValue: errors.full_name.message || "",
                      })}
                    </p>
                  )}
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="reg-phone">{t("auth.phoneLabel")}</Label>
                  <Input
                    id="reg-phone"
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
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="reg-role">{t("auth.roleLabel")}</Label>
                  <NativeSelect id="reg-role" {...register("role")}>
                    <option value="WORKER">{t("auth.roleWorker")}</option>
                    <option value="EMPLOYER">{t("auth.roleEmployer")}</option>
                  </NativeSelect>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="reg-email">
                    {t("auth.emailLabel")} ({t("common.optional")})
                  </Label>
                  <Input id="reg-email" type="email" autoComplete="email"
                    aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? "reg-email-error" : undefined}
                    {...register("email")} />
                  {errors.email && (
                    <p id="reg-email-error" role="alert" className="text-xs text-destructive">
                      {t("validation.emailInvalid")}
                    </p>
                  )}
                </div>
              </div>

              {(role === "EMPLOYER" || dualRole) && (
                <div className="grid gap-4 sm:grid-cols-2 rounded-lg border bg-muted/40 p-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="reg-emp-type">{t("auth.employerTypeLabel")}</Label>
                    <NativeSelect id="reg-emp-type" {...register("employer_type")}>
                      <option value="INDIVIDUAL">{t("auth.employerIndividual")}</option>
                      <option value="COMPANY">{t("auth.employerCompany")}</option>
                    </NativeSelect>
                  </div>
                  {employerType === "COMPANY" && (
                    <div className="space-y-1.5">
                      <Label htmlFor="reg-company">{t("auth.companyNameLabel")}</Label>
                      <Input id="reg-company" {...register("company_name")} />
                    </div>
                  )}
                </div>
              )}

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="reg-location">{t("auth.locationLabel")}</Label>
                  <Input id="reg-location" {...register("location")} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="reg-district">{t("auth.districtLabel")}</Label>
                  <Input id="reg-district" {...register("district")} />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="reg-pass">{t("auth.passwordLabel")}</Label>
                  <Input id="reg-pass" type="password" {...register("password")} />
                  {errors.password && (
                    <p className="text-xs text-destructive">
                      {t(`validation.${errors.password.message}`, {
                        defaultValue: errors.password.message || "",
                      })}
                    </p>
                  )}
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="reg-pass2">{t("auth.confirmPasswordLabel")}</Label>
                  <Input id="reg-pass2" type="password" {...register("confirm_password")} />
                  {errors.confirm_password && (
                    <p className="text-xs text-destructive">
                      {t(`validation.${errors.confirm_password.message}`, {
                        defaultValue: errors.confirm_password.message || "",
                      })}
                    </p>
                  )}
                </div>
              </div>

              <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-input"
                  {...register("dual_role")}
                />
                <span>{t("auth.dualRoleCheckbox")}</span>
              </label>

              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? t("common.loading") : t("nav.register")}
              </Button>
            </form>

            <p className="mt-4 text-center text-sm text-muted-foreground">
              {t("auth.hasAccount")}{" "}
              <Link to="/login" className="font-medium text-primary hover:underline">
                {t("nav.login")}
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
