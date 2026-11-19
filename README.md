# Qwen3.5-4B-Base weight mirror

Tools for packaging and distributing the unmodified [Qwen/Qwen3.5-4B-Base](https://huggingface.co/Qwen/Qwen3.5-4B-Base) model via GitHub Release assets.

> **Status:** The scripts are provided here. **No model weights have been uploaded to Releases yet.** Until a release is published, the `download` command has nothing to retrieve.

## For the publisher

Prerequisites: Python 3.10+, enough free disk space for the original files, a ZIP copy and split chunks, [Hugging Face CLI](https://huggingface.co/docs/huggingface_hub/guides/cli), and [GitHub CLI](https://cli.github.com/) authenticated with permission to publish Releases.

```bash
python -m pip install -U huggingface_hub
hf download Qwen/Qwen3.5-4B-Base --local-dir models/Qwen3.5-4B-Base

# Include the exact upstream license and notice files in the downloaded snapshot.
python scripts/weights.py pack models/Qwen3.5-4B-Base --out dist --chunk-mib 1024

# Inspect dist/manifest.json and then publish the chunks.
gh auth login
gh release create qwen3.5-4b-base-v1 dist/manifest.json dist/*.part* \
  --repo caderea/qwen3.5-4b-weights \
  --title 'Qwen3.5-4B-Base weights' \
  --notes 'Unmodified model mirror; see upstream model card and Apache-2.0 license.'
```

**Do not use `git add` on the model weights, ZIP or chunks.** They belong to Release assets, not Git history. A publication should be based on one pinned upstream revision to avoid mixing snapshots.

## On another computer

```bash
git clone https://github.com/caderea/qwen3.5-4b-weights.git
cd qwen3.5-4b-weights
python scripts/weights.py download --tag qwen3.5-4b-base-v1 --out ./models/Qwen3.5-4B-Base
```

The download command obtains the manifest and chunks from the named GitHub Release, verifies all SHA-256 checksums, and reconstructs the model directory. Re-running the command skips already valid chunks.

To reconstruct from already downloaded local chunks:

```bash
python scripts/weights.py restore dist/manifest.json --parts-dir dist --out ./models/Qwen3.5-4B-Base
```

The scripts use only Python's standard library. They preserve the original model files and check their hashes.

## Attribution and license

Original model: [Qwen/Qwen3.5-4B-Base](https://huggingface.co/Qwen/Qwen3.5-4B-Base), published by the Qwen team under **Apache License 2.0**. This project is an independent redistribution utility, not an official Qwen repository. Keep original LICENSE/NOTICE and any required attribution with the model. Review the upstream license before publishing.

The source code in this repository does **not** include the model weights. The base model alone does not include the separate Kev-4B adapter needed by [Kev](https://github.com/jaredpalmer/kev).

## Notes

- GitHub Release asset files must be smaller than 2 GiB. The default chunk size is 1 GiB.
- This format temporarily uses extra disk space while packaging. For use on a machine with limited free disk space, download directly from Hugging Face instead.
- It is often simpler to use `hf download Qwen/Qwen3.5-4B-Base` directly on each computer; this repository is for users who specifically want GitHub-based distribution.
