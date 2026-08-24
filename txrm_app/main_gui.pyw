from __future__ import print_function

import os
import sys
import threading
import Queue

import Tkinter as tk
import tkFileDialog
import tkMessageBox
import ttk

if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from txrm_app.processing.txrm_processor import TXRMProcessor
from txrm_app.watcher.file_watcher import TXRMFileWatcher

class Config(object):
    def __init__(self, values):
        self.config = values


class TXRMApp(object):
    def __init__(self, root):
        self.root = root
        self.root.title("TXRM Metadata")
        self.root.resizable(False, False)

        self.mode = tk.StringVar(value="watch")
        self.directory = tk.StringVar()
        self.status = tk.StringVar(value="")
        self.queue = Queue.Queue()
        self.stop_event = threading.Event()
        self.running = False

        frame = tk.Frame(root, padx=18, pady=16)
        frame.pack()

        tk.Label(frame, text="TXRM Metadata", font=("Arial", 14, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10)
        )

        tk.Radiobutton(
            frame, text="Monitoring", variable=self.mode, value="watch"
        ).grid(row=1, column=0, sticky="w")

        tk.Radiobutton(
            frame, text="Manual", variable=self.mode, value="manual"
        ).grid(row=1, column=1, sticky="w")

        tk.Label(frame, text="Directory:").grid(row=2, column=0, sticky="w", pady=(12, 4))

        self.entry = tk.Entry(frame, textvariable=self.directory, width=58)
        self.entry.grid(row=3, column=0, columnspan=2, sticky="we")

        tk.Button(frame, text="Browse...", command=self.browse).grid(
            row=3, column=2, padx=(8, 0)
        )

        self.start_button = tk.Button(
            frame, text="Start", width=12, command=self.start, state="disabled"
        )
        self.start_button.grid(row=4, column=0, sticky="w", pady=(14, 0))

        self.stop_button = tk.Button(
            frame, text="Stop", width=12, command=self.stop, state="disabled"
        )
        self.stop_button.grid(row=4, column=1, sticky="w", pady=(14, 0))

        tk.Label(
            frame,
            textvariable=self.status,
            anchor="w",
            justify="left",
            wraplength=510
        ).grid(row=5, column=0, columnspan=3, sticky="we", pady=(14, 4))

        self.progress = ttk.Progressbar(frame, mode="indeterminate", length=510)
        self.progress.grid(row=6, column=0, columnspan=3, sticky="we", pady=(4, 4))

        tk.Label(
            frame,
            text="Keep this window open while monitoring!",
            fg="#9A6700"
        ).grid(row=7, column=0, columnspan=3, sticky="w", pady=(8, 0))

        self.directory.trace("w", self.update_start_state)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(150, self.read_queue)

    def browse(self):
        path = tkFileDialog.askdirectory()
        if path:
            self.directory.set(os.path.normpath(path))

    def update_start_state(self, *args):
        path = self.directory.get().strip().strip('"')
        state = "normal" if not self.running and os.path.isdir(path) else "disabled"
        self.start_button.config(state=state)

    def set_status(self, message):
        self.queue.put(message)

    def read_queue(self):
        try:
            while True:
                message = self.queue.get_nowait()
                self.status.set(message)
                if message == "Processing...":
                    self.progress.start(10)
                else:
                    self.progress.stop()
        except Queue.Empty:
            pass
        self.root.after(150, self.read_queue)

    def start(self):
        if self.running:
            return

        path = self.directory.get().strip().strip('"')
        if not os.path.isdir(path):
            return

        path = os.path.normpath(path)
        self.directory.set(path)
        self.stop_event.clear()
        self.running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

        target = self.run_manual if self.mode.get() == "manual" else self.run_watch
        thread = threading.Thread(target=target, args=(path,))
        thread.daemon = True
        thread.start()

    def finish(self, message):
        self.set_status(message)
        self.running = False
        self.root.after(0, self.update_start_state)
        self.root.after(0, lambda: self.stop_button.config(state="disabled"))

    def iter_txrm_files(self, path):
        for root, dirs, files in os.walk(path):
            dirs[:] = [
                name for name in dirs
                if name.lower() not in ("$recycle.bin", "metadata_output")
            ]
            for name in files:
                lower = name.lower()
                if lower.endswith(".txrm") and "drift" not in lower:
                    yield os.path.normpath(os.path.join(root, name))

    def run_manual(self, path):
        processor = TXRMProcessor(path)
        count = 0
        self.set_status("Processing...")

        for file_path in self.iter_txrm_files(path):
            if self.stop_event.is_set():
                self.finish("Stopped.")
                return

            if processor.process_single_file(file_path):
                count += 1

        if count == 0:
            self.finish("Manual processing complete. No TXRM files found.")
            return

        csv_path = processor.save_manual_csv()
        if not csv_path:
            self.finish("Manual CSV could not be saved.")
            return

        self.finish("Manual processing complete. {0} file(s) processed.".format(count))

    def run_watch(self, path):
        output_dir = os.path.join(path, "metadata_output")
        config = Config({
            "watch_directory": path,
            "polling_interval": 60,
            "cumulative_csv_path": output_dir,
            "processed_files_log": os.path.join(output_dir, "processed_files.json")
        })

        processor = TXRMProcessor(output_dir)
        watcher = TXRMFileWatcher(
            processor,
            config,
            stop_event=self.stop_event,
            status_callback=self.set_status
        )
        watcher.watch()
        self.finish("Stopped.")

    def stop(self):
        if self.running:
            self.status.set("Stopping...")
            self.progress.stop()
            self.stop_event.set()

    def close(self):
        if self.running:
            close_anyway = tkMessageBox.askyesno(
                "TXRM Metadata",
                "Closing this window stops processing. Close anyway?"
            )
            if not close_anyway:
                return
            self.stop_event.set()
        self.root.destroy()


def main():
    root = tk.Tk()
    TXRMApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
