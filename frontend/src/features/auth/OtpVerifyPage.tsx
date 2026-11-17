import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { KeyRound } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authApi } from "@/services/api";
import { useAuthStore } from "@/stores/authStore";
import { extractApiErrorMessage } from "@/lib/utils";

export function OtpVerifyPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, setUser } = useAuthStore();

  const phone = user?.phone_number || "+998";
  const [otp, setOtp] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!user) navigate("/login", { replace: true });
  }, [user, navigate]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => setCooldown((c) => Math.max(0, c - 1)), 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!/^[0-9]{6}$/.test(otp)) {
      toast.error(t("validation.otpFormat"));
      return;
    }
    setSubmitting(true);
    try {
      const res = await authApi.verifyOtp({ phone_number: phone, otp });
      setUser(res.data.user);
      toast.success(res.message || t("auth.otpTitle"));
      const u = res.data.user;
      if (u.role === "ADMIN") navigate("/admin");
      else if (u.is_employer && u.role === "EMPLOYER") navigate("/employer");
      else navigate("/worker");
    } catch (err) {
      toast.error(extractApiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    try {
      const res = await authApi.resendOtp({ phone_number: phone, purpose: "VERIFY_PHONE" });
      setCooldown(res.data.cooldown_seconds || 60);
      toast.success(res.message || t("auth.resendOtpBtn"));
    } catch (err) {
      toast.error(extractApiErrorMessage(err));
    }
  };

  return (
    <div className="container flex min-h-[calc(100vh-12rem)] items-center justify-center py-10">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader>
          <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <KeyRound className="h-5 w-5" />
          </div>
          <CardTitle>{t("auth.otpTitle")}</CardTitle>
          <CardDescription>{t("auth.otpSubtitle")}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleVerify} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="otp-phone">{t("auth.phoneLabel")}</Label>
              <Input id="otp-phone" value={phone} readOnly />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="otp-code">{t("auth.otpCodeLabel")}</Label>
              <Input
                id="otp-code"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                maxLength={6}
                inputMode="numeric"
                autoComplete="one-time-code"
              />
            </div>

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? t("common.loading") : t("auth.verifyOtpBtn")}
            </Button>

            <Button
              type="button"
              variant="outline"
              className="w-full"
              disabled={cooldown > 0}
              onClick={handleResend}
            >
              {t("auth.resendOtpBtn")} {cooldown > 0 ? `(${cooldown}s)` : ""}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
