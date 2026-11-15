import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { categoriesApi, ordersApi } from "@/services/api";
import { extractApiErrorMessage, getLocalizedCategoryName } from "@/lib/utils";

const schema = z.object({
  category: z.string().min(1, "requiredField"),
  title: z.string().min(3, "requiredField"),
  description: z.string().min(10, "requiredField"),
  budget: z.coerce.number().positive("positiveNumber"),
  capacity: z.coerce.number().int().min(1).max(50).default(1),
  budget_type: z.enum(["FIXED", "HOURLY", "NEGOTIABLE"]),
  work_type: z.enum(["ONSITE", "REMOTE", "HYBRID"]),
  location: z.string().min(2, "requiredField"),
  district: z.string().optional(),
  address: z.string().optional(),
  start_date: z.string().optional(),
  deadline: z.string().optional(),
  status: z.enum(["DRAFT", "PUBLISHED"]).default("PUBLISHED"),
});

type FormValues = z.infer<typeof schema>;

export function EmployerOrderFormPage() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [imageFile, setImageFile] = useState<File | null>(null);

  const catsQuery = useQuery({
    queryKey: ["categories", "all"],
    queryFn: () => categoriesApi.list({ page_size: 100 }),
  });

  const orderQuery = useQuery({
    queryKey: ["order", id],
    queryFn: () => ordersApi.detail(id!),
    enabled: isEdit,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<z.input<typeof schema>, unknown, FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      budget_type: "FIXED",
      work_type: "ONSITE",
      location: "Toshkent",
      status: "PUBLISHED",
      capacity: 1,
    },
  });

  useEffect(() => {
    if (orderQuery.data) {
      const o = orderQuery.data;
      reset({
        category: o.category,
        title: o.title,
        description: o.description,
        budget: Number(o.budget),
        capacity: o.capacity ?? 1,
        budget_type: o.budget_type,
        work_type: o.work_type,
        location: o.location,
        district: o.district || "",
        address: o.address || "",
        start_date: o.start_date || "",
        deadline: o.deadline || "",
        status: o.status === "DRAFT" ? "DRAFT" : "PUBLISHED",
      });
    }
  }, [orderQuery.data, reset]);

  const onSubmit = async (values: FormValues) => {
    try {
      const payload = {
        ...values,
        budget: values.budget.toFixed(2),
        start_date: values.start_date || null,
        deadline: values.deadline || null,
      };
      const saved = isEdit
        ? await ordersApi.update(id!, payload)
        : await ordersApi.create(payload);

      if (imageFile) {
        await ordersApi.uploadImage(saved.id, imageFile);
      }

      toast.success(t("common.save"));
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard", "employer"] });
      navigate(`/orders/${saved.id}`);
    } catch (err) {
      toast.error(extractApiErrorMessage(err));
    }
  };

  if (isEdit && orderQuery.isLoading) return <Skeleton className="h-96" />;

  return (
    <Card className="max-w-3xl">
      <CardHeader>
        <CardTitle>{isEdit ? t("employer.editOrderTitle") : t("employer.createOrderTitle")}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="ord-capacity">{t("employer.capacityLabel", { defaultValue: "Workers needed (1–50)" })}</Label>
            <Input id="ord-capacity" type="number" min={1} max={50} {...register("capacity")} />
            {errors.capacity && <p role="alert">{t("validation.positiveNumber")}</p>}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="ord-title">{t("employer.orderTitleLabel")}</Label>
            <Input id="ord-title" {...register("title")} />
            {errors.title && (
              <p className="text-xs text-destructive">{t("validation.requiredField")}</p>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="ord-cat">{t("marketplace.category")}</Label>
              <NativeSelect id="ord-cat" {...register("category")}>
                <option value="">-- {t("marketplace.category")} --</option>
                {(catsQuery.data?.results || []).map((c) => (
                  <option key={c.id} value={c.id}>
                    {getLocalizedCategoryName(c, i18n.language)}
                  </option>
                ))}
              </NativeSelect>
              {errors.category && (
                <p className="text-xs text-destructive">{t("validation.requiredField")}</p>
              )}
            </div>

            {!isEdit && (
              <div className="space-y-1.5">
                <Label htmlFor="ord-status">{t("common.status")}</Label>
                <NativeSelect id="ord-status" {...register("status")}>
                  <option value="PUBLISHED">{t("employer.publishImmediately")}</option>
                  <option value="DRAFT">{t("employer.saveAsDraft")}</option>
                </NativeSelect>
              </div>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="ord-desc">{t("employer.orderDescLabel")}</Label>
            <Textarea id="ord-desc" rows={4} {...register("description")} />
            {errors.description && (
              <p className="text-xs text-destructive">{t("validation.minChars", { min: 10 })}</p>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label htmlFor="ord-budget">{t("employer.budgetLabel")}</Label>
              <Input id="ord-budget" type="number" {...register("budget")} />
              {errors.budget && (
                <p className="text-xs text-destructive">{t("validation.positiveNumber")}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="ord-btype">{t("marketplace.budgetType")}</Label>
              <NativeSelect id="ord-btype" {...register("budget_type")}>
                <option value="FIXED">{t("statuses.FIXED")}</option>
                <option value="HOURLY">{t("statuses.HOURLY")}</option>
                <option value="NEGOTIABLE">{t("statuses.NEGOTIABLE")}</option>
              </NativeSelect>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="ord-wtype">{t("marketplace.workType")}</Label>
              <NativeSelect id="ord-wtype" {...register("work_type")}>
                <option value="ONSITE">{t("statuses.ONSITE")}</option>
                <option value="REMOTE">{t("statuses.REMOTE")}</option>
                <option value="HYBRID">{t("statuses.HYBRID")}</option>
              </NativeSelect>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label htmlFor="ord-loc">{t("marketplace.location")}</Label>
              <Input id="ord-loc" {...register("location")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ord-dist">{t("marketplace.district")}</Label>
              <Input id="ord-dist" {...register("district")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ord-addr">{t("employer.addressLabel")}</Label>
              <Input id="ord-addr" {...register("address")} />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label htmlFor="ord-start">{t("employer.startDateLabel")}</Label>
              <Input id="ord-start" type="date" {...register("start_date")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ord-dead">{t("employer.deadlineLabel")}</Label>
              <Input id="ord-dead" type="date" {...register("deadline")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ord-img">Image ({t("common.optional")})</Label>
              <Input
                id="ord-img"
                type="file"
                accept="image/*"
                onChange={(e) => setImageFile(e.target.files?.[0] || null)}
              />
            </div>
          </div>

          <div className="flex gap-2 pt-2">
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? t("common.loading") : t("common.save")}
            </Button>
            <Button type="button" variant="outline" onClick={() => navigate(-1)}>
              {t("common.cancel")}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
