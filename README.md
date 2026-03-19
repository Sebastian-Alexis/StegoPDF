# StegoPDF

> **This repository is archived and is no longer actively maintained.**

> Published at the [IEEE Silicon Valley Cybersecurity Conference (SVCC) 2025](https://www.svcsi.org/events-1/ieee-svcc-2025-conference). Won 3rd Place in Systems Software at [ISEF 2025](https://www.societyforscience.org/isef/).

Detection and isolation of stegomalware in PDFs using Kolmogorov complexity.

## Overview

PDF-based stegomalware hides malicious payloads within the tree structure of PDF documents, exploiting features like embedded JavaScript, metadata, and open actions while appearing legitimate. Traditional heuristic and signature-based detection methods often fail due to the external similarities between clean and infected documents.

This implementation detects these threats by approximating the Kolmogorov complexity of individual components within a PDF's internal tree structure and comparing them against baselines derived from known clean documents. Deviations in complexity — particularly in high-risk components like JavaScript, OpenAction triggers, and metadata — indicate malicious modifications.

## How It Works

1. **PDF Tree Extraction** — A custom parser extracts the hierarchical tree structure of a PDF, isolating components such as `/Catalog`, `/Pages`, `/OpenAction`, `/Kids`, and embedded `/JavaScript` objects.

2. **Complexity Estimation** — Each component is compressed using DEFLATE (zlib). The compressed length serves as an upper-bound approximation of its Kolmogorov complexity.

3. **Baseline Comparison** — Clean PDFs are profiled to establish baseline complexity values per component. Incoming PDFs are compared against these baselines.

4. **Anomaly Scoring** — Deviations are computed per component and combined into a weighted anomaly score, with higher weights on suspicious attributes (JavaScript, OpenAction) and lower weights on benign variations (page count, text length).

5. **Classification & Quarantine** — PDFs exceeding the anomaly threshold are flagged as malicious and quarantined using Firejail.

## Results

Tested with 600 PDFs (100 clean, 500 with injected stegomalware across 5 injection methods):

| Approach | True Positive Rate | False Positive Rate |
|---|---|---|
| Whole-PDF analysis | 100% | 86.2% |
| Component-based analysis | 97.8% | 3.7% |

Malicious PDFs consistently exhibited 35–50% higher complexity in JavaScript and embedded object components compared to clean baselines.

## Paper

The full research paper is included in this repository: [`SVCC_2025_paper_2414.pdf`](SVCC_2025_paper_2414.pdf)

## Architecture

```
Incoming Email → Mail Server → PDF Extraction → Tree Parsing
    → Per-Component Complexity Calculation → Baseline Comparison
    → Anomaly Scoring → Clean (deliver) / Malicious (quarantine)
```

The test environment uses a Raspberry Pi running the mail server with detection software, with two additional machines for sending and receiving emails with PDF attachments.
