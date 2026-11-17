import { Link, Route, Routes, useLocation } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError } from "axios";
import { describe, expect, it, vi } from "vitest";
import { Navbar } from "@/components/navigation/Navbar";
import { ScrollToTop } from "@/app/router/ScrollToTop";
import { ProtectedRoute } from "@/app/router/ProtectedRoute";
import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { EmployerOrderFormPage } from "@/features/employer/EmployerOrderFormPage";
import { MessagesPage } from "@/features/chat/MessagesPage";
import { authApi, categoriesApi, chatApi, notificationsApi, ordersApi } from "@/services/api";
import { useAuthStore } from "@/stores/authStore";
import { extractApiErrorMessage, formatCurrencyUZS, formatDate, formatDateTime } from "@/lib/utils";
import i18n from "@/i18n";
import { renderWithProviders } from "@/test/renderWithProviders";
import type { ApiPaginatedResponse, Category, ChatMessage, Conversation, OrderImage, ServiceOrder, UserSummary } from "@/types/api";

const page = <T,>(results: T[]): ApiPaginatedResponse<T> => ({
  success:true, count:results.length, total_pages:1, current_page:1, next:null, previous:null, results,
});
const worker = { id:"worker", role:"WORKER", full_name:"Usability worker", phone_number:"+998901234567",
  account_status:"ACTIVE", is_worker:true, is_employer:false, worker_profile_id:"wp", is_phone_verified:false } as UserSummary;
const category = { id:"cat", name:"Tozalash", is_active:true } as Category;
const order = { id:"saved-order", category:"cat", title:"Existing order", description:"Existing order description",
  budget:"500.50", capacity:1, budget_type:"FIXED", work_type:"ONSITE", location:"Toshkent", status:"PUBLISHED" } as ServiceOrder;

function LocationView() {
  const location = useLocation();
  return <p>{location.pathname + location.search + location.hash}</p>;
}

function RefreshOrder() {
  const cache = useQueryClient();
  return <button onClick={() => void cache.invalidateQueries({queryKey:["order","saved-order"]})}>Refresh order</button>;
}

async function fillOrder(user: ReturnType<typeof userEvent.setup>) {
  await screen.findByRole("option", { name:"Tozalash" });
  await user.selectOptions(screen.getByLabelText("Kategoriya"), "cat");
  await user.type(screen.getByLabelText("Buyurtma sarlavhasi"), "Tozalash buyurtmasi");
  await user.type(screen.getByLabelText("Batafsil tavsif"), "Uy tozalash bo'yicha batafsil tavsif");
  await user.type(screen.getByLabelText("Byudjet (UZS)"), "500.50");
}

