"""Build an OpenBeken LittleFS image (OpenRTL8720D) holding the hub scripts.

The image is written to the WBRG1 at the LittleFS start address, next to the
OpenRTL8720D application, so the hub boots with autoexec.bat already in place
(LED/button pin roles, Zigbee TCP bridge, BLE proxy) instead of uploading the
scripts through the web UI afterwards.

Parameters come from OpenBeken 1.18.321 src/littlefs/our_lfs.[ch]:
  * RTL8720D, flash > 2 MiB: start 0x3C6000, size = flash size - 0x3C6000
  * RTL8720D, 2 MiB flash:   start 0x1F0000, size 0x10000
  * block 4096, read/prog 1, cache 16, lookahead 16, block_cycles 500
  * littlefs 2.4 core -> on-disk format 2.0
lfs_mount() compares block_count with the superblock, so the size must match
exactly or OpenBeken reformats the area and the scripts are lost.

Wi-Fi credentials, admin password and paired devices are NOT in this image;
they live in the OpenBeken config sector of each unit.

Usage:
    python build_lfs_image.py [--flash-mb 8] [--output-dir DIR] [files...]
Default files: autoexec.bat and wifi-recovery.bat next to this script.
"""

import argparse
import hashlib
from pathlib import Path

from littlefs import LittleFS

BLOCK_SIZE = 0x1000
DISK_VERSION_2_0 = 0x00020000


def layout(flash_mb):
    if flash_mb == 2:
        return 0x1F0000, 0x10000
    start = 0x3C6000
    return start, (flash_mb << 20) - start


def make_fs(block_count, image=None):
    kwargs = dict(block_size=BLOCK_SIZE, block_count=block_count, read_size=1, prog_size=1,
                  cache_size=16, lookahead_size=16, block_cycles=500,
                  disk_version=DISK_VERSION_2_0)
    if image is None:
        return LittleFS(**kwargs)
    fs = LittleFS(mount=False, **kwargs)
    fs.context.buffer = bytearray(image)
    fs.mount()
    return fs


def normalize(data):
    """OpenBeken scripts: no UTF-8 BOM, LF line endings, ASCII only."""
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    data = data.replace(b"\r\n", b"\n")
    data.decode("ascii")  # raises on non-ASCII so the device never sees mojibake
    return data


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--flash-mb", type=int, default=8, help="WBRG1 flash size in MiB (default 8)")
    parser.add_argument("--output-dir", type=Path, default=here)
    parser.add_argument("files", nargs="*", type=Path,
                        default=[here / "autoexec.bat", here / "wifi-recovery.bat"])
    args = parser.parse_args()

    start, size = layout(args.flash_mb)
    block_count = size // BLOCK_SIZE
    fs = make_fs(block_count)
    contents = {}
    for path in args.files:
        data = normalize(path.read_bytes())
        contents[path.name] = data
        with fs.open(path.name, "wb") as handle:
            handle.write(data)
    fs.unmount()
    image = bytes(fs.context.buffer)

    # Only the blocks littlefs used need to be written; the rest of the area may
    # keep old data, littlefs never reads blocks outside its metadata tree.
    used = [b for b in range(block_count) if image[b * BLOCK_SIZE:(b + 1) * BLOCK_SIZE] != b"\xff" * BLOCK_SIZE]
    trimmed = image[:(max(used) + 1) * BLOCK_SIZE]

    # Verify: mount what the device will see (trimmed image + erased tail).
    check = make_fs(block_count, trimmed + b"\xff" * (size - len(trimmed)))
    for name, data in contents.items():
        with check.open(name, "rb") as handle:
            if handle.read() != data:
                raise SystemExit(f"Verification failed for {name}")
    listed = sorted(check.listdir("/"))
    check.unmount()

    out = args.output_dir / f"OpenRTL8720D-lfs-{args.flash_mb}MB-at-0x{start:06X}.bin"
    out.write_bytes(trimmed)
    print(f"LittleFS {size:#x} bytes ({block_count} blocks) at {start:#x}, disk format 2.0")
    print(f"files: {', '.join(listed)}; blocks used: {used}")
    print(f"wrote {out.name}: {len(trimmed)} bytes, write at {start:#x}")
    print(f"SHA-256 {hashlib.sha256(trimmed).hexdigest()}")


if __name__ == "__main__":
    main()
