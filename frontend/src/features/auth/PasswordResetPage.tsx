import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { ShieldAlert } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authApi } from "@/services/api";
import { extractApiErrorMessage } from "@/lib/utils";

export function PasswordResetPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2>(1);
  const [phone, setPhone] = useState("+998");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!/^\+998[0-9]{9}$/.test(phone)) {
      toast.error(t("validation.phoneInvalid"));
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.requestPasswordReset({ phone_number: phone });
      toast.success(res.message || t("auth.resetStep1Btn"));
      setStep(2);
    } catch (err) {
      toast.error(extractApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!/^[0-9]{6}$/.test(otp)) {
      toast.error(t("validation.otpFormat"));
      return;
    }
    if (newPassword.length < 8) {
      toast.error(t("validation.passwordMin"));
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.confirmPasswordReset({
        phone_number: phone,
        otp,
        new_password: newPassword,
      });
      toast.success(res.message || t("auth.resetStep2Btn"));
      navigate("/login");
    } catch (err) {
      toast.error(extractApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container flex min-h-[calc(100vh-12rem)] items-center justify-center py-10">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader>
          <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <CardTitle>{t("auth.resetTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          {step === 1 ? (
            <form onSubmit={handleRequest} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="reset-phone">{t("auth.phoneLabel")}</Label>
                <Input
                  id="reset-phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+998901234567"
                />
              </div>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? t("common.loading") : t("auth.resetStep1Btn")}
              </Button>
            </form>
          ) : (
            <form onSubmit={handleConfirm} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="reset-otp">{t("auth.otpCodeLabel")}</Label>
                <Input
                  id="reset-otp"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  maxLength={6}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="reset-pass">{t("auth.newPasswordLabel")}</Label>
                <Input
                  id="reset-pass"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? t("common.loading") : t("auth.resetStep2Btn")}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
