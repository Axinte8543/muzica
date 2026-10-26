import { describe, test, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import PaginationControls from "../../src/components/PaginationControls";
import ConversationsList from "../../src/components/ConversationsList";
import ReactionPicker from "../../src/components/ReactionPicker";
import ReactionsList from "../../src/components/ReactionsList";

const pagination = (props = {}) => render(<PaginationControls page={2} totalPages={3} onPrev={vi.fn()} onNext={vi.fn()} {...props} />);
const conversation = (props = {}) => render(<ConversationsList conversations={[]} friends={[]} friendSearchValue="" onSelectUser={vi.fn()} {...props} />);
const friends = [{ id: 2, username: "Bob" }, { id: 3, username: "Alice" }];

describe("Pagination", () => {
  test("hides a single page", () => { pagination({totalPages: 1}); expect(screen.queryByRole("button")).not.toBeInTheDocument(); });
  test("hides empty results", () => { pagination({totalPages: 0}); expect(screen.queryByRole("button")).not.toBeInTheDocument(); });
  test("disables previous on first page", () => { pagination({page: 1}); expect(screen.getByRole("button", {name: "Înapoi"})).toBeDisabled(); });
  test("disables next on last page", () => { pagination({page: 3}); expect(screen.getByRole("button", {name: "Înainte"})).toBeDisabled(); });
  test("invokes previous", () => { const fn = vi.fn(); pagination({onPrev: fn}); fireEvent.click(screen.getByText("Înapoi")); expect(fn).toHaveBeenCalledOnce(); });
  test("invokes next", () => { const fn = vi.fn(); pagination({onNext: fn}); fireEvent.click(screen.getByText("Înainte")); expect(fn).toHaveBeenCalledOnce(); });
  test("shows total count", () => { pagination({totalCount: 25}); expect(screen.getByText(/25 total/)).toBeVisible(); });
});
describe("Conversations", () => {
  test("handles missing lists", () => { conversation({conversations: undefined, friends: undefined}); expect(screen.getByText(/Nu ai prieteni/)).toBeVisible(); });
  test("sorts friends by name", () => { conversation({friends}); expect(screen.getAllByRole("button").map(b => b.textContent)).toEqual([expect.stringContaining("Alice"), expect.stringContaining("Bob")]); });
  test("filters friends ignoring case and whitespace", () => { conversation({friends, friendSearchValue: "  bOB  "}); expect(screen.getByText("Bob")).toBeVisible(); expect(screen.queryByText("Alice")).not.toBeInTheDocument(); });
  test("distinguishes no search matches from no friends", () => { conversation({friends, friendSearchValue: "zzz"}); expect(screen.getByText("Niciun prieten găsit.")).toBeVisible(); });
  test("selects a friend", () => { const fn=vi.fn(); conversation({friends, onSelectUser: fn}); fireEvent.click(screen.getByRole("button", {name: /Bob/})); expect(fn).toHaveBeenCalledWith(2); });
  test("conversation items support keyboard via native buttons", () => { conversation({conversations: [{user_id: 2, username: "Bob", last_message: "Salut"}]}); expect(screen.getByRole("button", {name: /Bob/})).toHaveAttribute("type", "button"); });
  test("normalizes selected identifiers", () => { conversation({conversations: [{user_id: 2, username: "Bob"}], selectedUserId: "2"}); expect(screen.getByRole("button", {name: /Bob/})).toHaveClass("active"); });
  test("search has an accessible name", () => { conversation(); expect(screen.getByRole("searchbox", {name: "Caută prieteni"})).toBeVisible(); });
  test("announces friend loading errors", () => { conversation({friendsError: "Indisponibil"}); expect(screen.getByRole("alert")).toHaveTextContent("Indisponibil"); });
  test("shows unread counts", () => { conversation({conversations: [{user_id: 2, username: "Bob", unread_count: 3}]}); expect(screen.getByText("3")).toBeVisible(); });
});
describe("Reactions", () => {
  test("starts closed", () => { render(<ReactionPicker onSelectEmoji={vi.fn()} />); expect(screen.queryByTitle("🔥")).not.toBeInTheDocument(); });
  test("opens all available reactions", () => { render(<ReactionPicker onSelectEmoji={vi.fn()} />); fireEvent.click(screen.getByTitle("Add reaction")); expect(screen.getAllByRole("button")).toHaveLength(9); });
  test("selects emoji and closes", () => { const fn=vi.fn(); render(<ReactionPicker onSelectEmoji={fn} />); fireEvent.click(screen.getByTitle("Add reaction")); fireEvent.click(screen.getByTitle("🔥")); expect(fn).toHaveBeenCalledWith("🔥"); expect(screen.queryByTitle("🔥")).not.toBeInTheDocument(); });
  test("picker buttons do not submit parent forms", () => { const fn=vi.fn(e=>e.preventDefault()); render(<form onSubmit={fn}><ReactionPicker onSelectEmoji={vi.fn()} /></form>); fireEvent.click(screen.getByTitle("Add reaction")); fireEvent.click(screen.getByTitle("🔥")); expect(fn).not.toHaveBeenCalled(); });
  test("disables picker while saving", () => { render(<ReactionPicker isLoading onSelectEmoji={vi.fn()} />); expect(screen.getByRole("button")).toBeDisabled(); });
  test("hides empty reaction list", () => { render(<ReactionsList reactions={[]} />); expect(screen.queryByRole("button")).not.toBeInTheDocument(); });
  test("reaction buttons do not submit parent forms", () => { const fn=vi.fn(e=>e.preventDefault()); render(<form onSubmit={fn}><ReactionsList reactions={[{emoji:"🔥", count:2}]} onReactionClick={vi.fn()} /></form>); fireEvent.click(screen.getByRole("button")); expect(fn).not.toHaveBeenCalled(); });
  test("exposes selected state to assistive technology", () => { render(<ReactionsList reactions={[{emoji:"🔥", count:2, user_reacted:true}]} onReactionClick={vi.fn()} />); expect(screen.getByRole("button")).toHaveAttribute("aria-pressed", "true"); });
  test("returns clicked reaction", () => { const fn=vi.fn(); render(<ReactionsList reactions={[{emoji:"🔥", count:2}]} onReactionClick={fn} />); fireEvent.click(screen.getByRole("button")); expect(fn).toHaveBeenCalledWith("🔥"); });
});
