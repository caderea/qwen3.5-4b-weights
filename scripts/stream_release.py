#!/usr/bin/env python3
"""Stream a pinned Hugging Face model snapshot into split GitHub Release assets."""
import argparse
import hashlib
import io
import json
import os
import subprocess
from pathlib import Path
import zipfile


class ChunkWriter(io.RawIOBase):
    def __init__(self, out, chunk_bytes, on_part=None):
        self.out = Path(out)
        self.on_part = on_part
        self.limit = chunk_bytes
        self.total = 0
        self.parts = []
        self.current = None
        self.part_size = 0
        self.part_hash = None
        self.archive_hash = hashlib.sha256()
        self.finalized = False

    def writable(self):
        return True

    def tell(self):
        return self.total

    def _start(self):
        name = f"weights.zip.part{len(self.parts):04d}"
        self.current = (self.out / name).open("wb")
        self.current_name = name
        self.part_size = 0
        self.part_hash = hashlib.sha256()

    def _finish(self):
        if self.current is None:
            return
        self.current.close()
        item = {"name": self.current_name, "size": self.part_size,
                "sha256": self.part_hash.hexdigest()}
        if self.on_part:
            self.on_part(self.out / self.current_name)
        self.parts.append(item)
        self.current = None

    def write(self, b):
        if self.finalized:
            raise ValueError("Already finalized")
        view = memoryview(b)
        length = len(view)
        offset = 0
        while offset < length:
            if self.current is None:
                self._start()
            n = min(length - offset, self.limit - self.part_size)
            block = view[offset:offset + n]
            self.current.write(block)
            self.archive_hash.update(block)
            self.part_hash.update(block)
            self.total += n
            self.part_size += n
            offset += n
            if self.part_size == self.limit:
                self._finish()
        return length

    def flush(self):
        if self.current is not None:
            self.current.flush()

    def finalize(self):
        self._finish()
        self.finalized = True


def build_archive(entries, stream_file, out, chunk_mib=1024, on_part=None, source='Qwen/Qwen3.5-4B-Base'):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    limit = chunk_mib * 1024 * 1024
    if not 0 < limit < 2 * 1024**3:
        raise ValueError("Chunk size must be below 2 GiB")
    writer = ChunkWriter(out, limit, on_part=on_part)
    records = []
    with zipfile.ZipFile(writer, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for entry in entries:
            path = entry["path"]
            if not path or path.startswith("/") or ".." in Path(path).parts or "\\" in path:
                raise ValueError(f"Unsafe path: {path}")
            sha = hashlib.sha256()
            size = 0
            info = zipfile.ZipInfo(path)
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o644 << 16
            with archive.open(info, "w", force_zip64=True) as dest:
                for block in stream_file(entry):
                    dest.write(block)
                    sha.update(block)
                    size += len(block)
            if entry.get("size") is not None and size != entry["size"]:
                raise ValueError(f"Size mismatch for {path}")
            if entry.get("sha256") and sha.hexdigest() != entry["sha256"]:
                raise ValueError(f"SHA256 mismatch for {path}")
            records.append({"path": path, "size": size, "sha256": sha.hexdigest()})
            print(f"Packaged {path} ({size} bytes)", flush=True)
    writer.finalize()
    return {"format": 1, "source": source,
            "archive": {"name": "weights.zip", "size": writer.total,
                        "sha256": writer.archive_hash.hexdigest()},
            "files": records, "parts": writer.parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="Qwen/Qwen3.5-4B-Base")
    parser.add_argument("--revision", default="main")
    parser.add_argument("--out", default="dist")
    parser.add_argument("--chunk-mib", type=int, default=1024)
    parser.add_argument("--release-tag", help="Upload chunks to draft release, deleting local copies")
    args = parser.parse_args()
    from huggingface_hub import HfApi, hf_hub_url
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    api = HfApi()
    revision = api.model_info(args.repo, revision=args.revision).sha
    tree = list(api.list_repo_tree(args.repo, recursive=True, revision=revision))
    entries = []
    for item in tree:
        if item.__class__.__name__ != "RepoFile":
            continue
        lfs = getattr(item, "lfs", None)
        entries.append({"path": item.path, "size": item.size,
                        "sha256": (lfs or {}).get("sha256") if isinstance(lfs, dict) else None})
    entries.sort(key=lambda e: e["path"])
    if not entries:
        raise RuntimeError("No model files found")
    print(f"Pinned revision: {revision}; {len(entries)} files", flush=True)
    session = requests.Session()
    retry = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))

    def stream(entry):
        url = hf_hub_url(args.repo, entry["path"], revision=revision)
        with session.get(url, stream=True, timeout=(30, 300)) as response:
            response.raise_for_status()
            yield from (b for b in response.iter_content(4 * 1024 * 1024) if b)

    def upload_part(part):
        print(f"Uploading {part.name} to release {args.release_tag}", flush=True)
        subprocess.run(["gh", "release", "upload", args.release_tag, str(part),
                        "--repo", os.environ["GITHUB_REPOSITORY"]], check=True)
        part.unlink()

    manifest = build_archive(entries, stream, args.out, args.chunk_mib,
                             on_part=upload_part if args.release_tag else None,
                             source=args.repo)
    manifest["revision"] = revision
    (Path(args.out) / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if args.release_tag:
        subprocess.run(["gh", "release", "upload", args.release_tag,
                        str(Path(args.out) / "manifest.json"),
                        "--repo", os.environ["GITHUB_REPOSITORY"]], check=True)
    print(f"Wrote {len(manifest['parts'])} chunks; total {manifest['archive']['size']} bytes", flush=True)


if __name__ == "__main__":
    main()
