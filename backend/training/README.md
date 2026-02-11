# Heimdall Face Recognition Model Training

This module contains the training infrastructure for retraining the face recognition model to achieve **97% accuracy** across all conditions including noise and combined distortions.

## Current Performance Issues

| Condition | Current Accuracy | Target |
|-----------|------------------|--------|
| Original | 100% | 100% |
| Rotation | 100% | 100% |
| Grayscale | 100% | 100% |
| **Noise (σ=30)** | **13.3%** | **97%** |
| **Combined** | **15.2%** | **97%** |
| Overall | ~77% | 97% |

## Quick Start (Cloud GPU)

### 1. Setup Environment

```bash
# On Lambda Labs / RunPod / etc.
cd backend/training
pip install -r requirements.txt
```

### 2. Download Dataset

```bash
# Download LFW (13K images) - quick test
python scripts/download_datasets.py --dataset lfw --prepare

# Or download CASIA-WebFace (500K images) - full training
python scripts/download_datasets.py --dataset casia --prepare
```

### 3. Train Model

```bash
# Start training
python scripts/train.py --config configs/train_config.yaml

# With custom settings
python scripts/train.py --config configs/train_config.yaml --epochs 100 --batch-size 64
```

### 4. Evaluate

```bash
python scripts/evaluate.py --model models/final/heimdall_facenet_retrained.pt
```

### 5. Export & Deploy

```bash
python scripts/export_model.py --checkpoint models/checkpoints/best_model.pth --deploy
```

## Directory Structure

```
training/
├── configs/
│   └── train_config.yaml      # Training configuration
├── data/
│   ├── raw/                   # Downloaded datasets
│   └── processed/             # Train/val/test splits
├── models/
│   ├── checkpoints/           # Training checkpoints
│   └── final/                 # Exported models
├── src/
│   ├── arcface_loss.py        # ArcFace loss implementation
│   └── dataset.py             # Dataset with augmentation
├── scripts/
│   ├── download_datasets.py   # Download datasets
│   ├── train.py               # Main training script
│   ├── evaluate.py            # Evaluation script
│   └── export_model.py        # Model export
└── requirements.txt           # Dependencies
```

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | RTX 3080 (10GB) | A100 (40GB) |
| RAM | 32 GB | 64 GB |
| Storage | 100 GB | 500 GB |
| Training Time | ~37 hours | ~12 hours |

## Cloud GPU Options

| Provider | GPU | Cost/Hour | Total Est. |
|----------|-----|-----------|------------|
| Lambda Labs | A100 | $1.10 | ~$25 |
| RunPod | A100 | $1.99 | ~$45 |
| AWS p4d | 8xA100 | $32.77 | ~$150 |

## Key Training Features

### ArcFace Loss
- Adds angular margin for better class separation
- Critical for noise robustness
- Scale=64, margin=0.5

### Heavy Augmentation
- Gaussian noise (σ=10-50)
- JPEG compression (Q=30-100)
- Rotation (up to 45°)
- Blur, occlusion, lighting variations

### Curriculum Learning
- Start with mild augmentation
- Gradually increase difficulty

## After Training

1. **Evaluate** on all conditions to verify 97% target
2. **Export** model to TorchScript
3. **Update** `embedding_service.py` to use new model
4. **Re-encode** all existing inmates

## Troubleshooting

### Out of Memory
- Reduce batch size: `--batch-size 64`
- Enable gradient accumulation (already configured)

### Slow Training
- Increase workers: Edit `num_workers` in config
- Use mixed precision (enabled by default)

### Poor Accuracy
- Train longer: `--epochs 100`
- Increase noise augmentation probability
- Try CosFace loss instead of ArcFace
