import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  Check,
  CheckCheck,
  FileIcon,
  Flag,
  MessageSquare,
  Paperclip,
  Send,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { ReportModal } from "@/components/shared/ReportModal";
import { chatApi } from "@/services/api";
import { apiClient } from "@/services/apiClient";
import { extractApiErrorMessage, formatDateTime } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";
import type { ApiPaginatedResponse, ChatMessage } from "@/types/api";

export function MessagesPage() {
  const { t, i18n } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  const selectedId = searchParams.get("conversation") || "";
  const [content, setContent] = useState("");
  const [attachment, setAttachment] = useState<File | null>(null);
  const [reportMsgId, setReportMsgId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const readAttempt = useRef("");

  const conversationsQuery = useQuery({
    queryKey: ["chat", "conversations"],
    queryFn: () => chatApi.listConversations({ page_size: 50 }),
    refetchInterval: 10000,
  });

  const conversations = conversationsQuery.data?.results || [];
  const activeConversation = conversations.find((c) => c.id === selectedId) || null;

  useEffect(() => {
    if (!selectedId && conversations.length > 0) {
      setSearchParams({ conversation: conversations[0].id }, { replace: true });
    }
  }, [selectedId, conversations, setSearchParams]);

  const messagesQuery = useQuery({
    queryKey: ["chat", "messages", selectedId],
    queryFn: () => chatApi.listMessages(selectedId, { page_size: 100 }),
    enabled: Boolean(selectedId),
    refetchInterval: 5000,
    retry: false,
  });

  const messages = messagesQuery.data?.results || [];

  const { mutate: markRead } = useMutation({
    mutationFn: (convId: string) => chatApi.markRead(convId),
    onSuccess: (_, convId) => {
      queryClient.setQueryData<ApiPaginatedResponse<ChatMessage>>(
        ["chat", "messages", convId],
        (cached) => cached && ({ ...cached, results: cached.results.map((message) =>
          message.sender_id !== user?.id ? { ...message, is_read: true } : message
        ) }),
      );
      void queryClient.invalidateQueries({ queryKey: ["chat", "conversations"] });
    },
    // Retry on the next message poll, never in a render loop.
    onError: () => { readAttempt.current = ""; },
  });

  useEffect(() => {
    if (!selectedId || !messages.length || !user) return;
    const unread = messages.filter((m) => m.sender_id !== user.id && !m.is_read);
    const attempt = `${selectedId}:${unread.map((m) => m.id).join(",")}`;
    if (unread.length && readAttempt.current !== attempt) {
      readAttempt.current = attempt;
      markRead(selectedId);
    }
  }, [selectedId, messages, messagesQuery.dataUpdatedAt, user, markRead]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, selectedId]);

  const sendMutation = useMutation({
    mutationFn: () => {
      if (!selectedId) throw new Error("No conversation selected");
      return chatApi.sendMessage(selectedId, { content: content.trim(), attachment });
    },
    onSuccess: () => {
      setContent("");
      setAttachment(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      void queryClient.invalidateQueries({ queryKey: ["chat", "messages", selectedId] });
      void queryClient.invalidateQueries({ queryKey: ["chat", "conversations"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const downloadAttachment = async (messageId: string) => {
    try {
      const response = await apiClient.get(`/chat/messages/${messageId}/attachment/`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data as Blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "attachment";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      toast.error(extractApiErrorMessage(error));
    }
  };

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim() && !attachment) return;
    sendMutation.mutate();
  };

  if (conversationsQuery.isLoading) return <Skeleton className="h-[520px]" />;
  if (conversationsQuery.isError) {
    return <ErrorState onRetry={() => void conversationsQuery.refetch()} />;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">{t("chat.title")}</h1>
        <Badge variant="outline" className="gap-1.5 text-xs">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          {t("chat.pollingActive")}
        </Badge>
      </div>

      {conversations.length === 0 ? (
        <EmptyState
          icon={<MessageSquare className="h-6 w-6" />}
          title={t("chat.noConversations")}
          description={t("chat.noConversationsHint")}
          action={
            <Link to="/marketplace?tab=orders">
              <Button variant="outline">{t("nav.marketplace")}</Button>
            </Link>
          }
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[320px_1fr] min-h-[640px] lg:h-[640px]">
          <Card className="flex flex-col overflow-hidden">
            <div className="border-b px-4 py-3 text-sm font-semibold">
              {t("nav.messages")} ({conversations.length})
            </div>
            <div className="flex-1 overflow-y-auto divide-y">
              {conversations.map((conv) => {
                const isSelected = conv.id === selectedId;
                const peerName =
                  user?.worker_profile_id === conv.worker ? conv.employer_name : conv.worker_name;
                return (
                  <button
                    key={conv.id}
                    type="button"
                    onClick={() => setSearchParams({ conversation: conv.id })}
                    className={`w-full text-left p-3.5 transition-colors hover:bg-muted/60 ${
                      isSelected ? "bg-primary/10 border-l-4 border-l-primary" : ""
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="truncate text-sm font-semibold">{peerName}</p>
                      {conv.unread_count > 0 && (
                        <Badge variant="default" className="h-5 px-1.5 text-[10px]">
                          {conv.unread_count}
                        </Badge>
                      )}
                    </div>
                    <p className="mt-0.5 truncate text-xs font-medium text-primary">
                      {conv.order_title}
                    </p>
                    <p className="mt-1 truncate text-xs text-muted-foreground">
                      {conv.last_message?.content ||
                        (conv.last_message?.has_attachment ? "Attachment" : "—")}
                    </p>
                  </button>
                );
              })}
            </div>
          </Card>

          <Card className="flex flex-col overflow-hidden">
            {!selectedId ? (
              <div className="flex flex-1 items-center justify-center p-6 text-sm text-muted-foreground">
                {t("chat.selectConversation")}
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
                  <div className="min-w-0">
                    <p className="truncate font-semibold">
                      {activeConversation
                        ? user?.worker_profile_id === activeConversation.worker
                          ? activeConversation.employer_name
                          : activeConversation.worker_name
                        : t("chat.title")}
                    </p>
                    {activeConversation && (
                      <Link
                        to={`/orders/${activeConversation.order}`}
                        className="truncate text-xs text-primary hover:underline block"
                      >
                        {activeConversation.order_title}
                      </Link>
                    )}
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-muted/20">
                  {messagesQuery.isLoading ? (
                    <Skeleton className="h-40" />
                  ) : messagesQuery.isError ? (
                    <ErrorState
                      message={t("chat.unauthorizedHint")}
                      onRetry={() => void messagesQuery.refetch()}
                    />
                  ) : messages.length === 0 ? (
                    <div className="py-12 text-center text-sm text-muted-foreground">
                      {t("common.noData")}
                    </div>
                  ) : (
                    messages.map((msg) => {
                      const isMine = msg.sender_id === user?.id;
                      const attachmentUrl = msg.attachment;
                      return (
                        <div
                          key={msg.id}
                          className={`flex ${isMine ? "justify-end" : "justify-start"}`}
                        >
                          <div
                            className={`group relative max-w-[78%] rounded-2xl px-4 py-2.5 text-sm shadow-xs ${
                              isMine
                                ? "bg-primary text-primary-foreground rounded-br-xs"
                                : "bg-card border text-foreground rounded-bl-xs"
                            }`}
                          >
                            {!isMine && (
                              <p className="mb-1 text-[11px] font-semibold opacity-80">
                                {msg.sender_name}
                              </p>
                            )}
                            {msg.content && <p className="whitespace-pre-wrap">{msg.content}</p>}
                            {attachmentUrl && (
                              <button
                                type="button"
                                onClick={() => void downloadAttachment(msg.id)}
                                className={`mt-2 inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs underline ${
                                  isMine
                                    ? "border-primary-foreground/30 bg-primary-foreground/10 text-primary-foreground"
                                    : "border-border bg-muted text-foreground"
                                }`}
                              >
                                <FileIcon className="h-3.5 w-3.5" />
                                <span>Attachment</span>
                              </button>
                            )}
                            <div
                              className={`mt-1 flex items-center justify-end gap-1.5 text-[10px] ${
                                isMine ? "text-primary-foreground/80" : "text-muted-foreground"
                              }`}
                            >
                              <span>{formatDateTime(msg.created_at, i18n.language)}</span>
                              {isMine &&
                                (msg.is_read ? (
                                  <CheckCheck className="h-3 w-3" aria-label={t("chat.readBadge")} />
                                ) : (
                                  <Check className="h-3 w-3" />
                                ))}
                              {!isMine && (
                                <button
                                  type="button"
                                  onClick={() => setReportMsgId(msg.id)}
                                  className="opacity-0 group-hover:opacity-100 transition-opacity hover:text-destructive"
                                  aria-label={t("reports.reportBtn")}
                                >
                                  <Flag className="h-3 w-3" />
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })
                  )}
                  <div ref={bottomRef} />
                </div>

                <form onSubmit={handleSend} className="border-t bg-card p-3 space-y-2">
                  {attachment && (
                    <div className="flex items-center justify-between rounded-md bg-muted px-3 py-1.5 text-xs">
                      <span className="truncate font-medium">{attachment.name}</span>
                      <button
                        type="button"
                        onClick={() => {
                          setAttachment(null);
                          if (fileInputRef.current) fileInputRef.current.value = "";
                        }}
                        className="text-muted-foreground hover:text-foreground"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <input
                      ref={fileInputRef}
                      type="file"
                      className="hidden"
                      onChange={(e) => setAttachment(e.target.files?.[0] || null)}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={() => fileInputRef.current?.click()}
                      aria-label={t("chat.attachFile")}
                    >
                      <Paperclip className="h-4 w-4" />
                    </Button>
                    <Input
                      aria-label={t("chat.typeMessage")}
                      value={content}
                      onChange={(e) => setContent(e.target.value)}
                      placeholder={t("chat.typeMessage")}
                      className="flex-1"
                    />
                    <Button
                      type="submit"
                      disabled={sendMutation.isPending || (!content.trim() && !attachment)}
                      className="gap-1.5"
                    >
                      <Send className="h-4 w-4" />
                      <span className="hidden sm:inline">{t("chat.send")}</span>
                    </Button>
                  </div>
                </form>
              </>
            )}
          </Card>
        </div>
      )}

      {reportMsgId && (
        <ReportModal
          open={Boolean(reportMsgId)}
          onOpenChange={(open) => !open && setReportMsgId(null)}
          targetType="MESSAGE"
          targetId={reportMsgId}
        />
      )}
    </div>
  );
}
