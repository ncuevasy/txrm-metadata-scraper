## Automatic Mode

1. Open `main_gui.pyw`.
2. Choose **Automatic Detection**.
3. Select the folder to watch.
4. Click **Start** and keep the GUI open.

### Output

```text
<selected folder>\metadata_output\MMDDYYYY.csv
<selected folder>\metadata_output\processed_files.json
```

The CSV is cumulative. `processed_files.json` prevents duplicate processing.

Drift files, `$RECYCLE.BIN`, and `metadata_output` are skipped.

A backup copy of the automatic CSV is also attempted at the configured network backup location. If that location is unavailable, the main CSV is still kept.

### Backup Location

Edit `self.backup_dir` on line 17 of `txrm_app/processing/txrm_processor.py`:

```python
self.backup_dir = r"..."
```

## Manual Mode

1. Open `main_gui.pyw`.
2. Choose **Manual Processing**.
3. Select a folder.
4. Click **Start**.

### Output

```text
<selected folder>\manual-MMDDYYYY.csv
```

Manual mode runs once and does not change the automatic processing history.
