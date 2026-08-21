from __future__ import print_function

import json
import os
import threading

class TXRMFileWatcher(object):
    def __init__(self, processor, config, stop_event=None, status_callback=None):
        self.processor = processor
        self.config = config.config
        self.stop_event = stop_event or threading.Event()
        self.status_callback = status_callback
        self.processed_files = self._load_processed()
        self.pending_path = None

    def _status(self, message):
        if self.status_callback:
            self.status_callback(message)
        else:
            print(message)

    def _load_processed(self):
        path = self.config.get("processed_files_log")
        if not path or not os.path.exists(path):
            return set()
        try:
            with open(path, "r") as handle:
                return set(json.load(handle))
        except (IOError, OSError, ValueError, TypeError):
            return set()

    def _save_processed(self):
        path = self.config.get("processed_files_log")
        if not path:
            return
        try:
            folder = os.path.dirname(path)
            if folder and not os.path.exists(folder):
                os.makedirs(folder)
            with open(path, "w") as handle:
                json.dump(sorted(self.processed_files), handle, indent=4)
        except (IOError, OSError, TypeError):
            pass

    def _find_new_files(self):
        for root, dirs, files in os.walk(self.config["watch_directory"]):
            dirs[:] = [
                name for name in dirs
                if name.lower() not in ("$recycle.bin", "metadata_output")
            ]

            for name in files:
                lower = name.lower()
                if not lower.endswith(".txrm") or "drift" in lower:
                    continue

                path = os.path.normpath(os.path.join(root, name))
                if path not in self.processed_files:
                    yield path

    def _retry_csv(self):
        if self.pending_path is None:
            return True

        csv_path = self.processor.save_cumulative_csv()
        if not csv_path:
            self._status("CSV update pending.")
            return False

        self.processed_files.add(self.pending_path)
        self._save_processed()
        self.pending_path = None
        self._status("Automatic detection active.")
        return True

    def _process_file(self, path):
        self._status("Processing...")

        if not self.processor.process_single_file(path):
            self._status("Automatic detection active.")
            return

        self.pending_path = path
        self._retry_csv()

    def watch(self):
        interval = self.config.get("polling_interval", 60)
        self._status("Automatic detection active.")

        while not self.stop_event.is_set():
            try:
                if self.pending_path is not None:
                    self._retry_csv()

                if self.pending_path is None:
                    for path in self._find_new_files():
                        if self.stop_event.is_set():
                            break
                        self._process_file(path)
                        if self.pending_path is not None:
                            break
            except (IOError, OSError, ValueError):
                pass

            if self.stop_event.wait(interval):
                break
