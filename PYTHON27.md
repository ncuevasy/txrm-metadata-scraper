## Python 2.7 & ZEISS Package
Install **64-bit Python 2.7** with Tkinter.

Find ZEISS files. They are usually located under:

```text
C:\Program Files\Carl Zeiss X-ray Microscopy\Xradia Versa\<version>\
```

Most are in or under `ScoutScan`.


```text
XradiaPy\
XradiaBasicDatasetAPI.py
_XradiaBasicDatasetAPI.pyd
```
```text
XrmBasicDatasetAPI.dll
XrmUtility.dll
XrmTypes.dll
sqlite3.dll
hdf5dll.dll
mkl_rt.dll
zlib1.dll
szip.dll
libIRON.dll
cudart64_101.dll
libReconCommonUtility.dll
libReconCommon.dll
JsonParsor.dll
libPrjDataPreprocessing.dll
libFDK.dll
```

Copy these into the root of your Python 2.7 `site-packages` folder, for example:

```text
C:\Python27.64\Lib\site-packages\
```

## `olefile`

The extractor uses `olefile` to read reconstruction settings directly from `.txrm` files.

Install version 0.47 with:

```bat
C:\Python27.64\python.exe -m pip install olefile==0.47
```

Official PyPI page:

https://pypi.org/project/olefile/0.47/#files

If the computer does not have internet access, download:

```text
olefile-0.47-py2.py3-none-any.whl
```

on another computer, transfer it, and install it with:

```bat
C:\Python27.64\python.exe -m pip install olefile-0.47-py2.py3-none-any.whl
```
