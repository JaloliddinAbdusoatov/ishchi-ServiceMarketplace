import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { AlertTriangle, Briefcase, KeyRound, LogOut, ShieldAlert, UserCog } from "lucide-react";
import { LanguageSwitcher } from "@/components/navigation/LanguageSwitcher";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { authApi } from "@/services/api";
import { extractApiErrorMessage } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";
import type { EmployerType } from "@/types/api";

export function SettingsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, setUser, setActiveWorkspace, clearSession } = useAuthStore();
  const { darkMode, toggleDarkMode } = useUIStore();

  // Account info
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [email, setEmail] = useState(user?.email || "");

  // Password change
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  // Enable complementary role
  const [employerType, setEmployerType] = useState<EmployerType>("INDIVIDUAL");
  const [companyName, setCompanyName] = useState("");

  // Account deletion
  const [confirmCheckbox, setConfirmCheckbox] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteReason, setDeleteReason] = useState("");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const updateMeMutation = useMutation({
    mutationFn: () => authApi.updateMe({ full_name: fullName, email: email || null }),
    onSuccess: (updated) => {
      setUser(updated);
      toast.success(t("common.save"));
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const changePasswordMutation = useMutation({
    mutationFn: () =>
      authApi.changePassword({ old_password: oldPassword, new_password: newPassword }),
    onSuccess: () => {
      toast.success(t("auth.changePasswordTitle"));
      setOldPassword("");
      setNewPassword("");
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const logoutAllMutation = useMutation({
    mutationFn: () => authApi.logoutAll(),
    onSuccess: () => {
      clearSession();
      toast.success(t("auth.logoutAllBtn"));
      navigate("/login");
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const enableRoleMutation = useMutation({
    mutationFn: (role: "WORKER" | "EMPLOYER") =>
      authApi.enableRole(
        role === "EMPLOYER"
          ? { role, employer_type: employerType, company_name: companyName }
          : { role }
      ),
    onSuccess: (updated, role) => {
      setUser(updated);
      setActiveWorkspace(role);
      toast.success(
        role === "EMPLOYER" ? t("nav.enableEmployerRole") : t("nav.enableWorkerRole")
      );
      navigate(role === "EMPLOYER" ? "/employer" : "/worker");
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const deleteAccountMutation = useMutation({
    mutationFn: () =>
      authApi.deleteAccount({
        password: deletePassword,
        confirm: confirmCheckbox,
        reason: deleteReason,
      }),
    onSuccess: () => {
      setDeleteDialogOpen(false);
      clearSession();
      toast.success(t("settings.deleteBtn"));
      navigate("/");
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-bold">{t("settings.title")}</h1>

      {/* Account info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <UserCog className="h-5 w-5 text-primary" />
            {t("settings.accountInfoTitle")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              updateMeMutation.mutate();
            }}
            className="space-y-4"
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>{t("auth.phoneLabel")}</Label>
                <Input value={user?.phone_number || ""} disabled />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="settings-fullname">{t("auth.fullNameLabel")}</Label>
                <Input
                  id="settings-fullname"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="settings-email">{t("auth.emailLabel")}</Label>
              <Input
                id="settings-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <Button type="submit" disabled={updateMeMutation.isPending}>
              {updateMeMutation.isPending ? t("common.loading") : t("common.save")}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Dual Role enablement */}
      {user && user.role !== "ADMIN" && (!user.is_worker || !user.is_employer) && (
        <Card className="border-primary/30 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Briefcase className="h-5 w-5 text-primary" />
              {!user.is_employer ? t("nav.enableEmployerRole") : t("nav.enableWorkerRole")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {!user.is_employer ? (
              <>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label>{t("auth.employerTypeLabel")}</Label>
                    <NativeSelect
                      value={employerType}
                      onChange={(e) => setEmployerType(e.target.value as EmployerType)}
                    >
                      <option value="INDIVIDUAL">{t("auth.employerIndividual")}</option>
                      <option value="COMPANY">{t("auth.employerCompany")}</option>
                    </NativeSelect>
                  </div>
                  {employerType === "COMPANY" && (
                    <div className="space-y-1.5">
                      <Label>{t("auth.companyNameLabel")}</Label>
                      <Input
                        value={companyName}
                        onChange={(e) => setCompanyName(e.target.value)}
                      />
                    </div>
                  )}
                </div>
                <Button
                  onClick={() => enableRoleMutation.mutate("EMPLOYER")}
                  disabled={enableRoleMutation.isPending}
                >
                  {t("nav.enableEmployerRole")}
                </Button>
              </>
            ) : (
              <Button
                onClick={() => enableRoleMutation.mutate("WORKER")}
                disabled={enableRoleMutation.isPending}
              >
                {t("nav.enableWorkerRole")}
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Interface Preferences */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{t("settings.preferencesTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <Label>{t("common.language")}</Label>
            <LanguageSwitcher />
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="settings-darkmode">
              {darkMode ? t("common.darkMode") : t("common.lightMode")}
            </Label>
            <Switch
              id="settings-darkmode"
              checked={darkMode}
              onCheckedChange={() => toggleDarkMode()}
            />
          </div>
        </CardContent>
      </Card>

      {/* Security & Password */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <KeyRound className="h-5 w-5 text-primary" />
            {t("settings.securityTitle")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (newPassword.length < 8) {
                toast.error(t("validation.passwordMin"));
                return;
              }
              changePasswordMutation.mutate();
            }}
            className="space-y-3"
          >
            <h3 className="text-sm font-semibold">{t("auth.changePasswordTitle")}</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="old-pw">{t("auth.oldPasswordLabel")}</Label>
                <Input
                  id="old-pw"
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="new-pw">{t("auth.newPasswordLabel")}</Label>
                <Input
                  id="new-pw"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button type="submit" disabled={changePasswordMutation.isPending}>
                {t("auth.changePasswordBtn")}
              </Button>
              <Button
                type="button"
                variant="outline"
                className="gap-1.5"
                disabled={logoutAllMutation.isPending}
                onClick={() => logoutAllMutation.mutate()}
              >
                <LogOut className="h-4 w-4" />
                {t("auth.logoutAllBtn")}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Danger Zone: Account Anonymization & Deletion */}
      <Card className="border-destructive/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg text-destructive">
            <ShieldAlert className="h-5 w-5" />
            {t("settings.dangerZoneTitle")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-xs space-y-1.5">
            <p className="font-semibold flex items-center gap-1.5 text-amber-700 dark:text-amber-400">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {t("settings.anonymizationPolicyTitle")}
            </p>
            <p className="text-muted-foreground leading-relaxed">
              {t("settings.anonymizationPolicyText")}
            </p>
          </div>

          <label className="flex items-start gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 accent-destructive"
              checked={confirmCheckbox}
              onChange={(e) => setConfirmCheckbox(e.target.checked)}
            />
            <span>{t("settings.deleteConfirmCheckbox")}</span>
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="delete-pw">{t("auth.passwordLabel")}</Label>
              <Input
                id="delete-pw"
                type="password"
                value={deletePassword}
                onChange={(e) => setDeletePassword(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="delete-reason">{t("settings.deleteReasonLabel")}</Label>
              <Input
                id="delete-reason"
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
              />
            </div>
          </div>

          <Button
            variant="destructive"
            disabled={!confirmCheckbox || !deletePassword || deleteAccountMutation.isPending}
            onClick={() => setDeleteDialogOpen(true)}
          >
            {t("settings.deleteBtn")}
          </Button>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title={t("settings.dangerZoneTitle")}
        description={t("settings.anonymizationPolicyText")}
        confirmLabel={t("settings.deleteBtn")}
        variant="destructive"
        loading={deleteAccountMutation.isPending}
        onConfirm={() => deleteAccountMutation.mutate()}
      />
    </div>
  );
}
