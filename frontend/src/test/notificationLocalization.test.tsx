import { act, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import { notificationText } from "@/lib/notificationText";
import { NotificationsPage } from "@/features/notifications/NotificationsPage";
import { NotificationBell } from "@/components/navigation/NotificationBell";
import { OrderDetailPage } from "@/features/orders/OrderDetailPage";
import { useAuthStore } from "@/stores/authStore";
import { applicationsApi, ordersApi, reviewsApi, notificationsApi } from "@/services/api";
import { renderWithProviders } from "@/test/renderWithProviders";
import userEvent from "@testing-library/user-event";
import type { ServiceOrder, UserSummary, NotificationItem } from "@/types/api";

const fixtures = [
 ["NEW_APPLICATION", "New application on 'O'ktamning ishi'", "Ali applied with a proposed price of 100.25."],
 ["APPLICATION_ACCEPTED", "Application Accepted: 'O'ktamning ishi'", "Your application for 'O'ktamning ishi' was accepted! You are now hired."],
 ["APPLICATION_REJECTED", "Application not selected for 'Ish'", "Another worker was selected for 'Ish'."],
 ["APPLICATION_REJECTED", "Application Rejected: 'Ish'", "Your application for 'Ish' was rejected."],
 ["NEW_INVITATION", "Direct Invitation: 'Ish'", "You have been invited to work on 'Ish'."],
 ["INVITATION_ACCEPTED", "Invitation Accepted: 'Ish'", "Ali accepted your invitation for 'Ish'."],
 ["INVITATION_REJECTED", "Invitation Rejected: 'Ish'", "Ali declined your invitation for 'Ish'."],
 ["NEW_MESSAGE", "New message on 'Ish'", "Sent an attachment."],
 ["NEW_REVIEW", "New 5-star review received", "You received a 5/5 review for 'Ish'."],
 ["ORDER_STATUS_CHANGED", "Order Completed: Ish", "Employer marked 'Ish' as COMPLETED. You can now leave a review."],
 ["ORDER_STATUS_CHANGED", "Order Cancelled: Ish", "Employer cancelled order 'Ish'."],
 ["ORDER_STATUS_CHANGED", "Order 'Ish' closed", "The order 'Ish' was marked CLOSED. Your pending application was closed."],
 ["ORDER_STATUS_CHANGED", "Order 'Ish' cancelled", "The order 'Ish' was marked CANCELLED. Your pending invitation was cancelled."],
 ["ORDER_STATUS_CHANGED", "Order CLOSED by Admin", "Order 'Ish' was closed by moderation."],
 ["VERIFICATION_UPDATED", "Worker Verification VERIFIED", "Your worker profile has been verified! You can now apply for service orders."],
 ["VERIFICATION_UPDATED", "Worker Verification REJECTED", "Your worker verification was rejected. Notes: Verification rejected by administrator."],
];
const make = ([event_type,title,message]:string[]):NotificationItem => ({id:"notice",event_type,title,message,data:{order_id:"order"},is_read:true,read_at:null,created_at:"2026-11-17T05:00:00Z"});

describe("Historical notification presentation", () => {
  it.each(["uz", "ru", "en"])("renders every existing server template in %s without changing data", async lang => {
    await i18n.changeLanguage(lang);
    for (const fixture of fixtures) {
      const item=make(fixture), original=JSON.stringify(item);
      const rendered=notificationText(item,i18n.t);
      expect(rendered.event).not.toBe(item.event_type);
      expect(rendered.title).not.toBe(item.title);
      if (lang!=="en") expect(rendered.message).not.toBe(item.message);
      expect(JSON.stringify(rendered)).not.toMatch(/notifications\.|\{\{/);
      expect(JSON.stringify(item)).toBe(original);
    }
    const apostrophe=notificationText(make(fixtures[1]),i18n.t);
    expect(apostrophe.title).toContain("O'ktamning ishi");
    expect(apostrophe.message).toContain("O'ktamning ishi");
  });
  it("preserves user-authored content and unknown future templates", () => {
    const chat=make(["NEW_MESSAGE","New message on 'Ish'","My literal message <script> & O'ktam"]);
    expect(notificationText(chat,i18n.t).message).toBe(chat.message);
    const system=make(["SYSTEM","Owner notice","Custom administrator message"]);
    expect(notificationText(system,i18n.t)).toMatchObject({title:system.title,message:system.message});
    const future=make(["FUTURE_EVENT","A future title","A future body"]);
    expect(notificationText(future,i18n.t)).toEqual({event:future.event_type,title:future.title,message:future.message});
    const notes=make(["VERIFICATION_UPDATED","Worker Verification REJECTED","Your worker verification was rejected. Notes: Shaxsiy izoh <b>unchanged</b>"]);
    expect(notificationText(notes,i18n.t).message).toContain("Shaxsiy izoh <b>unchanged</b>");
  });
  it("updates persisted list content on language switch without marking or rewriting notifications", async () => {
    const item=make(fixtures[8]);
    vi.spyOn(notificationsApi,"list").mockResolvedValue({success:true,count:1,total_pages:1,current_page:1,next:null,previous:null,unread_count:0,results:[item]});
    const mark=vi.spyOn(notificationsApi,"markRead");
    renderWithProviders(<NotificationsPage />);
    expect(await screen.findByText("Yangi 5 yulduzli sharh")).toBeInTheDocument();
    expect(screen.getByText("Yangi sharh")).toBeInTheDocument();
    await act(async()=>{await i18n.changeLanguage("ru");});
    expect(screen.getByText("Новый отзыв: 5 звёзд")).toBeInTheDocument();
    expect(mark).not.toHaveBeenCalled();
    expect(item.title).toBe("New 5-star review received");
  });
  it("also localizes notification dropdown content", async () => {
    const user=userEvent.setup(),item=make(fixtures[8]);
    vi.spyOn(notificationsApi,"list").mockResolvedValue({success:true,count:1,total_pages:1,current_page:1,next:null,previous:null,unread_count:0,results:[item]});
    renderWithProviders(<NotificationBell />);
    await user.click(screen.getByRole("button",{name:"Bildirishnomalar"}));
    expect(await screen.findByText("Yangi 5 yulduzli sharh")).toBeInTheDocument();
    expect(screen.getByText('“Ish” uchun 5/5 baholi sharh oldingiz.')).toBeInTheDocument();
  });
});

it.each(["uz","ru","en"])("renders all five review star buttons accessibly in %s", async lang => {
  await i18n.changeLanguage(lang);
  useAuthStore.getState().setSession({id:"worker",role:"WORKER",is_worker:true,worker_profile_id:"wp"} as UserSummary,{access:"test",refresh:"test",token_type:"Bearer"});
  const empty={success:true,count:0,total_pages:1,current_page:1,next:null,previous:null,results:[]};
  vi.spyOn(ordersApi,"detail").mockResolvedValue({id:"order",status:"COMPLETED",title:"Completed fixture",employer_user_id:"employer",images:[],assigned_workers:[],budget:"100.25",created_at:"2026-11-17T05:00:00Z"} as unknown as ServiceOrder);
  vi.spyOn(applicationsApi,"list").mockResolvedValue(empty);
  vi.spyOn(reviewsApi,"list").mockResolvedValue(empty);
  vi.spyOn(reviewsApi,"eligibility").mockResolvedValue({eligible:true,reason:"",direction:"WORKER_TO_EMPLOYER",existing_review:null,reviewee_id:"employer"});
  renderWithProviders(<OrderDetailPage />,{initialEntries:["/orders/order"],routePath:"/orders/:id"});
  for (let star=1;star<=5;star++) {
    expect(await screen.findByRole("button",{name:i18n.t("reviews.rateStars",{count:star})})).toHaveAttribute("type","button");
  }
  if(lang!=="en") expect(screen.queryByRole("button",{name:/^Rate /})).not.toBeInTheDocument();
});
