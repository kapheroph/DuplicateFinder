# Future Ideas

Nothing here is required for v1.0. These are intentionally parked ideas so the finished app does not grow just because it can.

## High-value, low-risk

### Rotate Left / Rotate Right

Useful for scanned photos with incorrect orientation. Prefer explicit manual rotation first. If editing files directly, preserve a safe backup or use non-destructive handling.

### Better visual comparison

For Similar groups, add one of:

- A/B flip button;
- draggable before/after slider;
- aligned overlay with adjustable opacity;
- highlighted crop/frame differences.

This may be more useful than making the similarity model more complicated.

### Version / About dialog

Show application name, version, and the safety promise. This is handy when helping someone remotely.

## If recursive use becomes important

The v1 quarantine model moves files into one quarantine folder and restores them to the scan root. If users regularly scan nested directory trees, add a persistent quarantine manifest or preserve relative directory structure so restoration can return each file to its exact original folder.

A manifest could record:

- original relative path;
- quarantine path;
- move time;
- file size;
- optional hash for integrity checking.

Restoration should continue to refuse overwrites.

## Similarity improvements

Only pursue these if real photos show that dHash is missing useful cases or producing too many false positives:

- pHash or wavelet hash;
- image embeddings;
- feature matching for crops and rescans;
- alignment before comparison;
- configurable similarity sensitivity in the UI.

Keep the current simple dHash path available even if a more advanced option is added.

## Features to approach cautiously

### Permanent delete

The absence of a delete button is part of the v1 safety design. If deletion is ever introduced, hide it behind an explicit advanced setting and multiple confirmations, or leave deletion to Windows Explorer.

### Automatic quarantine

Avoid automatically moving a file solely because it receives a technical `Suggested keep` comparison. The user should remain the final decision-maker.

### Editing originals

Rotation, metadata cleanup, compression, or image enhancement can alter the source file. Any such feature should have explicit confirmation and a clear recovery path.
