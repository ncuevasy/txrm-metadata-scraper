import os
import struct
import sys

from XradiaPy import Data

try:
    import olefile
except ImportError:
    olefile = None


class MetadataExtractor(object):
    def __init__(self):
        self.axis_names = []
        self.dataset = self._quiet_call(Data.XRMData.XrmBasicDataSet)

    def _quiet_call(self, func, *args):
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass

        saved_out = os.dup(1)
        saved_err = os.dup(2)
        null_fd = os.open(os.devnull, os.O_WRONLY)

        try:
            os.dup2(null_fd, 1)
            os.dup2(null_fd, 2)
            return func(*args)
        finally:
            os.dup2(saved_out, 1)
            os.dup2(saved_err, 2)
            os.close(saved_out)
            os.close(saved_err)
            os.close(null_fd)

    def get_basic_info(self):
        return {
            "file_name": self.dataset.GetName(),
            "initialized_correctly": self.dataset.IsInitializedCorrectly()
        }

    def get_machine_settings(self):
        return {
            "objective": self.dataset.GetObjective(),
            "pixel_size": self.dataset.GetPixelSize(),
            "power": self.dataset.GetPower(),
            "voltage": self.dataset.GetVoltage(),
            "filter": self.dataset.GetFilter(),
            "binning": self.dataset.GetBinning()
        }

    def get_image_properties(self):
        return {
            "height": self.dataset.GetHeight(),
            "width": self.dataset.GetWidth(),
            "total_projections": self.dataset.GetProjections()
        }

    def get_images_per_projection(self, tomo_point_index=0):
        getter = getattr(self.dataset, "GetImagesPerProjection", None)
        if getter is None:
            return ""
        try:
            return getter(tomo_point_index)
        except Exception:
            return ""

    def get_axis_positions(self, projection_idx):
        axis_data = {}
        for axis in self.axis_names:
            pos = self.dataset.GetAxisPosition(projection_idx, axis)
            axis_data["{0}_pos".format(axis.replace(" ", "_"))] = pos
        return axis_data

    def get_projection_data(self, projection_idx):
        data = {
            "projection_number": projection_idx,
            "date": self.dataset.GetDate(projection_idx),
            "detector_to_ra_distance": self.dataset.GetDetectorToRADistance(projection_idx),
            "source_to_ra_distance": self.dataset.GetSourceToRADistance(projection_idx),
            "exposure": self.dataset.GetExposure(projection_idx)
        }
        data.update(self.get_axis_positions(projection_idx))
        return data

    def _empty_reconstruction_settings(self):
        return {
            "beam_hardening": "",
            "beam_hardening_type": "",
            "smoothing_factor": "",
            "ring_removal": ""
        }

    def _read_reconstruction_streams(self, file_path):
        """
        Read the exact OLE streams proven by the standalone TXRM inspector.

        ReconSettings is preferred. AutoRecon is retained only as a fallback.
        """
        streams = {}

        if olefile is None:
            return streams

        ole = None
        try:
            ole = olefile.OleFileIO(file_path)

            wanted = (
                "BeamHardening",
                "BeamHardeningFileName",
                "ReconFilterSmoothFactor",
                "RemoveRingON",
            )

            for path in ole.listdir(streams=True, storages=False):
                if not path:
                    continue

                storage = path[0]
                field = path[-1]

                if storage not in ("ReconSettings", "AutoRecon"):
                    continue
                if field not in wanted:
                    continue

                try:
                    streams[(storage, field)] = ole.openstream(path).read()
                except Exception:
                    pass

        except Exception:
            return {}
        finally:
            if ole is not None:
                try:
                    ole.close()
                except Exception:
                    pass

        return streams

    def _get_reconstruction_raw(self, streams, field_name):
        raw = streams.get(("ReconSettings", field_name))
        if raw is not None:
            return raw
        return streams.get(("AutoRecon", field_name))

    def _decode_float(self, raw):
        if raw is None or len(raw) != 4:
            return ""
        try:
            return struct.unpack("<f", raw)[0]
        except Exception:
            return ""

    def _decode_bool(self, raw):
        if raw is None:
            return ""
        try:
            if len(raw) == 1:
                value = struct.unpack("<B", raw)[0]
            elif len(raw) == 4:
                value = struct.unpack("<i", raw)[0]
            else:
                return ""
            return "Yes" if value else "No"
        except Exception:
            return ""

    def _decode_text(self, raw):
        if not raw:
            return ""
        try:
            # These 260-byte ZEISS fields are null-terminated single-byte text.
            return raw.split(b"\x00", 1)[0].strip()
        except Exception:
            return ""

    def get_reconstruction_settings(self, file_path):
        settings = self._empty_reconstruction_settings()
        streams = self._read_reconstruction_streams(file_path)

        settings["beam_hardening"] = self._decode_float(
            self._get_reconstruction_raw(streams, "BeamHardening")
        )
        settings["beam_hardening_type"] = self._decode_text(
            self._get_reconstruction_raw(streams, "BeamHardeningFileName")
        )
        settings["smoothing_factor"] = self._decode_float(
            self._get_reconstruction_raw(streams, "ReconFilterSmoothFactor")
        )
        settings["ring_removal"] = self._decode_bool(
            self._get_reconstruction_raw(streams, "RemoveRingON")
        )

        return settings

    def _extract(self, file_path):
        original_file_path = str(file_path)
        xradia_file_path = original_file_path.replace("\\", "/")

        self.dataset = Data.XRMData.XrmBasicDataSet()
        self.dataset.ReadFile(xradia_file_path)

        if not self.dataset.IsInitializedCorrectly():
            return None

        self.axis_names = self.dataset.GetAxesNames()

        metadata = {
            "basic_info": self.get_basic_info(),
            "machine_settings": self.get_machine_settings(),
            "image_properties": self.get_image_properties(),
            "detector_info": {
                "images_per_projection": self.get_images_per_projection()
            },
            "reconstruction_settings": self.get_reconstruction_settings(
                original_file_path
            ),
            "projection_data": []
        }

        num_projections = metadata["image_properties"]["total_projections"]

        if num_projections > 0:
            metadata["projection_data"].append(self.get_projection_data(0))

        if num_projections > 1:
            metadata["projection_data"].append(
                self.get_projection_data(num_projections - 1)
            )

        return metadata

    def get_complete_metadata(self, file_path):
        try:
            return self._quiet_call(self._extract, file_path)
        except Exception:
            return None
