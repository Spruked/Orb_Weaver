# C Drive Space Recovery Report

Date: 2026-06-04
Repo: `C:\dev\Desktop\Orb_Weaver`

## C Drive Status

- Drive: `C:`
- Label: `SSD Win10`
- File system: `NTFS`
- Total size: `435.64 GiB`
- Free space: `59.17 GiB`

## Primary Space Loss Source

The largest space consumer found was the WSL virtual disk:

`C:\Users\bryan\AppData\Local\wsl\{1a2bdb1c-fa51-478c-a337-28ebb0ca5681}\ext4.vhdx`

- Size: `123.4 GB`
- Created: `2026-05-11 3:28 PM`
- Modified: `2026-06-04`

This is the main item to revisit for recovery. Normal Windows temp/cache locations were small and do not explain the lost space.

## WSL Internal Usage

WSL distro:

- Name: `Ubuntu`
- State: `Running`
- Version: `2`

Linux filesystem usage:

- Root filesystem: `1007G`
- Used inside WSL: `112G`
- Available inside WSL: `845G`
- Use: `12%`

Largest WSL paths:

| Path | Size |
|---|---:|
| `/var/lib/containerd` | `51 GB` |
| `/var/lib/docker` | `8.3 GB` |
| `/home/bryan` | `45 GB` |
| `/usr` | `14 GB` |
| `/home/bryan/.cache/huggingface` | `6.6 GB` |
| `/home/bryan/Qwen3-TTS` | `5.6 GB` |
| `/home/bryan/py312` | `5.5 GB` |
| `/home/bryan/cochlear_processor_3.0` | `4.7 GB` |
| `/home/bryan/.ollama` | `2.2 GB` |
| `/home/bryan/.cache/whisper` | `1.9 GB` |

Large WSL files found:

| Date | Path | Approx Size |
|---|---|---:|
| `2026-06-03` | `/var/lib/containerd/io.containerd.content.v1.content/blobs/sha256/318d7c56d3df2b2036cadd414fca2c2d042301c59ebb076fd976763e3ea93134` | `3.16 GB` |
| `2026-05-30` | `/home/bryan/.cache/huggingface/hub/models--Qwen--Qwen3-TTS-12Hz-1.7B-VoiceDesign/blobs/391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522` | `3.57 GB` |
| `2026-05-28` | `/var/lib/containerd/io.containerd.content.v1.content/blobs/sha256/390d05bc3d2003801b3c93670e3e804ffb643c1c4eeb622af68ab9fe27bde883` | `2.85 GB` |
| `2026-05-30` | `/home/bryan/.cache/huggingface/hub/models--Qwen--Qwen3-TTS-12Hz-0.6B-Base/blobs/180b3b10eb1c9f1b4db7806d5475bae3071c0243c299d49926bab1da3b6946f6` | `1.70 GB` |
| `2026-05-12` | `/usr/local/lib/ollama/cuda_v12/libggml-cuda.so` | `1.67 GB` |
| `2026-05-28` | `/home/bryan/.cache/whisper/medium.pt` | `1.42 GB` |
| `2026-06-01` | `/home/bryan/.ollama/models/blobs/sha256-74701a8c35f6c8d9a4b91f3f3497643001d63e0c7a84e085bed452548fa88d45` | `1.23 GB` |

## Recent Large C Drive Additions

| Date | Path | Size |
|---|---|---:|
| `2026-06-03` | `C:\dev\Desktop\Orb_Weaver` | `1.11 GB` |
| `2026-06-03` | `C:\dev\Desktop\neilpatel_seo_crawler - Copy` | `0.84 GB` |
| `2026-06-03` | `C:\Users\bryan\AppData\Local\ms-playwright` | `0.67 GB` |
| `2026-05-24` | `C:\Users\bryan\AppData\Local\electron` | `0.52 GB` |
| `2026-05-21` | `C:\Program Files (x86)\Microsoft Visual Studio` | `3.88 GB` |
| `2026-05-21` | `C:\Program Files (x86)\Windows Kits` | `1.69 GB` |
| `2026-05-14` | `C:\dev\Desktop\PLATFORM` | `14.78 GB` |
| `2026-05-14` | `C:\dev\Desktop\PLATFORM ARCHIVE` | `8.32 GB` |
| `2026-05-14` | `C:\dev\Desktop\PLATFORM STAGING` | `5.5 GB` |
| `2026-05-11` | `C:\Users\bryan\AppData\Local\wsl` | `123.4 GB` |

## Other C Drive Findings

Root files:

| Path | Size |
|---|---:|
| `C:\hiberfil.sys` | `12.78 GB` |
| `C:\pagefile.sys` | `9.5 GB` |
| `C:\swapfile.sys` | `0.02 GB` |

Common cleanup folders:

| Path | Size |
|---|---:|
| `C:\ProgramData\Package Cache` | `0.48 GB` |
| `C:\Users\bryan\Downloads` | `0.15 GB` |
| `C:\Users\bryan\AppData\Local\Temp` | `0.10 GB` |
| `C:\Windows\SoftwareDistribution\Download` | `0.02 GB` |
| `C:\Users\bryan\AppData\Local\pip\Cache` | `0 GB` |
| `C:\Users\bryan\AppData\Local\npm-cache` | `0 GB` |
| `C:\Windows\Temp` | `0 GB` |
| `C:\ProgramData\Microsoft\Windows\WER` | `0 GB` |
| `C:\Users\bryan\.cache` | `0 GB` |
| `C:\$Recycle.Bin` | `0 GB` |

## Recovery Estimate

| Source | Estimated Recoverable Space |
|---|---:|
| Obvious Windows temp/cache/download folders | about `0.75 GB` |
| Disable hibernation, if desired | `12.78 GB` |
| WSL container/model/cache cleanup | potentially `50-70+ GB` |
| WSL VHD compaction after cleanup | required to return freed WSL space to C: |

## Notes For Follow-Up

- Main target: WSL, especially `/var/lib/containerd` and `/var/lib/docker`.
- The WSL VHD will not necessarily shrink on its own after Linux-side deletion; compaction is needed after cleanup.
- DISM component store analysis was attempted but requires an elevated terminal.
- No cleanup commands were run during the scan.
