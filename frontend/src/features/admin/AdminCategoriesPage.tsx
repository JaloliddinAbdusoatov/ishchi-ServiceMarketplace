import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Pencil, Plus, PowerOff, Tag, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { categoriesApi } from "@/services/api";
import { extractApiErrorMessage, getLocalizedCategoryName } from "@/lib/utils";
import type { Category } from "@/types/api";

interface CategoryFormState {
  parent: string;
  slug: string;
  name: string;
  name_uz: string;
  name_ru: string;
  name_en: string;
  description: string;
  display_order: number;
  is_active: boolean;
}

const emptyForm: CategoryFormState = {
  parent: "",
  slug: "",
  name: "",
  name_uz: "",
  name_ru: "",
  name_en: "",
  description: "",
  display_order: 0,
  is_active: true,
};

export function AdminCategoriesPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<CategoryFormState>(emptyForm);
  const [deactivateTarget, setDeactivateTarget] = useState<Category | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Category | null>(null);

  const query = useQuery({
    queryKey: ["categories", "admin-list"],
    queryFn: () => categoriesApi.list({ page_size: 100 }),
  });

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload = {
        ...form,
        parent: form.parent || null,
        display_order: Number(form.display_order) || 0,
      };
      return editingId
        ? categoriesApi.update(editingId, payload)
        : categoriesApi.create(payload);
    },
    onSuccess: () => {
      toast.success(t("common.save"));
      setModalOpen(false);
      setEditingId(null);
      setForm(emptyForm);
      void queryClient.invalidateQueries({ queryKey: ["categories"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => categoriesApi.deactivate(id),
    onSuccess: () => {
      toast.success(t("admin.deactivateCategory"));
      setDeactivateTarget(null);
      void queryClient.invalidateQueries({ queryKey: ["categories"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => categoriesApi.remove(id),
    onSuccess: () => {
      toast.success(t("common.delete"));
      setDeleteTarget(null);
      void queryClient.invalidateQueries({ queryKey: ["categories"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (cat: Category) => {
    setEditingId(cat.id);
    setForm({
      parent: cat.parent || "",
      slug: cat.slug,
      name: cat.name,
      name_uz: cat.name_uz,
      name_ru: cat.name_ru,
      name_en: cat.name_en,
      description: cat.description || "",
      display_order: cat.display_order || 0,
      is_active: cat.is_active,
    });
    setModalOpen(true);
  };

  const items = query.data?.results || [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{t("nav.adminCategories")}</h1>
        <Button onClick={openCreate} className="gap-1.5">
          <Plus className="h-4 w-4" />
          {t("admin.createCategory")}
        </Button>
      </div>

      {query.isLoading ? (
        <Skeleton className="h-64" />
      ) : query.isError ? (
        <ErrorState onRetry={() => void query.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState icon={<Tag className="h-6 w-6" />} title={t("common.noData")} />
      ) : (
        <div className="space-y-2.5">
          {items.map((cat) => (
            <Card
              key={cat.id}
              className="p-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold">
                    {getLocalizedCategoryName(cat, i18n.language)}
                  </span>
                  <Badge variant="outline">{cat.slug}</Badge>
                  <Badge variant={cat.is_active ? "success" : "secondary"}>
                    {cat.is_active ? t("statuses.ACTIVE") : "INACTIVE"}
                  </Badge>
                  {cat.parent_name && <Badge variant="secondary">Parent: {cat.parent_name}</Badge>}
                </div>
                <p className="text-xs text-muted-foreground">
                  UZ: {cat.name_uz} • RU: {cat.name_ru} • EN: {cat.name_en}
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" className="gap-1" onClick={() => openEdit(cat)}>
                  <Pencil className="h-3.5 w-3.5" />
                  {t("common.edit")}
                </Button>
                {cat.is_active && (
                  <Button
                    variant="secondary"
                    size="sm"
                    className="gap-1"
                    onClick={() => setDeactivateTarget(cat)}
                  >
                    <PowerOff className="h-3.5 w-3.5" />
                    {t("admin.deactivateCategory")}
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setDeleteTarget(cat)}
                  aria-label={t("common.delete")}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingId ? t("admin.editCategory") : t("admin.createCategory")}
            </DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              saveMutation.mutate();
            }}
            className="space-y-3"
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <Label>Parent</Label>
                <NativeSelect
                  value={form.parent}
                  onChange={(e) => setForm({ ...form, parent: e.target.value })}
                >
                  <option value="">Root category</option>
                  {items
                    .filter((c) => c.id !== editingId && !c.parent)
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {getLocalizedCategoryName(c, i18n.language)}
                      </option>
                    ))}
                </NativeSelect>
              </div>
              <div className="space-y-1">
                <Label>Slug</Label>
                <Input
                  value={form.slug}
                  onChange={(e) => setForm({ ...form, slug: e.target.value })}
                  required
                />
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <Label>Name (Default)</Label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-1">
                <Label>Name (UZ)</Label>
                <Input
                  value={form.name_uz}
                  onChange={(e) => setForm({ ...form, name_uz: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-1">
                <Label>Name (RU)</Label>
                <Input
                  value={form.name_ru}
                  onChange={(e) => setForm({ ...form, name_ru: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-1">
                <Label>Name (EN)</Label>
                <Input
                  value={form.name_en}
                  onChange={(e) => setForm({ ...form, name_en: e.target.value })}
                  required
                />
              </div>
            </div>

            <div className="space-y-1">
              <Label>{t("employer.orderDescLabel")}</Label>
              <Textarea
                rows={2}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={saveMutation.isPending}>
                {t("common.save")}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deactivateTarget)}
        onOpenChange={(o) => !o && setDeactivateTarget(null)}
        title={t("admin.deactivateCategory")}
        description={`${deactivateTarget?.name || ""}: deactivating a category removes it from active worker assignments.`}
        variant="destructive"
        loading={deactivateMutation.isPending}
        onConfirm={() => deactivateTarget && deactivateMutation.mutate(deactivateTarget.id)}
      />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
        title={t("common.delete")}
        description={`${deleteTarget?.name || ""}`}
        variant="destructive"
        loading={deleteMutation.isPending}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
      />
    </div>
  );
}
