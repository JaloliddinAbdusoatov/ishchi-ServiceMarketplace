import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Plus, ShieldCheck, Trash2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { UserAvatar } from "@/components/ui/avatar";
import { ErrorState } from "@/components/shared/ErrorState";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { authApi, profilesApi } from "@/services/api";
import { extractApiErrorMessage } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";
import type { PricingType } from "@/types/api";

export function WorkerProfilePage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);

  const profileQuery = useQuery({
    queryKey: ["my-worker-profile"],
    queryFn: profilesApi.getMyWorkerProfile,
  });

  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [bio, setBio] = useState("");
  const [location, setLocation] = useState("");
  const [district, setDistrict] = useState("");
  const [skillsText, setSkillsText] = useState("");
  const [expYears, setExpYears] = useState("0");
  const [expDesc, setExpDesc] = useState("");
  const [pricingType, setPricingType] = useState<PricingType>("FIXED");
  const [hourlyRate, setHourlyRate] = useState("");
  const [fixedRate, setFixedRate] = useState("");
  const [isAvailable, setIsAvailable] = useState(true);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [verifyNotes, setVerifyNotes] = useState("");

  // Portfolio creation state
  const [pTitle, setPTitle] = useState("");
  const [pDesc, setPDesc] = useState("");
  const [pYear, setPYear] = useState("2025");
  const [pUrl, setPUrl] = useState("");

  useEffect(() => {
    if (profileQuery.data) {
      const p = profileQuery.data;
      setFullName(p.full_name || "");
      setPhone(p.phone_number || "");
      setBio(p.bio || "");
      setLocation(p.location || "");
      setDistrict(p.district || "");
      setSkillsText((p.skills || []).join(", "));
      setExpYears(String(p.experience_years ?? 0));
      setExpDesc(p.experience_description || "");
      setPricingType(p.pricing_type || "FIXED");
      setHourlyRate(p.hourly_rate || "");
      setFixedRate(p.fixed_rate_from || "");
      setIsAvailable(Boolean(p.is_available));
    }
  }, [profileQuery.data]);

  const updateMutation = useMutation({
    mutationFn: async () => {
      const skills = skillsText
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      if (photoFile) {
        const fd = new FormData();
        fd.append("full_name", fullName);
        fd.append("phone_number", phone);
        fd.append("bio", bio);
        fd.append("location", location);
        fd.append("district", district);
        fd.append("skills", JSON.stringify(skills));
        fd.append("experience_years", expYears || "0");
        fd.append("experience_description", expDesc);
        fd.append("pricing_type", pricingType);
        if (hourlyRate) fd.append("hourly_rate", hourlyRate);
        if (fixedRate) fd.append("fixed_rate_from", fixedRate);
        fd.append("is_available", String(isAvailable));
        fd.append("photo", photoFile);
        return profilesApi.updateMyWorkerProfile(fd);
      }

      return profilesApi.updateMyWorkerProfile({
        full_name: fullName,
        phone_number: phone,
        bio,
        location,
        district,
        skills,
        experience_years: Number(expYears) || 0,
        experience_description: expDesc,
        pricing_type: pricingType,
        hourly_rate: hourlyRate ? hourlyRate : null,
        fixed_rate_from: fixedRate ? fixedRate : null,
        is_available: isAvailable,
      });
    },
    onSuccess: async () => {
      toast.success(t("common.save"));
      setPhotoFile(null);
      void queryClient.invalidateQueries({ queryKey: ["my-worker-profile"] });
      const me = await authApi.me();
      setUser(me);
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const verifyReqMutation = useMutation({
    mutationFn: () => profilesApi.requestWorkerVerification(verifyNotes),
    onSuccess: async () => {
      toast.success(t("worker.requestVerificationBtn"));
      void queryClient.invalidateQueries({ queryKey: ["my-worker-profile"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard", "worker"] });
      const me = await authApi.me();
      setUser(me);
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const addPortfolioMutation = useMutation({
    mutationFn: () =>
      profilesApi.createPortfolioItem({
        title: pTitle,
        description: pDesc,
        completed_year: pYear ? Number(pYear) : null,
        project_url: pUrl,
      }),
    onSuccess: () => {
      toast.success(t("worker.addPortfolioBtn"));
      setPTitle("");
      setPDesc("");
      setPUrl("");
      void queryClient.invalidateQueries({ queryKey: ["my-worker-profile"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const delPortfolioMutation = useMutation({
    mutationFn: (itemId: string) => profilesApi.deletePortfolioItem(itemId),
    onSuccess: () => {
      toast.success(t("common.delete"));
      void queryClient.invalidateQueries({ queryKey: ["my-worker-profile"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  if (profileQuery.isLoading) return <Skeleton className="h-96" />;
  if (profileQuery.isError || !profileQuery.data) {
    return <ErrorState onRetry={() => void profileQuery.refetch()} />;
  }

  const profile = profileQuery.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <UserAvatar src={profile.photo} name={profile.full_name} className="h-14 w-14" />
          <div>
            <h1 className="text-2xl font-bold">{t("nav.profile")}</h1>
            <div className="mt-1 flex items-center gap-2">
              <StatusBadge status={profile.verification_status} showIcon />
              {profile.verification_notes && (
                <span className="text-xs text-muted-foreground">{profile.verification_notes}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Optional Verification Request Card */}
      {!profile.is_verified && (
        <Card className="border-blue-200/80 bg-blue-50/30 dark:border-blue-900/50 dark:bg-blue-950/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldCheck className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              {t("worker.requestVerificationBtn")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {profile.verification_status === "PENDING"
                ? t("worker.verificationBannerPending")
                : t("worker.verificationBannerUnverified")}
            </p>
            {profile.verification_status !== "PENDING" && (
              <div className="flex flex-col gap-3 sm:flex-row">
                <Input
                  value={verifyNotes}
                  onChange={(e) => setVerifyNotes(e.target.value)}
                  placeholder={t("worker.verificationNotesLabel")}
                />
                <Button
                  onClick={() => verifyReqMutation.mutate()}
                  disabled={verifyReqMutation.isPending}
                  className="shrink-0"
                >
                  {t("worker.requestVerificationBtn")}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Profile Form */}
      <Card>
        <CardHeader>
          <CardTitle>{t("common.edit")}</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              updateMutation.mutate();
            }}
            className="space-y-4"
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="wp-name">{t("auth.fullNameLabel")}</Label>
                <Input
                  id="wp-name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="wp-phone">{t("auth.phoneLabel")}</Label>
                <Input
                  id="wp-phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="wp-loc">{t("auth.locationLabel")}</Label>
                <Input
                  id="wp-loc"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="wp-dist">{t("auth.districtLabel")}</Label>
                <Input
                  id="wp-dist"
                  value={district}
                  onChange={(e) => setDistrict(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="wp-bio">{t("worker.bioLabel")}</Label>
              <Textarea id="wp-bio" value={bio} onChange={(e) => setBio(e.target.value)} rows={3} />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="wp-skills">{t("worker.skillsLabel")}</Label>
                <Input
                  id="wp-skills"
                  value={skillsText}
                  onChange={(e) => setSkillsText(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="wp-exp">{t("worker.experienceYearsLabel")}</Label>
                <Input
                  id="wp-exp"
                  type="number"
                  min={0}
                  max={70}
                  value={expYears}
                  onChange={(e) => setExpYears(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="wp-exp-desc">{t("worker.experienceDescLabel")}</Label>
              <Textarea
                id="wp-exp-desc"
                value={expDesc}
                onChange={(e) => setExpDesc(e.target.value)}
                rows={2}
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="wp-ptype">{t("marketplace.budgetType")}</Label>
                <NativeSelect
                  id="wp-ptype"
                  value={pricingType}
                  onChange={(e) => setPricingType(e.target.value as PricingType)}
                >
                  <option value="FIXED">{t("statuses.FIXED")}</option>
                  <option value="HOURLY">{t("statuses.HOURLY")}</option>
                  <option value="NEGOTIABLE">{t("statuses.NEGOTIABLE")}</option>
                </NativeSelect>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="wp-hrate">{t("worker.hourlyRateLabel")}</Label>
                <Input
                  id="wp-hrate"
                  type="number"
                  value={hourlyRate}
                  onChange={(e) => setHourlyRate(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="wp-frate">{t("worker.fixedRateLabel")}</Label>
                <Input
                  id="wp-frate"
                  type="number"
                  value={fixedRate}
                  onChange={(e) => setFixedRate(e.target.value)}
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 items-center pt-2">
              <div className="space-y-1.5">
                <Label htmlFor="wp-photo" className="inline-flex items-center gap-2">
                  <Upload className="h-4 w-4" />
                  {t("worker.photoLabel")}
                </Label>
                <Input
                  id="wp-photo"
                  type="file"
                  accept="image/*"
                  onChange={(e) => setPhotoFile(e.target.files?.[0] || null)}
                />
              </div>

              <div className="flex items-center justify-between rounded-lg border p-3">
                <Label htmlFor="wp-avail">{t("worker.availabilityLabel")}</Label>
                <Switch
                  id="wp-avail"
                  checked={isAvailable}
                  onCheckedChange={setIsAvailable}
                />
              </div>
            </div>

            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending ? t("common.loading") : t("common.save")}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Portfolio Management */}
      <Card>
        <CardHeader>
          <CardTitle>{t("worker.portfolioTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!pTitle.trim()) return;
              addPortfolioMutation.mutate();
            }}
            className="grid gap-3 rounded-xl border bg-muted/30 p-4 sm:grid-cols-3"
          >
            <Input
              value={pTitle}
              onChange={(e) => setPTitle(e.target.value)}
              placeholder={t("worker.portfolioTitleLabel")}
              required
            />
            <Input
              value={pYear}
              onChange={(e) => setPYear(e.target.value)}
              type="number"
              placeholder={t("worker.portfolioYearLabel")}
            />
            <Input
              value={pUrl}
              onChange={(e) => setPUrl(e.target.value)}
              placeholder={t("worker.portfolioUrlLabel")}
            />
            <Textarea
              className="sm:col-span-2"
              value={pDesc}
              onChange={(e) => setPDesc(e.target.value)}
              placeholder={t("employer.orderDescLabel")}
              rows={2}
            />
            <Button type="submit" disabled={addPortfolioMutation.isPending} className="self-end">
              <Plus className="h-4 w-4" />
              {t("worker.addPortfolioBtn")}
            </Button>
          </form>

          {profile.portfolio_items.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("common.noData")}</p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {profile.portfolio_items.map((item) => (
                <div key={item.id} className="flex items-start justify-between rounded-xl border p-4">
                  <div>
                    <h4 className="font-semibold text-sm">{item.title}</h4>
                    <p className="mt-1 text-xs text-muted-foreground">{item.description}</p>
                    {item.completed_year && (
                      <p className="mt-1 text-[11px] text-muted-foreground">{item.completed_year}</p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => delPortfolioMutation.mutate(item.id)}
                    aria-label={t("common.delete")}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
