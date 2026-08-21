TXRM METADATA EXTRACTOR
This project is based on original code developed by John True. This version includes subsequent modifications updates by Naia Cuevas Yaraure.

AUTOMATIC MODE

1. Open main_gui.pyw.
2. Choose Automatic Detection.
3. Select the folder to watch.
4. Click Start and keep the GUI open.

Output:

    <selected folder>\metadata_output\MMDDYYYY.csv
    <selected folder>\metadata_output\processed_files.json

The CSV is cumulative. processed_files.json prevents duplicate processing.
Drift files, $RECYCLE.BIN, and metadata_output are skipped.

A backup copy of the automatic CSV is also attempted at the configured network
backup location. If that location is unavailable, the main CSV is still kept.

MANUAL MODE

1. Open main_gui.pyw.
2. Choose Manual Processing.
3. Select a folder.
4. Click Start.

Output:

    <selected folder>\manual-MMDDYYYY.csv

Manual mode runs once and does not change the automatic processing history.
