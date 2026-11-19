# Qwen3.5-4B-Base weight mirror

Tools for packaging and distributing the unmodified [Qwen/Qwen3.5-4B-Base](https://huggingface.co/Qwen/Qwen3.5-4B-Base) model via GitHub Release assets.

> **Status:** The scripts are provided here. **No model weights have been uploaded to Releases yet.** Until a release is published, the `download` command has nothing to retrieve.

## Publish without using local disk (recommended)

This repository includes a **manually triggered GitHub Actions workflow**, so you can publish model weights without downloading them to your Mac:

1. Open [Actions → Publish Qwen3.5-4B-Base weight chunks](https://github.com/caderea/qwen3.5-4b-weights/actions/workflows/publish-weights.yml).
2. Click **Run workflow**, keep the default revision (`main`, which is resolved to a pinned model commit SHA), and choose release tag `qwen3.5-4b-base-v1`.
3. The workflow streams model files from Hugging Face into ~1 GiB GitHub Release chunks without keeping a full copy of the model or ZIP. It verifies hashes and publishes the manifest and chunk assets.
4. Check [Releases](https://github.com/caderea/qwen3.5-4b-weights/releases) to confirm successful publication.

**Important:** GitHub-hosted runner disk limits, transfer failures, GitHub quotas, and asset upload errors can still prevent the publish. The workflow is manual to avoid unexpected large transfers. It refuses to overwrite an existing release. Verify the model's current upstream license and model card before making the public release.

## Local fallback

On a machine with considerably more free disk space, the older local workflow still works:

```bash
python -m pip install -U huggingface_hub
hf download Qwen/Qwen3.5-4B-Base --local-dir models/Qwen3.5-4B-Base
python scripts/weights.py pack models/Qwen3.5-4B-Base --out dist --chunk-mib 1024
gh release create qwen3.5-4b-base-v1 dist/manifest.json dist/*.part* \
  --repo caderea/qwen3.5-4b-weights \
  --title 'Qwen3.5-4B-Base weights'
```

**Do not commit weights or chunks to Git history.** A release is required before the download command works.

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
- The GitHub Actions streaming publisher stores only output chunks, not source model files or a complete ZIP. The local fallback consumes much more disk space.
- It is often simpler to use `hf download Qwen/Qwen3.5-4B-Base` directly on each computer; this repository is for users who specifically want GitHub-based distribution.
