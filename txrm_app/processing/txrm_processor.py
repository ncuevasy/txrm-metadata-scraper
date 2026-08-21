from __future__ import print_function

import csv
import os
import shutil
from datetime import datetime
from txrm_app.metadata.metadata_extractor import MetadataExtractor


class TXRMProcessor(object):
    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.path.join(os.getcwd(), "metadata_output")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self.all_metadata = []
        self.backup_dir = r"\\VERSA542\versa542data\Scheiffele\backup_metadata"
        self.metadata_extractor = MetadataExtractor()

    def save_metadata_txt(self, metadata, file_path):
        txt_path = os.path.splitext(file_path)[0] + "_metadata.txt"
        try:
            with open(txt_path, "w") as handle:
                handle.write("TXRM File Metadata\n{0}\n\n".format("=" * 50))

                for title, key in (
                    ("Basic Information", "basic_info"),
                    ("Machine Settings", "machine_settings"),
                    ("Image Properties", "image_properties"),
                    ("Detector Information", "detector_info"),
                    ("Reconstruction Settings", "reconstruction_settings"),
                ):
                    handle.write("{0}:\n{1}\n".format(title, "-" * 20))
                    for name, value in metadata.get(key, {}).items():
                        handle.write("{0}: {1}\n".format(name, value))
                    handle.write("\n")

                projections = metadata.get("projection_data") or []
                handle.write("Projection Data Summary:\n{0}\n".format("-" * 20))
                if projections:
                    first, last = projections[0], projections[-1]
                    handle.write("Total Projections: {0}\n".format(
                        metadata.get("image_properties", {}).get("total_projections", "")
                    ))
                    handle.write("First Projection Date: {0}\n".format(first.get("date", "")))
                    handle.write("Last Projection Date: {0}\n\n".format(last.get("date", "")))
                    for label, projection in (("First", first), ("Last", last)):
                        handle.write("{0} Projection Axis Positions:\n".format(label))
                        for name, value in projection.items():
                            if "_pos" in name:
                                handle.write("{0}: {1}\n".format(name, value))
                        handle.write("\n")
            return True
        except (IOError, OSError, UnicodeError, TypeError):
            return False

    def _get_file_name(self, metadata):
        return os.path.splitext(os.path.basename(metadata.get("file_path", "")))[0]

    def _get_file_path(self, metadata):
        return metadata.get("file_path", "")

    def _get_file_hyperlink(self, metadata):
        path = metadata.get("file_path", "")
        if not path:
            return ""
        url = "file:///{0}".format(path.replace("\\", "/").lstrip("/"))
        return '=HYPERLINK("{0}","Open File")'.format(url)

    def _calculate_xray_power(self, metadata):
        settings = metadata.get("machine_settings", {})
        power = settings.get("power")
        if power not in (None, ""):
            return str(power)
        try:
            voltage = float(settings.get("voltage", 0))
            current_ua = float(settings.get("current", 0))
            if voltage > 0 and current_ua > 0:
                return str(round((current_ua / 1000000.0) * voltage, 2))
        except (ValueError, TypeError):
            pass
        return ""

    def _calculate_xray_current(self, metadata):
        settings = metadata.get("machine_settings", {})
        current = settings.get("current")
        if current not in (None, ""):
            return str(current)
        try:
            power = float(settings.get("power", 0))
            voltage = float(settings.get("voltage", 0))
            if voltage > 0:
                return str(round((power / voltage) * 1000000.0, 2))
        except (ValueError, TypeError):
            pass
        return ""

    def _format_reconstruction_number(self, metadata, key):
        value = metadata.get("reconstruction_settings", {}).get(key, "")
        if value in (None, ""):
            return ""
        try:
            return "{0:g}".format(float(value))
        except (ValueError, TypeError):
            return str(value)

    def _check_and_fix_pixel_size(self, pixel_size):
        try:
            value = float(pixel_size)
            if value > 100:
                return value / 1000.0
            if 0 < value < 0.01:
                return value * 1000.0
            return value
        except (ValueError, TypeError):
            return 0.0

    def _calculate_real_dimension(self, metadata, dimension):
        try:
            pixels = float(metadata.get("image_properties", {}).get(dimension, 0))
            pixel_size = self._check_and_fix_pixel_size(
                metadata.get("machine_settings", {}).get("pixel_size", 0)
            )
            if pixels > 0 and pixel_size > 0:
                return str(round(pixels * pixel_size, 2))
        except (ValueError, TypeError):
            pass
        return ""

    def _parse_date_string(self, value):
        if isinstance(value, datetime):
            return value
        if not value:
            return None

        value = str(value)
        for date_format in (
            "%m/%d/%Y %H:%M:%S.%f",
            "%m/%d/%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S.%f",
            "%d/%m/%Y %H:%M:%S",
        ):
            try:
                return datetime.strptime(value, date_format)
            except ValueError:
                pass
        return None

    def _calculate_scan_time(self, metadata):
        projections = metadata.get("projection_data") or []
        if not projections:
            return ""

        start = self._parse_date_string(projections[0].get("date"))
        end = self._parse_date_string(projections[-1].get("date"))
        if not start or not end:
            return ""

        seconds = int((end - start).total_seconds())
        if seconds < 0:
            return ""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "{0:02d}:{1:02d}:{2:02d}".format(hours, minutes, seconds)

    def _get_axis_position(self, metadata, axis_name, index):
        projections = metadata.get("projection_data") or []
        if not projections:
            return "0.0"
        try:
            value = projections[index].get(axis_name)
            return "{0:.6f}".format(float(value)) if value is not None else "0.0"
        except (ValueError, TypeError, IndexError):
            return "0.0"

    def _calculate_axis_range_new(self, metadata, axis_name):
        projections = metadata.get("projection_data") or []
        if not projections:
            return "0.0"
        try:
            start = float(projections[0].get(axis_name, 0))
            end = float(projections[-1].get(axis_name, 0))
            return "{0:.6f}".format(abs(end - start))
        except (ValueError, TypeError, IndexError):
            return "0.0"

    def _column_order(self):
        columns = [
            ("file_name", self._get_file_name),
            ("file_hyperlink", self._get_file_hyperlink),
            ("ct_voxel_size_um", lambda m: str(m.get("machine_settings", {}).get("pixel_size", "0.0"))),
            ("ct_objective", lambda m: str(m.get("machine_settings", {}).get("objective", ""))),
            ("ct_number_images", lambda m: str(m.get("image_properties", {}).get("total_projections", "0"))),
            ("ct_optical_magnification", lambda m: "yes" if str(m.get("machine_settings", {}).get("objective", "")).lower() in ("4x", "20x", "40x") else "no"),
            ("xray_tube_voltage", lambda m: str(m.get("machine_settings", {}).get("voltage", "0.0"))),
            ("xray_tube_power", self._calculate_xray_power),
            ("xray_tube_current", self._calculate_xray_current),
            ("xray_filter", lambda m: str(m.get("machine_settings", {}).get("filter", ""))),
            ("detector_binning", lambda m: str(m.get("machine_settings", {}).get("binning", ""))),
            ("detector_capture_time", lambda m: str((m.get("projection_data") or [{}])[0].get("exposure", "0.0"))),
            ("detector_averaging", lambda m: str(m.get("detector_info", {}).get("images_per_projection", 1))),
            ("beam_hardening", lambda m: self._format_reconstruction_number(m, "beam_hardening")),
            ("beam_hardening_type", lambda m: str(m.get("reconstruction_settings", {}).get("beam_hardening_type", ""))),
            ("smoothing_factor", lambda m: self._format_reconstruction_number(m, "smoothing_factor")),
            ("ring_removal", lambda m: str(m.get("reconstruction_settings", {}).get("ring_removal", ""))),
            ("image_width_pixels", lambda m: str(m.get("image_properties", {}).get("width", "0"))),
            ("image_height_pixels", lambda m: str(m.get("image_properties", {}).get("height", "0"))),
            ("image_width_real", lambda m: self._calculate_real_dimension(m, "width")),
            ("image_height_real", lambda m: self._calculate_real_dimension(m, "height")),
            ("scan_time", self._calculate_scan_time),
            ("start_time", lambda m: str((m.get("projection_data") or [{}])[0].get("date", ""))),
            ("end_time", lambda m: str((m.get("projection_data") or [{}])[-1].get("date", ""))),
            ("txrm_file_path", self._get_file_path),
            ("file_path", lambda m: os.path.dirname(m.get("file_path", ""))),
            ("acquisition_successful", lambda m: str(m.get("basic_info", {}).get("initialized_correctly", "False"))),
        ]

        axes = (
            ("Sample X", "Sample_X_pos"),
            ("Sample Y", "Sample_Y_pos"),
            ("Sample Z", "Sample_Z_pos"),
            ("Sample Theta", "Sample_Theta_pos"),
            ("Source X", "Source_X_pos"),
            ("Source Z", "Source_Z_pos"),
            ("Flat Panel Z", "Flat_Panel_Z_pos"),
            ("Flat Panel X", "Flat_Panel_X_pos"),
            ("Detector Z", "Detector_Z_pos"),
            ("CCD Z", "CCD_Z_pos"),
            ("CCD X", "CCD_X_pos"),
            ("MkIV Filter Wheel", "MkIV_Filter_Wheel_pos"),
            ("DCT", "DCT_pos"),
        )

        for display_name, metadata_name in axes:
            safe_name = display_name.lower().replace(" ", "_")
            columns.extend((
                ("{0}_start".format(safe_name), lambda m, name=metadata_name: self._get_axis_position(m, name, 0)),
                ("{0}_end".format(safe_name), lambda m, name=metadata_name: self._get_axis_position(m, name, -1)),
                ("{0}_range".format(safe_name), lambda m, name=metadata_name: self._calculate_axis_range_new(m, name)),
            ))
        return columns

    def _current_rows(self, columns):
        rows = []
        for metadata in self.all_metadata:
            if not isinstance(metadata, dict) or not metadata:
                continue
            row = {}
            for name, getter in columns:
                try:
                    value = getter(metadata)
                except (ValueError, TypeError, IndexError, KeyError, AttributeError):
                    value = ""
                row[name] = "{0:.6f}".format(value) if isinstance(value, float) else str(value or "")
            if any(row.values()):
                rows.append(row)
        return rows

    def _cumulative_csv_files(self):
        files = []
        try:
            names = os.listdir(self.output_dir)
        except (IOError, OSError):
            return files

        for name in names:
            stem, ext = os.path.splitext(name)
            if ext.lower() != ".csv":
                continue
            if (len(stem) == 8 and stem.isdigit()) or stem.startswith("cumulative_metadata_"):
                files.append(os.path.join(self.output_dir, name))
        return files

    def _row_date(self, row):
        value = self._parse_date_string(row.get("start_time", ""))
        return value or datetime.min

    def _read_csv_rows(self, path):
        if not path or not os.path.exists(path):
            return []
        try:
            with open(path, "rb") as handle:
                return list(csv.DictReader(handle))
        except (IOError, OSError, csv.Error):
            return []

    def _dedupe_rows(self, rows):
        by_path = {}
        without_path = []

        for row in rows:
            path = row.get("txrm_file_path", "")
            if path:
                key = os.path.normcase(os.path.normpath(path))
                by_path[key] = row
            else:
                without_path.append(row)

        return without_path + list(by_path.values())

    def _latest_existing_csv(self, current_path):
        candidates = [
            path for path in self._cumulative_csv_files()
            if os.path.normcase(path) != os.path.normcase(current_path)
        ]
        if not candidates:
            return None

        def modified(path):
            try:
                return os.path.getmtime(path)
            except OSError:
                return 0

        return max(candidates, key=modified)

    def _remove_old_csvs(self, current_path):
        for path in self._cumulative_csv_files():
            if os.path.normcase(path) == os.path.normcase(current_path):
                continue
            try:
                os.remove(path)
            except OSError:
                pass

    def _backup_csv(self, csv_path):
        try:
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)

            backup_path = os.path.join(
                self.backup_dir,
                os.path.basename(csv_path)
            )
            shutil.copy2(csv_path, backup_path)

            for name in os.listdir(self.backup_dir):
                stem, ext = os.path.splitext(name)
                if ext.lower() != ".csv":
                    continue
                if len(stem) == 8 and stem.isdigit():
                    path = os.path.join(self.backup_dir, name)
                    if os.path.normcase(path) != os.path.normcase(backup_path):
                        try:
                            os.remove(path)
                        except OSError:
                            pass
        except (IOError, OSError):
            pass

    def save_cumulative_csv(self):
        if not self.all_metadata:
            return False

        columns = self._column_order()
        fieldnames = [name for name, _ in columns]
        new_rows = self._current_rows(columns)
        if not new_rows:
            return False

        csv_name = datetime.now().strftime("%m%d%Y") + ".csv"
        csv_path = os.path.join(self.output_dir, csv_name)

        source_path = csv_path if os.path.exists(csv_path) else self._latest_existing_csv(csv_path)
        rows = self._read_csv_rows(source_path)
        rows.extend(new_rows)
        rows = self._dedupe_rows(rows)
        rows.sort(key=self._row_date, reverse=True)

        try:
            with open(csv_path, "wb") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=fieldnames,
                    extrasaction="ignore",
                    lineterminator="\n"
                )
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
        except (IOError, OSError, csv.Error):
            return False

        self.all_metadata = []
        self._remove_old_csvs(csv_path)
        self._backup_csv(csv_path)
        return csv_path

    def save_manual_csv(self):
        if not self.all_metadata:
            return False

        columns = self._column_order()
        fieldnames = [name for name, _ in columns]
        rows = self._current_rows(columns)
        if not rows:
            return False

        rows = self._dedupe_rows(rows)
        rows.sort(key=self._row_date, reverse=True)

        csv_name = "manual-{0}.csv".format(datetime.now().strftime("%m%d%Y"))
        csv_path = os.path.join(self.output_dir, csv_name)

        try:
            with open(csv_path, "wb") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=fieldnames,
                    extrasaction="ignore",
                    lineterminator="\n"
                )
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
        except (IOError, OSError, csv.Error):
            return False

        self.all_metadata = []
        return csv_path

    def process_single_file(self, file_path):
        try:
            metadata = self.metadata_extractor.get_complete_metadata(file_path)
            if not metadata:
                return False

            metadata["file_path"] = file_path
            metadata["is_drift_file"] = "drift" in os.path.basename(file_path).lower()

            self.save_metadata_txt(metadata, file_path)
            self.all_metadata.append(metadata)
            return True

        except (IOError, OSError, ValueError, TypeError):
            return False