describe("Everyday local navigation and forms", () => {
  it("closes the mobile navigation when logging out from a public page", async () => {
    const user = userEvent.setup();
    useAuthStore.getState().setSession(worker, {access:"qa-access", refresh:"qa-refresh", token_type:"Bearer"});
    vi.spyOn(authApi, "logout").mockResolvedValue({success:true,data:null});
    vi.spyOn(notificationsApi, "list").mockResolvedValue(page([]));
    renderWithProviders(<><Navbar /><LocationView /></>, {initialEntries:["/orders/synthetic"]});
    await user.click(screen.getByRole("button", {name:"Menyuni ochish"}));
    await user.click(within(screen.getByRole("navigation", {name:"Asosiy navigatsiya"})).getByRole("button", {name:"Chiqish"}));
    await screen.findByText("/login");
    expect(screen.queryByRole("navigation", {name:"Asosiy navigatsiya"})).not.toBeInTheDocument();
    expect(screen.getByRole("button", {name:"Menyuni ochish"})).toHaveAttribute("aria-expanded", "false");
    expect(useAuthStore.getState().user).toBeNull();
  });

  it("keeps fractional budget amounts and renders portable numeric Uzbek dates", () => {
    expect(formatCurrencyUZS("500.50")).toMatch(/500[,.]50 UZS/);
    expect(formatCurrencyUZS("500")).toBe("500 UZS");
    expect(formatDate("2026-11-16T12:00:00Z","uz")).toContain("11");
    expect(formatDateTime("2026-11-16T12:00:00Z","uz")).toContain("11");
    expect(formatDate("2026-11-16T12:00:00Z","uz")).not.toMatch(/M11|noy|Nov/);
  });
  it("localizes credential and connection errors while keeping server authorization failures intact", async () => {
    const denied = new AxiosError("Request failed", "ERR_BAD_REQUEST", undefined, {}, {
      status:401, statusText:"Unauthorized", headers:{}, config:{} as never,
      data:{error:{code:"invalid_credentials",message:"Invalid phone number or password."}},
    });
    expect(extractApiErrorMessage(denied)).toBe("Telefon raqami yoki parol noto'g'ri.");
    expect(extractApiErrorMessage(new AxiosError("Network Error"))).toMatch(/^Serverga ulanib bo'lmadi/);
    await i18n.changeLanguage("en");
    expect(extractApiErrorMessage(denied)).toBe("Incorrect phone number or password.");
    await i18n.changeLanguage("ru");
    expect(extractApiErrorMessage(denied)).toBe("Неверный номер телефона или пароль.");
    expect(denied.response?.status).toBe(401);
    const forbidden = new AxiosError("Request failed", "ERR_BAD_REQUEST", undefined, {}, {
      status:403, statusText:"Forbidden", headers:{}, config:{} as never,
      data:{error:{code:"forbidden",message:"You do not have permission to view this order."}},
    });
    expect(extractApiErrorMessage(forbidden)).toBe(i18n.t("errors.permissionDenied"));
    expect(forbidden.response?.status).toBe(403);

  });
  it("returns to the exact protected chat link after normal login", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi,"login").mockResolvedValue({success:true,data:{user:worker,tokens:{access:"test-access",refresh:"test-refresh",token_type:"Bearer"}}});
    renderWithProviders(<Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute requiredRole="WORKER" />}>
        <Route path="/dashboard/messages" element={<LocationView />} />
      </Route>
    </Routes>,{initialEntries:["/dashboard/messages?conversation=conv-b#latest"]});
    await user.clear(screen.getByLabelText("Telefon raqami"));
    await user.type(screen.getByLabelText("Telefon raqami"),"+998901234567");
    await user.type(screen.getByLabelText("Parol"),"SyntheticLogin2026!");
    await user.click(screen.getByRole("button",{name:"Kirish"}));
    expect(await screen.findByText("/dashboard/messages?conversation=conv-b#latest")).toBeInTheDocument();
  });

  it("shows the blocking invalid-email error beside the optional email field", async () => {
    const user=userEvent.setup();
    const register=vi.spyOn(authApi,"register");
    renderWithProviders(<RegisterPage />);
    await user.type(screen.getByLabelText("To'liq ism-familiya"),"Test User");
    await user.clear(screen.getByLabelText("Telefon raqami"));
    await user.type(screen.getByLabelText("Telefon raqami"),"+998901234567");
    await user.type(screen.getByLabelText("Parol"),"SyntheticRegister2026!");
    await user.type(screen.getByLabelText("Parolni tasdiqlang"),"SyntheticRegister2026!");
    await user.type(screen.getByLabelText(/Elektron pochta/),"invalid-email");
    await user.click(screen.getByRole("button",{name:"Ro'yxatdan o'tish"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("To'g'ri elektron pochta manzilini kiriting");
    expect(screen.getByLabelText(/Elektron pochta/)).toHaveAttribute("aria-invalid","true");
    expect(register).not.toHaveBeenCalled();
  });

  it("offers dual workspace switching in the localized mobile menu without changing authentication", async () => {
    const user=userEvent.setup();
    vi.spyOn(notificationsApi,"list").mockResolvedValue(page([]));
    useAuthStore.getState().setSession({...worker,is_employer:true,employer_profile_id:"ep"},{access:"unchanged-access",refresh:"unchanged-refresh",token_type:"Bearer"});
    renderWithProviders(<><Navbar /><Routes><Route path="/employer" element={<LocationView />} /><Route path="/" element={<div>Home</div>} /></Routes></>);
    const menu=screen.getByRole("button",{name:"Menyuni ochish"});
    expect(menu).toHaveAttribute("aria-expanded","false");
    await user.click(menu);
    const navigation=screen.getByRole("navigation",{name:"Asosiy navigatsiya"});
    await user.click(within(navigation).getByRole("button",{name:"Buyurtmachi rejimi"}));
    expect(await screen.findByText("/employer")).toBeInTheDocument();
    expect(useAuthStore.getState().activeWorkspace).toBe("EMPLOYER");
    expect(useAuthStore.getState().accessToken).toBe("unchanged-access");
    expect(screen.queryByRole("navigation",{name:"Asosiy navigatsiya"})).not.toBeInTheDocument();
  });

  it("scrolls to the top on page changes without jumping while filters change", async () => {
    const user=userEvent.setup();
    const scroll=vi.spyOn(window,"scrollTo").mockImplementation(() => {});
    renderWithProviders(<><ScrollToTop /><Link to="/marketplace?search=test">Filter</Link><Link to="/register">Register</Link></>,{initialEntries:["/marketplace"]});
    scroll.mockClear();
    await user.click(screen.getByRole("link",{name:"Filter"}));
    expect(scroll).not.toHaveBeenCalled();
    await user.click(screen.getByRole("link",{name:"Register"}));
    expect(scroll).toHaveBeenCalledWith(0,0);
  });

  it("retries a failed image upload on the saved order, without creating a duplicate", async () => {
    const user=userEvent.setup();
    vi.spyOn(categoriesApi,"list").mockResolvedValue(page([category]));
    const create=vi.spyOn(ordersApi,"create").mockResolvedValue(order);
    const update=vi.spyOn(ordersApi,"update").mockResolvedValue(order);
    const upload=vi.spyOn(ordersApi,"uploadImage").mockRejectedValueOnce(new Error("Upload failed"))
      .mockResolvedValueOnce({id:"image",image:"/private/image"} as OrderImage);
    renderWithProviders(<Routes><Route path="/employer/orders/new" element={<EmployerOrderFormPage />} /><Route path="/orders/:id" element={<LocationView />} /></Routes>,{initialEntries:["/employer/orders/new"]});
    await fillOrder(user);
    const image=new File(["synthetic image"],"fixture.png",{type:"image/png"});
    await user.upload(screen.getByLabelText(/Buyurtma rasmi/),image);
    await user.click(screen.getByRole("button",{name:"Saqlash"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("Buyurtma saqlandi, ammo rasm yuklanmadi");
    await user.click(screen.getByRole("button",{name:"Saqlash"}));
    expect(await screen.findByText("/orders/saved-order")).toBeInTheDocument();
    expect(create).toHaveBeenCalledTimes(1);
    expect(create).toHaveBeenCalledWith(expect.objectContaining({budget:"500.50"}));
    expect(update).toHaveBeenCalledWith("saved-order",expect.objectContaining({budget:"500.50"}));
    expect(upload).toHaveBeenCalledTimes(2);
    expect(upload).toHaveBeenLastCalledWith("saved-order",image);
  });

  it("shows retry instead of an editable empty form when order retrieval fails", async () => {
    vi.spyOn(categoriesApi,"list").mockResolvedValue(page([category]));
    vi.spyOn(ordersApi,"detail").mockRejectedValue(new Error("Unavailable"));
    renderWithProviders(<EmployerOrderFormPage />,{routePath:"/employer/orders/:id/edit",initialEntries:["/employer/orders/saved-order/edit"]});
    expect(await screen.findByRole("button",{name:"Qayta urinish"})).toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"Saqlash"})).not.toBeInTheDocument();
  });

  it("keeps unsaved edits when the background order query refreshes", async () => {
    const user=userEvent.setup();
    vi.spyOn(categoriesApi,"list").mockResolvedValue(page([category]));
    const detail=vi.spyOn(ordersApi,"detail").mockResolvedValueOnce(order).mockResolvedValue({...order,title:"Server changed title"});
    renderWithProviders(<><EmployerOrderFormPage /><RefreshOrder /></>,{routePath:"/employer/orders/:id/edit",initialEntries:["/employer/orders/saved-order/edit"]});
    const title=await screen.findByLabelText("Buyurtma sarlavhasi");
    await user.clear(title);await user.type(title,"My unsaved title");
    await user.click(screen.getByRole("button",{name:"Refresh order"}));
    await waitFor(() => expect(detail).toHaveBeenCalledTimes(2));
    expect(title).toHaveValue("My unsaved title");
  });
});

const conversations=["a","b"].map((letter) => ({id:`conv-${letter}`,order:`order-${letter}`,order_title:`Job ${letter}`,
  employer_name:`Peer ${letter}`,worker:"wp",worker_name:"Worker",unread_count:0,last_message:null} as Conversation));
const message=(id:string,content:string):ChatMessage => ({id,conversation:"conv-a",content,sender_id:"worker",sender_name:"Worker",attachment:null,is_read:true,read_at:null,created_at:"2026-11-17T00:00:00Z"});

describe("Chat drafts and long histories", () => {
  it("does not navigate back to chat when an in-flight send finishes after leaving the page", async () => {
    const user=userEvent.setup();useAuthStore.setState({user:worker});
    vi.spyOn(chatApi,"listConversations").mockResolvedValue(page(conversations));
    vi.spyOn(chatApi,"listMessages").mockResolvedValue(page([]));
    let finish!: (value:ChatMessage) => void;
    const send=vi.spyOn(chatApi,"sendMessage").mockImplementation(() => new Promise((resolve) => {finish=resolve;}));
    renderWithProviders(<><Link to="/settings">Leave chat</Link><Routes>
      <Route path="/dashboard/messages" element={<MessagesPage />} />
      <Route path="/settings" element={<div>Settings remain open</div>} />
    </Routes></>,{initialEntries:["/dashboard/messages?conversation=conv-a"]});
    await user.type(await screen.findByLabelText("Xabar yozing..."),"Sending reply");
    await user.click(screen.getByRole("button",{name:"Yuborish"}));
    await waitFor(() => expect(send).toHaveBeenCalledTimes(1));
    await user.click(screen.getByRole("link",{name:"Leave chat"}));
    await act(async () => {finish(message("sent","Sending reply"));});
    expect(screen.getByText("Settings remain open")).toBeInTheDocument();
  });

  it("keeps each conversation's draft and never clears another draft when an earlier send completes", async () => {
    const user=userEvent.setup();useAuthStore.setState({user:worker});
    vi.spyOn(chatApi,"listConversations").mockResolvedValue(page(conversations));
    vi.spyOn(chatApi,"listMessages").mockResolvedValue(page([]));
    let finish!: (value:ChatMessage) => void;
    const send=vi.spyOn(chatApi,"sendMessage").mockImplementationOnce(() => new Promise((resolve) => {finish=resolve;})).mockResolvedValue(message("sent-b","Draft B"));
    renderWithProviders(<MessagesPage />,{initialEntries:["/dashboard/messages?conversation=conv-a"]});
    const input=await screen.findByLabelText("Xabar yozing...");
    await user.type(input,"Draft A");
    await user.click(screen.getByRole("button",{name:/Peer b/}));
    expect(input).toHaveValue("");await user.type(input,"Draft B");
    await user.click(screen.getByRole("button",{name:/Peer a/}));
    expect(input).toHaveValue("Draft A");
    await user.click(screen.getByRole("button",{name:"Yuborish"}));
    await waitFor(() => expect(send).toHaveBeenCalledWith("conv-a",{content:"Draft A",attachment:null}));
    await user.click(screen.getByRole("button",{name:/Peer b/}));
    finish(message("sent-a","Draft A"));
    await waitFor(() => expect(screen.getByRole("button",{name:"Yuborish"})).toBeEnabled());
    expect(input).toHaveValue("Draft B");
    await user.click(screen.getByRole("button",{name:"Yuborish"}));
    await waitFor(() => expect(send).toHaveBeenLastCalledWith("conv-b",{content:"Draft B",attachment:null}));
  });

  it("requests the newest page, displays it chronologically and can load older history", async () => {
    const user=userEvent.setup();useAuthStore.setState({user:worker});
    vi.spyOn(chatApi,"listConversations").mockResolvedValue(page(conversations));
    const latest={...page([message("newest","Visible newest"),message("older","Visible older")]),count:101,total_pages:2};
    const older={...page([message("oldest","Visible oldest")]),count:101,total_pages:2,current_page:2};
    const list=vi.spyOn(chatApi,"listMessages").mockImplementation(async (_,params) => params?.page===2 ? older : latest);
    renderWithProviders(<MessagesPage />,{initialEntries:["/dashboard/messages?conversation=conv-a"]});
    await screen.findByText("Visible newest");
    expect(list).toHaveBeenCalledWith("conv-a",{page_size:100,page:1,ordering:"-created_at"});
    expect(screen.getAllByText(/^Visible /).map((item) => item.textContent)).toEqual(["Visible older","Visible newest"]);
    await user.click(screen.getByRole("button",{name:"Oldingi xabarlar"}));
    expect(await screen.findByText("Visible oldest")).toBeInTheDocument();
    expect(list).toHaveBeenLastCalledWith("conv-a",{page_size:100,page:2,ordering:"-created_at"});
    await user.click(screen.getByRole("button",{name:"Yangi xabarlar"}));
    expect(await screen.findByText("Visible newest")).toBeInTheDocument();
  });
});
