from __future__ import annotations

import datetime as dt
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Static

from shelf.decisions import merge_scan, set_status
from shelf.executor import apply_deletions
from shelf.model import ShelfItem, ShelfState
from shelf.scanner import resolve_roots, scan_shelf


def _format_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0:
            return f"{value:,.1f} {unit}"
        value /= 1024.0
    return f"{value:,.1f} PB"


def _format_date(timestamp: float) -> str:
    if not timestamp:
        return "-"
    return dt.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")


class ApplyConfirmation(ModalScreen[bool]):
    def __init__(self, total_items: int, total_size: int) -> None:
        super().__init__()
        self.total_items = total_items
        self.total_size = total_size

    def compose(self) -> ComposeResult:
        message = (
            f"Apply deletions for {self.total_items} item(s) "
            f"({ _format_size(self.total_size) })?\n\n"
            "Press [y] to confirm, [n] to cancel."
        )
        yield Container(Static(message, id="apply-message"))

    def on_key(self, event) -> None:  # type: ignore[override]
        if event.key.lower() == "y":
            self.dismiss(True)
        elif event.key.lower() == "n" or event.key == "escape":
            self.dismiss(False)


class DetailsScreen(ModalScreen[None]):
    def __init__(self, item: ShelfItem) -> None:
        super().__init__()
        self.item = item

    def compose(self) -> ComposeResult:
        message = (
            f"Title: {self.item.title}\n"
            f"Kind: {self.item.kind}\n"
            f"Size: {_format_size(self.item.size_bytes)}\n"
            f"Last Modified: {_format_date(self.item.last_modified)}\n"
            f"Status: {self.item.status}\n"
            f"Path: {self.item.path}\n\n"
            "Press [esc] to close."
        )
        yield Container(Static(message, id="details-message"))

    def on_key(self, event) -> None:  # type: ignore[override]
        if event.key == "escape" or event.key.lower() in {"q", "enter"}:
            self.dismiss(None)


class ShelfApp(App):
    CSS_PATH = None
    BINDINGS = [
        Binding("k", "mark_keep", "Keep"),
        Binding("d", "mark_delete", "Delete"),
        Binding("s", "mark_defer", "Defer"),
        Binding("enter", "details", "Details"),
        Binding("a", "apply", "Apply"),
        Binding("r", "rescan", "Rescan"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.state: ShelfState = ShelfState()
        self.items: list[ShelfItem] = []
        self.selected_item: ShelfItem | None = None
        self.header_text = Static("", id="shelf-header")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield self.header_text
        table = DataTable(id="shelf-table")
        table.add_column("Title", key="title", width=40)
        table.add_column("Kind", key="kind", width=6)
        table.add_column("Size", key="size", width=10)
        table.add_column("Last", key="last", width=12)
        table.add_column("Status", key="status", width=10)
        table.zebra_stripes = True
        yield table
        yield Footer()

    def on_mount(self) -> None:
        self.load_items()

    def load_items(self) -> None:
        self.items = scan_shelf()
        self.state = merge_scan(self.items)
        self.items = list(self.state.items.values())
        self.items.sort(key=lambda item: item.size_bytes, reverse=True)
        self.refresh_table()

    def refresh_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        total_size = 0
        for item in self.items:
            total_size += item.size_bytes
            table.add_row(
                item.title,
                item.kind.upper(),
                _format_size(item.size_bytes),
                _format_date(item.last_modified),
                item.status.upper(),
                key=item.item_id,
            )
        self.header_text.update(
            f"Shelf ({len(self.items)} items, {_format_size(total_size)})"
        )

    def _update_status(self, status: str) -> None:
        if not self.selected_item:
            return
        set_status(self.state, self.selected_item.item_id, status)
        self.selected_item = self.state.items[self.selected_item.item_id]
        self.items = list(self.state.items.values())
        self.items.sort(key=lambda item: item.size_bytes, reverse=True)
        self.refresh_table()

    def action_mark_keep(self) -> None:
        self._update_status("keep")

    def action_mark_delete(self) -> None:
        self._update_status("delete")

    def action_mark_defer(self) -> None:
        self._update_status("defer")

    def action_rescan(self) -> None:
        self.load_items()

    def action_apply(self) -> None:
        delete_items = [item for item in self.items if item.status == "delete"]
        if not delete_items:
            self.notify("No items marked for deletion.", severity="warning")
            return
        total_size = sum(item.size_bytes for item in delete_items)
        self.push_screen(ApplyConfirmation(len(delete_items), total_size), self._apply_confirmed)

    def action_details(self) -> None:
        if not self.selected_item:
            self.notify("No item selected.", severity="warning")
            return
        self.push_screen(DetailsScreen(self.selected_item))

    def _apply_confirmed(self, confirmed: bool) -> None:
        if not confirmed:
            return
        roots = resolve_roots()
        results = apply_deletions(self.items, roots, dry_run=False)
        deleted = [result for result in results if result.deleted]
        for result in results:
            if result.deleted:
                set_status(self.state, result.item.item_id, "deleted")
        self.notify(f"Deleted {len(deleted)} item(s).")
        self.load_items()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:  # type: ignore[override]
        item_id = getattr(event.row_key, "value", None) or str(event.row_key)
        self.selected_item = self.state.items.get(item_id)


if __name__ == "__main__":
    ShelfApp().run()
