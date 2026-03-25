"""Step-by-step tutorial body + bottom action bar (timer lives in app header)."""
from __future__ import annotations

from typing import Any, Callable, Dict, List

import customtkinter as ctk

from gui.tutorial_session import TutorialNavigator


class TutorialPlayScreen(ctk.CTkFrame):
    """
    Renders one step at a time. ``refresh`` pulls from ``TutorialNavigator``.
    """

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkFrame,
        *,
        on_back: Callable[[], None],
        on_confirm: Callable[[], None],
        on_next: Callable[[], None],
        on_pause_resume: Callable[[], None],
        on_skip: Callable[[], None],
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._on_back = on_back
        self._on_confirm = on_confirm
        self._on_next = on_next
        self._on_pause_resume = on_pause_resume
        self._on_skip = on_skip

        self._profile_strip = ctk.CTkFrame(self, height=6, corner_radius=0)
        self._profile_strip.pack(fill="x", pady=(0, 8))

        self._sub_title = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=26, weight="bold"),
            anchor="w",
            justify="left",
        )
        self._sub_title.pack(fill="x", padx=16, pady=(4, 4))

        self._objective = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=16),
            text_color=("gray10", "gray85"),
            anchor="w",
            justify="left",
            wraplength=860,
        )
        self._objective.pack(fill="x", padx=16, pady=(0, 4))

        self._summary = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=14),
            text_color="gray",
            anchor="w",
            justify="left",
            wraplength=860,
        )
        self._summary.pack(fill="x", padx=16, pady=(0, 8))

        self._phase_row = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#7d6608", "#f7dc6f"),
            anchor="w",
        )
        self._phase_row.pack(fill="x", padx=16, pady=(0, 4))

        self._step_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
            justify="left",
            wraplength=860,
        )
        self._step_label.pack(fill="x", padx=16, pady=(0, 6))

        self._instruction = ctk.CTkTextbox(
            self,
            height=220,
            font=ctk.CTkFont(size=18),
            wrap="word",
            activate_scrollbars=True,
        )
        self._instruction.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self._instruction.configure(state="disabled")

        self._hints_title = ctk.CTkLabel(
            self,
            text="Live hints",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        )
        self._hints_box = ctk.CTkTextbox(
            self,
            height=100,
            font=ctk.CTkFont(size=15),
            wrap="word",
            text_color=("gray15", "gray75"),
        )

        self._btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._btn_frame.pack(fill="x", padx=12, pady=(12, 16))

        specs: List[tuple[str, Callable[[], None]]] = [
            ("Back", self._on_back),
            ("Confirm", self._on_confirm),
            ("Next", self._on_next),
            ("Pause Timer", self._on_pause_resume),
            ("Skip subsection", self._on_skip),
        ]
        self._buttons: list[ctk.CTkButton] = []
        self._btn_actions = [fn for _, fn in specs]
        for i, (label, fn) in enumerate(specs):
            b = ctk.CTkButton(
                self._btn_frame,
                text=label,
                font=ctk.CTkFont(size=16, weight="bold"),
                height=44,
                width=150,
                command=lambda idx=i: self._click_button(idx),
            )
            b.grid(row=0, column=i, padx=4, pady=4, sticky="ew")
            self._buttons.append(b)
        for c in range(len(specs)):
            self._btn_frame.grid_columnconfigure(c, weight=1)

        self._focus_i = 2
        self._apply_button_focus()

    def _click_button(self, index: int) -> None:
        self._focus_i = index
        self._apply_button_focus()
        self._btn_actions[index]()

    def move(self, delta: int) -> None:
        n = len(self._buttons)
        self._focus_i = (self._focus_i + delta) % n
        self._apply_button_focus()

    def activate_focused(self) -> None:
        self._btn_actions[self._focus_i]()

    def set_pause_caption(self, paused: bool) -> None:
        self._buttons[3].configure(
            text="Resume Timer" if paused else "Pause Timer"
        )

    def _apply_button_focus(self) -> None:
        for i, b in enumerate(self._buttons):
            if i == self._focus_i:
                b.configure(fg_color=("#1f538d", "#1a4d7a"), border_width=2)
            else:
                b.configure(fg_color=("gray75", "gray25"), border_width=0)

    def refresh(
        self,
        nav: TutorialNavigator,
        task_title: str,
    ) -> None:
        """Fill fields from current navigator position."""
        sub = nav.current_subsection()
        step = nav.current_step()
        profile = (sub or {}).get("display_profile") or "standard"
        self._set_profile_strip(profile)

        if nav.is_final_segment():
            self._sub_title.configure(text=str(task_title))
            self._objective.configure(text="Final flow — follow each screen.")
            summ = ""
            if nav.final_flow:
                summ = str(nav.final_flow.get("title") or "")
            self._summary.configure(text=summ)
            hints: List[str] = []
            fc = (nav.final_flow or {}).get("final_checks") or []
            if fc:
                hints = [str(x) for x in fc]
        else:
            if sub:
                self._sub_title.configure(text=str(sub.get("title") or "—"))
                obj = str(sub.get("objective") or "")
                self._objective.configure(text=obj if obj else " ")
                summ = str(sub.get("overview_summary") or "")
                self._summary.configure(text=summ if summ else " ")
                hints = list(sub.get("live_hints") or [])
            else:
                self._sub_title.configure(text="—")
                self._objective.configure(text=" ")
                self._summary.configure(text=" ")
                hints = []

        if step:
            ph = step.get("_phase_title")
            ws = step.get("_workflow_style")
            extra = ""
            if step.get("loop_iteration") and step.get("loop_total"):
                extra = (
                    f"  (Repeat {step['loop_iteration']}/"
                    f"{step['loop_total']})"
                )
            if ph:
                self._phase_row.configure(
                    text=f"Phase: {ph}{extra}" + (f"  ·  {ws}" if ws else "")
                )
            elif extra:
                self._phase_row.configure(text=extra.strip())
            else:
                self._phase_row.configure(text="")

            self._step_label.configure(text=str(step.get("label") or "Step"))
            body = str(step.get("instruction") or "").strip()
            self._instruction.configure(state="normal")
            self._instruction.delete("1.0", "end")
            self._instruction.insert("1.0", body if body else "(No text)")
            self._instruction.configure(state="disabled")
        else:
            self._phase_row.configure(text="")
            self._step_label.configure(text="No steps")
            self._instruction.configure(state="normal")
            self._instruction.delete("1.0", "end")
            self._instruction.insert("1.0", "This section has no steps.")
            self._instruction.configure(state="disabled")

        show_hints = bool(hints) and self._should_show_hints(
            profile, step or {}
        )
        if show_hints:
            self._hints_title.pack(fill="x", padx=16, pady=(4, 0))
            self._hints_box.pack(fill="x", padx=16, pady=(4, 8))
            self._hints_box.configure(state="normal")
            self._hints_box.delete("1.0", "end")
            self._hints_box.insert("1.0", "\n".join(f"• {h}" for h in hints))
            self._hints_box.configure(state="disabled")
        else:
            self._hints_title.pack_forget()
            self._hints_box.pack_forget()

    def _set_profile_strip(self, profile: str) -> None:
        colors = {
            "continuous": ("#1e8449", "#58d68d"),
            "review": ("#6c3483", "#bb8fce"),
            "decision_heavy": ("#b7950b", "#f39c12"),
            "standard": ("#1f538d", "#5dade2"),
        }
        pair = colors.get(profile, colors["standard"])
        self._profile_strip.configure(fg_color=pair)

    @staticmethod
    def _should_show_hints(profile: str, step: Dict[str, Any]) -> bool:
        kind = step.get("_kind")
        if profile == "continuous":
            return kind not in ("intro", "completion")
        if kind == "instruction":
            return True
        return False
