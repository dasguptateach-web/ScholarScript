import os
import re
import shutil
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from pathlib import Path
from datetime import datetime

from config_manager import load_config, save_config
from deploy_github import push_content_folder


class ScholarScriptApp:
    def __init__(self):
        self.cfg = load_config()
        self.watcher_running = False
        self.watcher_thread = None

        self.root = tk.Tk()
        self.root.title("ScholarScript Portable")
        self.root.geometry("780x560")
        self.root.minsize(640, 460)
        try:
            self.root.iconbitmap(default=os.path.join(os.path.dirname(__file__), "assets", "icon.ico"))
        except Exception:
            pass

        self._build_ui()
        self._apply_config()
        self.log("ScholarScript Portable v1.0 ready.")
        self.log(f"Drop folder: {self.cfg.get('drop_folder', 'Not set')}")
        self.log(f"Repository: {self.cfg.get('github_repo', 'Not set')}")
        self.log("")

    def _build_ui(self):
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Top toolbar
        toolbar = ttk.Frame(self.root, padding=6)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_columnconfigure(0, weight=1)

        self.status_label = ttk.Label(toolbar, text="● Stopped", font=("Segoe UI", 9))
        self.status_label.pack(side=tk.LEFT, padx=(0, 12))

        self.watch_btn = ttk.Button(toolbar, text="Start Watcher", command=self._toggle_watcher)
        self.watch_btn.pack(side=tk.LEFT, padx=2)

        self.process_btn = ttk.Button(toolbar, text="Process Now", command=self._process_now)
        self.process_btn.pack(side=tk.LEFT, padx=2)

        ttk.Button(toolbar, text="Open Drop Folder", command=self._open_drop).pack(side=tk.LEFT, padx=2)

        ttk.Button(toolbar, text="Save Settings", command=self._save_settings).pack(side=tk.RIGHT, padx=2)

        # Notebook (tabs)
        nb = ttk.Notebook(self.root)
        nb.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        # Log tab
        log_frame = ttk.Frame(nb)
        nb.add(log_frame, text="Activity Log")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        self.log_widget = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="white", state=tk.DISABLED
        )
        self.log_widget.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        ttk.Button(log_frame, text="Clear Log", command=self._clear_log).grid(row=1, column=0, pady=(0, 4))

        # Settings tab
        settings_frame = ttk.Frame(nb, padding=12)
        nb.add(settings_frame, text="Settings")
        settings_frame.grid_columnconfigure(1, weight=1)

        row = 0
        ttk.Label(settings_frame, text="GitHub Token:").grid(row=row, column=0, sticky="w", pady=3)
        self.token_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.token_var, show="*", width=50).grid(row=row, column=1, sticky="ew", padx=6)
        row += 1

        ttk.Label(settings_frame, text="Repository:").grid(row=row, column=0, sticky="w", pady=3)
        self.repo_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.repo_var, width=50).grid(row=row, column=1, sticky="ew", padx=6)
        ttk.Label(settings_frame, text="e.g. user/repo").grid(row=row, column=2, sticky="w", padx=4)
        row += 1

        ttk.Label(settings_frame, text="Branch:").grid(row=row, column=0, sticky="w", pady=3)
        self.branch_var = tk.StringVar(value="main")
        ttk.Entry(settings_frame, textvariable=self.branch_var, width=20).grid(row=row, column=1, sticky="w", padx=6)
        row += 1

        ttk.Label(settings_frame, text="Drop Folder:").grid(row=row, column=0, sticky="w", pady=3)
        self.drop_var = tk.StringVar()
        drop_frame = ttk.Frame(settings_frame)
        drop_frame.grid(row=row, column=1, sticky="ew", padx=6)
        drop_frame.grid_columnconfigure(0, weight=1)
        ttk.Entry(drop_frame, textvariable=self.drop_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(drop_frame, text="Browse...", command=self._browse_drop, width=10).grid(row=0, column=1, padx=(4, 0))
        row += 1

        self.auto_deploy_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Auto-deploy to GitHub after processing", variable=self.auto_deploy_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=6)
        row += 1

        # Test connection button
        ttk.Button(settings_frame, text="Test GitHub Connection", command=self._test_github).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1

        # Status info
        sep = ttk.Separator(settings_frame, orient="horizontal")
        sep.grid(row=row, column=0, columnspan=3, sticky="ew", pady=8)
        row += 1

        info_text = (
            "ScholarScript Portable v1.0\n"
            "Built from scholarscript package\n"
            "No Python or Git required on this machine.\n"
            "All processing is done locally; deployment uses GitHub API."
        )
        ttk.Label(settings_frame, text=info_text, foreground="#666").grid(
            row=row, column=0, columnspan=3, sticky="w", pady=4)

    def _apply_config(self):
        self.token_var.set(self.cfg.get("github_token", ""))
        self.repo_var.set(self.cfg.get("github_repo", ""))
        self.branch_var.set(self.cfg.get("github_branch", "main"))
        self.drop_var.set(self.cfg.get("drop_folder", ""))
        self.auto_deploy_var.set(self.cfg.get("auto_deploy", True))

    def _read_settings(self) -> dict:
        return {
            "github_token": self.token_var.get().strip(),
            "github_repo": self.repo_var.get().strip(),
            "github_branch": self.branch_var.get().strip() or "main",
            "drop_folder": self.drop_var.get().strip(),
            "auto_deploy": self.auto_deploy_var.get(),
        }

    def _save_settings(self):
        new_cfg = self._read_settings()
        self.cfg.update(new_cfg)
        save_config(self.cfg)
        self.log("Settings saved.")

    def _browse_drop(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(title="Select Drop Folder")
        if path:
            self.drop_var.set(path)

    def _test_github(self):
        token = self.token_var.get().strip()
        repo = self.repo_var.get().strip()
        if not token or not repo:
            messagebox.showwarning("Missing Info", "Enter both GitHub Token and Repository first.")
            return
        self.log("Testing GitHub connection...")
        from deploy_github import get_default_branch
        branch = get_default_branch(repo, token)
        if branch:
            self.log(f"OK: Connected to {repo}, default branch is '{branch}'")
            messagebox.showinfo("Success", f"Connected to {repo}\nDefault branch: {branch}")
        else:
            self.log("FAILED: Could not connect. Check token and repo.")
            messagebox.showerror("Error", "Could not connect. Check token and repo.")

    def _open_drop(self):
        folder = self.drop_var.get().strip()
        if folder and os.path.isdir(folder):
            os.startfile(folder)
        else:
            messagebox.showwarning("No Folder", "Drop folder does not exist yet.")

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.root.after(0, self._append_log, f"[{ts}] {msg}")

    def _append_log(self, msg: str):
        self.log_widget.configure(state=tk.NORMAL)
        self.log_widget.insert(tk.END, msg + "\n")
        self.log_widget.see(tk.END)
        self.log_widget.configure(state=tk.DISABLED)

    def _clear_log(self):
        self.log_widget.configure(state=tk.NORMAL)
        self.log_widget.delete("1.0", tk.END)
        self.log_widget.configure(state=tk.DISABLED)

    def _toggle_watcher(self):
        if self.watcher_running:
            self.watcher_running = False
            self.watch_btn.configure(text="Start Watcher")
            self.status_label.configure(text="● Stopped", foreground="#cc4444")
            self.log("Watcher stopped.")
        else:
            drop = self.drop_var.get().strip()
            if not drop:
                messagebox.showwarning("No Drop Folder", "Set a drop folder in Settings first.")
                return
            Path(drop).mkdir(parents=True, exist_ok=True)
            self.watcher_running = True
            self.watch_btn.configure(text="Stop Watcher")
            self.status_label.configure(text="● Watching", foreground="#44cc44")
            self.log(f"Watcher started on: {drop}")
            self.watcher_thread = threading.Thread(target=self._watcher_loop, daemon=True)
            self.watcher_thread.start()

    def _watcher_loop(self):
        drop = self.drop_var.get().strip()
        seen = set()
        while self.watcher_running:
            try:
                p = Path(drop)
                if p.exists():
                    for f in p.iterdir():
                        if f.is_file() and not f.name.startswith("_") and f.suffix.lower() in (".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".tex"):
                            if f.name not in seen:
                                seen.add(f.name)
                                self.log(f"New file detected: {f.name}")
                                self._process_single_file(f)
            except Exception as e:
                self.log(f"Watcher error: {e}")
            for _ in range(10):
                if not self.watcher_running:
                    break
                time.sleep(0.5)

    def _process_now(self):
        self.log("Manual processing triggered...")
        threading.Thread(target=self._process_all, daemon=True).start()

    def _process_single_file(self, f: Path):
        self.root.after(0, lambda: self.process_btn.configure(state=tk.DISABLED))
        try:
            self.log(f"Processing: {f.name}")
            project_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            uploads_dir = project_dir / "uploads"
            content_dir = project_dir / "content"
            uploads_dir.mkdir(parents=True, exist_ok=True)

            dest = uploads_dir / f.name
            shutil.copy2(str(f), str(dest))
            self.log(f"  Copied to uploads/")

            try:
                from scholarscript.ingestion import IngestionEngine
                from scholarscript import cli
                engine = IngestionEngine(uploads_dir, content_dir)
                results = engine.ingest_all()
                for r in results:
                    if r["status"] == "success":
                        self.log(f"  Ingested: {r['title']} -> {r['output']}")
                    else:
                        self.log(f"  FAILED: {r['file']} - {r.get('error', 'Unknown')}")
            except Exception as e:
                self.log(f"  Ingestion error: {e}")

            if self.auto_deploy_var.get():
                self._deploy(project_dir, content_dir)
            else:
                self.log("  Auto-deploy disabled. Files processed locally.")

            archive = f.parent / "_Processed"
            archive.mkdir(exist_ok=True)
            shutil.move(str(f), str(archive / f.name))
            self.log(f"  Archived to _Processed")

        except Exception as e:
            self.log(f"  ERROR processing {f.name}: {e}")
        finally:
            self.root.after(0, lambda: self.process_btn.configure(state=tk.NORMAL))

    def _process_all(self):
        self.root.after(0, lambda: self.process_btn.configure(state=tk.DISABLED))
        try:
            drop = self.drop_var.get().strip()
            if not drop:
                self.log("No drop folder set.")
                return
            p = Path(drop)
            if not p.exists():
                self.log("Drop folder does not exist.")
                return
            supported = (".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".tex")
            files = [f for f in p.iterdir() if f.is_file() and not f.name.startswith("_") and f.suffix.lower() in supported]
            if not files:
                self.log("No supported files found.")
                return
            self.log(f"Found {len(files)} file(s) to process.")
            for f in files:
                self._process_single_file(f)
        except Exception as e:
            self.log(f"Batch error: {e}")
        finally:
            self.root.after(0, lambda: self.process_btn.configure(state=tk.NORMAL))

    def _deploy(self, project_dir: Path, content_dir: Path):
        token = self.token_var.get().strip()
        repo = self.repo_var.get().strip()
        branch = self.branch_var.get().strip() or "main"
        if not token or not repo:
            self.log("  SKIP deploy: GitHub token or repo not configured.")
            return

        self.log("  Deploying to GitHub...")
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        msg = f"ScholarScript Portable auto-deploy {ts}"

        success = push_content_folder(
            repo=repo,
            branch=branch,
            content_dir=content_dir,
            message=msg,
            token=token,
            log_fn=lambda m: self.log(f"  {m}"),
        )
        if success:
            self.log("  Site will auto-deploy via GitHub Actions.")

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        if self.watcher_running:
            self.watcher_running = False
        self.root.destroy()
