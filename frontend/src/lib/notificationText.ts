import type { TFunction } from "i18next";
import type { NotificationItem } from "@/types/api";

// Render historical server templates in the selected language. Never rewrite
// persisted records or translate user-authored chat text / moderation notes.
export function notificationText(item: NotificationItem, t: TFunction) {
  const eventKey = `notifications.events.${item.event_type}`;
  const event = t(eventKey, { defaultValue: item.event_type });
  const render = (value: string, rules: Array<[RegExp, string, string[]]>) => {
    for (const [pattern, key, names] of rules) {
      const match = value.match(pattern);
      if (!match) continue;
      const params: Record<string, string> = {};
      names.forEach((name, index) => { params[name] = match[index + 1]; });
      if (params.status) params.status = t(`statuses.${params.status.toUpperCase()}`, {defaultValue:params.status});
      return t(`notifications.templates.${key}`, params);
    }
    return value;
  };
  const titles: Record<string, Array<[RegExp, string, string[]]>> = {
    NEW_APPLICATION: [[/^New application on '(.*)'$/, "newApplicationTitle", ["order"]]],
    APPLICATION_ACCEPTED: [[/^Application Accepted: '(.*)'$/, "acceptedTitle", ["order"]]],
    APPLICATION_REJECTED: [
      [/^Application not selected for '(.*)'$/, "notSelectedTitle", ["order"]],
      [/^Application Rejected: '(.*)'$/, "rejectedTitle", ["order"]],
    ],
    NEW_INVITATION: [[/^Direct Invitation: '(.*)'$/, "invitationTitle", ["order"]]],
    INVITATION_ACCEPTED: [[/^Invitation Accepted: '(.*)'$/, "invitationAcceptedTitle", ["order"]]],
    INVITATION_REJECTED: [[/^Invitation Rejected: '(.*)'$/, "invitationRejectedTitle", ["order"]]],
    NEW_MESSAGE: [[/^New message on '(.*)'$/, "messageTitle", ["order"]]],
    NEW_REVIEW: [[/^New ([1-5])-star review received$/, "reviewTitle", ["rating"]]],
    ORDER_STATUS_CHANGED: [
      [/^Order Completed: (.*)$/, "completedTitle", ["order"]],
      [/^Order Cancelled: (.*)$/, "cancelledTitle", ["order"]],
      [/^Order '(.*)' ([a-z_]+)$/, "statusTitle", ["order", "status"]],
      [/^Order ([A-Z_]+) by Admin$/, "moderatedTitle", ["status"]],
    ],
    VERIFICATION_UPDATED: [
      [/^Worker Verification VERIFIED$/, "verifiedTitle", []],
      [/^Worker Verification REJECTED$/, "verificationRejectedTitle", []],
    ],
  };
  const messages: Record<string, Array<[RegExp, string, string[]]>> = {
    NEW_APPLICATION: [[/^(.*) applied with a proposed price of (.*)\.$/, "newApplication", ["worker", "price"]]],
    APPLICATION_ACCEPTED: [[/^Your application for '(.*)' was accepted! You are now hired\.$/, "accepted", ["order"]]],
    APPLICATION_REJECTED: [
      [/^Another worker was selected for '(.*)'\.$/, "notSelected", ["order"]],
      [/^Your application for '(.*)' was rejected\.$/, "rejected", ["order"]],
    ],
    NEW_INVITATION: [[/^You have been invited to work on '(.*)'\.$/, "invitation", ["order"]]],
    INVITATION_ACCEPTED: [[/^(.*) accepted your invitation for '(.*)'\.$/, "invitationAccepted", ["worker", "order"]]],
    INVITATION_REJECTED: [[/^(.*) declined your invitation for '(.*)'\.$/, "invitationRejected", ["worker", "order"]]],
    NEW_REVIEW: [[/^You received a ([1-5])\/5 review for '(.*)'\.$/, "review", ["rating", "order"]]],
    ORDER_STATUS_CHANGED: [
      [/^Employer marked '(.*)' as COMPLETED\. You can now leave a review\.$/, "completed", ["order"]],
      [/^Employer cancelled order '(.*)'\.$/, "cancelled", ["order"]],
      [/^The order '(.*)' was marked ([A-Z_]+)\. Your pending application was closed\.$/, "applicationClosed", ["order", "status"]],
      [/^The order '(.*)' was marked ([A-Z_]+)\. Your pending invitation was cancelled\.$/, "invitationCancelled", ["order", "status"]],
      [/^Order '(.*)' was ([a-z_]+) by moderation\.$/, "moderated", ["order", "status"]],
    ],
    VERIFICATION_UPDATED: [
      [/^Your worker profile has been verified! You can now apply for service orders\.$/, "verified", []],
      [/^Your worker verification was rejected\. Notes: Verification rejected by administrator\.$/, "verificationRejected", []],
      [/^Your worker verification was rejected\. Notes: ([\s\S]*)$/, "verificationRejectedNotes", ["notes"]],
    ],
  };
  const message = item.event_type === "NEW_MESSAGE"
    ? (item.message === "Sent an attachment." ? t("notifications.templates.attachment") : item.message)
    : render(item.message, messages[item.event_type] || []);
  return { event, title:render(item.title, titles[item.event_type] || []), message };
}
