"""
Cosmic Scout — cosmos/_links_section.py  (v1.1.0 — Monday 9 November 2026)

The "Further Reading" card shared by every Cosmos tab: one button per link with
a status dot, plus Edit links (cosmos/_sources_dialog.py) and Check links.
Links come from AppState.links(key): the active profile's own list for that tab,
else the shipped defaults. With no profile, the defaults show and open, but
editing and checking are off.

Check links is the only network use here, and runs only when pressed
(cosmos/links.py).
"""

from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6 import sip

from ui.theme import LIGHT
from cosmos import links as L

_RUNNING = set()        # live LinkChecker threads (kept off the widget tree, so a
                        # page rebuilt mid-check never destroys a running thread)


def _dot(status):
    colour, tip = L.STATUS_DOTS.get(status, L.STATUS_DOTS[None])
    d = QLabel("●")
    d.setFixedWidth(16)
    d.setStyleSheet("color:%s;font-size:13px;" % colour)
    d.setToolTip(tip)
    return d


def build_links_card(state, page, key, card, note):
    """Return the Further Reading card for tab `key`. `card` is the page's own
    card factory, `note` its one-line intro."""
    c = card()
    cl = QVBoxLayout(c)
    cl.setContentsMargins(20, 16, 20, 18)
    cl.setSpacing(10)

    head = QHBoxLayout()
    h = QLabel("Further Reading")
    h.setStyleSheet("font-size:14px;font-weight:bold;color:%s;" % LIGHT["text"])
    head.addWidget(h)
    head.addStretch(1)
    check_btn = QPushButton("Check links")
    edit_btn = QPushButton("Edit links")
    head.addWidget(check_btn)
    head.addWidget(edit_btn)
    cl.addLayout(head)

    intro = QLabel(note)
    intro.setWordWrap(True)
    intro.setStyleSheet("font-size:11px;color:%s;" % LIGHT["subtle"])
    cl.addWidget(intro)

    links_box = QVBoxLayout()
    links_box.setSpacing(6)
    cl.addLayout(links_box)

    status = QLabel("")
    status.setWordWrap(True)
    status.setStyleSheet("font-size:11px;color:%s;" % LIGHT["subtle"])
    cl.addWidget(status)

    editable = state.links_editable()
    for b in (check_btn, edit_btn):
        b.setEnabled(editable)
        if not editable:
            b.setToolTip("Create a profile to edit and check links")

    def render():
        while links_box.count():
            w = links_box.takeAt(0).widget()
            if w:
                w.deleteLater()
        items = state.links(key)
        dates = []
        for src in items:
            chk = state.link_check(src["url"])
            if chk.get("checked"):
                dates.append(chk["checked"])
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(4)
            rl.addWidget(_dot(chk.get("status")))
            b = QPushButton("%s  ↗" % src["name"])
            b.setStyleSheet("text-align:left;")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip(src["url"])
            b.clicked.connect(lambda _=False, u=src["url"]: QDesktopServices.openUrl(QUrl(u)))
            rl.addWidget(b, 1)
            links_box.addWidget(row)
        if not items:
            empty = QLabel("No links. Use Edit links to add some, or reset to the defaults.")
            empty.setStyleSheet("font-size:11px;color:%s;" % LIGHT["subtle"])
            links_box.addWidget(empty)
        check_btn.setEnabled(editable and bool(items))
        if not editable:
            status.setText("Create a profile to edit and check these links.")
        elif dates:
            status.setText("Last checked %s. Green: confirmed · amber: the site "
                           "refused the check, open it to confirm · red: no answer."
                           % max(dates))
        else:
            status.setText("Not checked yet. Check links contacts only these sites, "
                           "only when you press it.")

    def open_editor():
        from cosmos._sources_dialog import SourcesDialog
        if SourcesDialog(state, page, sources_key=key).exec():
            render()

    def run_check():
        urls = [x["url"] for x in state.links(key)]
        if not urls:
            return
        check_btn.setEnabled(False)
        check_btn.setText("Checking…")
        th = L.LinkChecker(urls)
        _RUNNING.add(th)

        def got_results(results):
            state.record_link_checks(results)
            if not sip.isdeleted(check_btn):
                check_btn.setText("Check links")
                render()

        def thread_ended():
            # release only once run() has returned: deleting a running QThread aborts
            _RUNNING.discard(th)
            th.deleteLater()

        th.done.connect(got_results)
        th.finished.connect(thread_ended)
        th.start()

    edit_btn.clicked.connect(open_editor)
    check_btn.clicked.connect(run_check)
    render()
    return c
