import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { profilesApi } from "@/services/api";
import { extractApiErrorMessage } from "@/lib/utils";
import type { EmployerType } from "@/types/api";

export function EmployerProfilePage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const profileQuery = useQuery({
    queryKey: ["my-employer-profile"],
    queryFn: profilesApi.getMyEmployerProfile,
  });

  const [employerType, setEmployerType] = useState<EmployerType>("INDIVIDUAL");
  const [fullName, setFullName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [bio, setBio] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [location, setLocation] = useState("");
  const [district, setDistrict] = useState("");
  const [address, setAddress] = useState("");

  useEffect(() => {
    if (profileQuery.data) {
      const p = profileQuery.data;
      setEmployerType(p.employer_type);
      setFullName(p.full_name || "");
      setCompanyName(p.company_name || "");
      setBio(p.bio || "");
      setPhone(p.phone_number || "");
      setEmail(p.email || "");
      setLocation(p.location || "");
      setDistrict(p.district || "");
      setAddress(p.address || "");
    }
  }, [profileQuery.data]);

  const mutation = useMutation({
    mutationFn: () =>
      profilesApi.updateMyEmployerProfile({
        employer_type: employerType,
        full_name: fullName,
        company_name: employerType === "COMPANY" ? companyName : "",
        bio,
        phone_number: phone,
        email: email || null,
        location,
        district,
        address,
      }),
    onSuccess: () => {
      toast.success(t("common.save"));
      void queryClient.invalidateQueries({ queryKey: ["my-employer-profile"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  if (profileQuery.isLoading) return <Skeleton className="h-80" />;
  if (profileQuery.isError) return <ErrorState onRetry={() => void profileQuery.refetch()} />;

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>{t("nav.profile")}</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            mutation.mutate();
          }}
          className="space-y-4"
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="ep-type">{t("auth.employerTypeLabel")}</Label>
              <NativeSelect
                id="ep-type"
                value={employerType}
                onChange={(e) => setEmployerType(e.target.value as EmployerType)}
              >
                <option value="INDIVIDUAL">{t("auth.employerIndividual")}</option>
                <option value="COMPANY">{t("auth.employerCompany")}</option>
              </NativeSelect>
            </div>
            {employerType === "COMPANY" && (
              <div className="space-y-1.5">
                <Label htmlFor="ep-comp">{t("auth.companyNameLabel")}</Label>
                <Input
                  id="ep-comp"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                />
              </div>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="ep-name">{t("auth.fullNameLabel")}</Label>
              <Input id="ep-name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ep-phone">{t("auth.phoneLabel")}</Label>
              <Input id="ep-phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label htmlFor="ep-loc">{t("auth.locationLabel")}</Label>
              <Input id="ep-loc" value={location} onChange={(e) => setLocation(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ep-dist">{t("auth.districtLabel")}</Label>
              <Input id="ep-dist" value={district} onChange={(e) => setDistrict(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ep-email">{t("auth.emailLabel")}</Label>
              <Input id="ep-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="ep-addr">{t("employer.addressLabel")}</Label>
            <Input id="ep-addr" value={address} onChange={(e) => setAddress(e.target.value)} />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="ep-bio">{t("worker.bioLabel")}</Label>
            <Textarea id="ep-bio" value={bio} onChange={(e) => setBio(e.target.value)} rows={3} />
          </div>

          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? t("common.loading") : t("common.save")}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
