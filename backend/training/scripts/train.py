#!/usr/bin/env python3
"""
Heimdall Face Recognition Model Training Script

This script trains a face recognition model using ArcFace loss with heavy
augmentation to achieve 97% accuracy across all conditions including noise.

Usage:
    # On cloud GPU (Lambda Labs, RunPod, etc.)
    cd backend/training
    python scripts/train.py --config configs/train_config.yaml

    # With custom settings
    python scripts/train.py --config configs/train_config.yaml --epochs 100 --batch-size 64

Requirements:
    - NVIDIA GPU with 10GB+ VRAM
    - PyTorch with CUDA
    - facenet_pytorch
    - albumentations
    - wandb (optional, for logging)
"""

import os
import sys
import argparse
import time
from datetime import datetime
from pathlib import Path

import yaml
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts
from torch.cuda.amp import GradScaler, autocast

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from facenet_pytorch import InceptionResnetV1
from src.arcface_loss import ArcFaceLoss, get_loss_function
from src.dataset import FaceDataset, get_training_augmentation, get_validation_transform

# Optional wandb import
try:
    import wandb
    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Train Heimdall Face Recognition Model')
    parser.add_argument('--config', type=str, default='configs/train_config.yaml',
                        help='Path to configuration file')
    parser.add_argument('--epochs', type=int, default=None,
                        help='Override number of epochs')
    parser.add_argument('--batch-size', type=int, default=None,
                        help='Override batch size')
    parser.add_argument('--lr', type=float, default=None,
                        help='Override learning rate')
    parser.add_argument('--resume', type=str, default=None,
                        help='Path to checkpoint to resume from')
    parser.add_argument('--no-wandb', action='store_true',
                        help='Disable Weights & Biases logging')
    parser.add_argument('--debug', action='store_true',
                        help='Debug mode (small dataset, verbose output)')
    return parser.parse_args()


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def create_model(config: dict, device: torch.device) -> nn.Module:
    """
    Create and initialize the face recognition model.

    Args:
        config: Model configuration
        device: Target device

    Returns:
        Initialized model
    """
    print("Creating model...")

    # Load pretrained FaceNet
    model = InceptionResnetV1(
        pretrained=config['model'].get('pretrained', 'vggface2'),
        classify=False,
        num_classes=None,
        dropout_prob=config['model'].get('dropout_prob', 0.6)
    )

    model = model.to(device)
    model.train()

    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Total parameters: {total_params:,}")
    print(f"  Trainable parameters: {trainable_params:,}")

    return model


def create_dataloaders(config: dict, debug: bool = False):
    """
    Create training and validation dataloaders.

    Args:
        config: Data configuration
        debug: If True, use smaller subset

    Returns:
        train_loader, val_loader, num_classes
    """
    print("Creating dataloaders...")

    data_config = config.get('data', {})
    aug_config = config.get('augmentation', {})

    train_dir = data_config.get('train_dir', 'data/processed/train')
    val_dir = data_config.get('val_dir', 'data/processed/val')

    # Training dataset with augmentation
    train_dataset = FaceDataset(
        root_dir=train_dir,
        transform=get_training_augmentation(aug_config),
        min_samples_per_class=data_config.get('min_samples_per_class', 5),
        image_size=(data_config.get('image_size', 160), data_config.get('image_size', 160))
    )

    # Validation dataset (no augmentation)
    val_dataset = FaceDataset(
        root_dir=val_dir,
        transform=get_validation_transform(),
        min_samples_per_class=1,
        image_size=(data_config.get('image_size', 160), data_config.get('image_size', 160))
    )

    batch_size = config['training'].get('batch_size', 128)
    if debug:
        batch_size = min(batch_size, 16)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=data_config.get('num_workers', 8),
        pin_memory=data_config.get('pin_memory', True),
        drop_last=True
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=data_config.get('num_workers', 4),
        pin_memory=data_config.get('pin_memory', True)
    )

    print(f"  Training samples: {len(train_dataset)}")
    print(f"  Validation samples: {len(val_dataset)}")
    print(f"  Number of classes: {train_dataset.num_classes}")
    print(f"  Batch size: {batch_size}")

    return train_loader, val_loader, train_dataset.num_classes


def train_epoch(
    model: nn.Module,
    loss_fn: nn.Module,
    train_loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scaler: GradScaler,
    config: dict,
    device: torch.device,
    epoch: int
) -> dict:
    """
    Train for one epoch.

    Args:
        model: Face recognition model
        loss_fn: ArcFace loss function
        train_loader: Training dataloader
        optimizer: Optimizer
        scaler: Gradient scaler for mixed precision
        config: Training configuration
        device: Target device
        epoch: Current epoch number

    Returns:
        Dictionary of training metrics
    """
    model.train()
    loss_fn.train()

    total_loss = 0.0
    num_batches = 0
    correct = 0
    total = 0

    grad_accum_steps = config['training'].get('gradient_accumulation_steps', 1)
    use_amp = config['hardware'].get('mixed_precision', True)

    start_time = time.time()

    for batch_idx, (images, labels) in enumerate(train_loader):
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        # Forward pass with mixed precision
        with autocast(enabled=use_amp):
            embeddings = model(images)
            loss = loss_fn(embeddings, labels)
            loss = loss / grad_accum_steps

        # Backward pass
        scaler.scale(loss).backward()

        # Optimizer step with gradient accumulation
        if (batch_idx + 1) % grad_accum_steps == 0:
            # Gradient clipping
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            torch.nn.utils.clip_grad_norm_(loss_fn.parameters(), max_norm=1.0)

            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad()

        total_loss += loss.item() * grad_accum_steps
        num_batches += 1

        # Compute accuracy (for monitoring)
        with torch.no_grad():
            cosine_sim = loss_fn.get_cosine_similarity(F.normalize(embeddings, p=2, dim=1))
            predicted = cosine_sim.argmax(dim=1)
            correct += (predicted == labels).sum().item()
            total += labels.size(0)

        # Progress logging
        if (batch_idx + 1) % config['logging'].get('log_interval', 100) == 0:
            elapsed = time.time() - start_time
            samples_per_sec = total / elapsed
            print(f"  Batch {batch_idx + 1}/{len(train_loader)} | "
                  f"Loss: {loss.item() * grad_accum_steps:.4f} | "
                  f"Acc: {100 * correct / total:.2f}% | "
                  f"Speed: {samples_per_sec:.1f} samples/sec")

    avg_loss = total_loss / num_batches
    accuracy = correct / total

    return {
        'loss': avg_loss,
        'accuracy': accuracy,
        'samples_per_sec': total / (time.time() - start_time)
    }


@torch.no_grad()
def validate(
    model: nn.Module,
    loss_fn: nn.Module,
    val_loader: DataLoader,
    device: torch.device
) -> dict:
    """
    Validate the model.

    Args:
        model: Face recognition model
        loss_fn: ArcFace loss function
        val_loader: Validation dataloader
        device: Target device

    Returns:
        Dictionary of validation metrics
    """
    model.eval()
    loss_fn.eval()

    total_loss = 0.0
    num_batches = 0
    correct = 0
    total = 0

    for images, labels in val_loader:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        # Forward pass
        embeddings = model(images)
        loss = loss_fn(embeddings, labels)

        total_loss += loss.item()
        num_batches += 1

        # Compute accuracy
        cosine_sim = loss_fn.get_cosine_similarity(F.normalize(embeddings, p=2, dim=1))
        predicted = cosine_sim.argmax(dim=1)
        correct += (predicted == labels).sum().item()
        total += labels.size(0)

    return {
        'loss': total_loss / num_batches,
        'accuracy': correct / total
    }


def save_checkpoint(
    model: nn.Module,
    loss_fn: nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler,
    epoch: int,
    metrics: dict,
    path: str
):
    """Save training checkpoint."""
    checkpoint = {
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'loss_fn_state_dict': loss_fn.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'scheduler_state_dict': scheduler.state_dict() if scheduler else None,
        'metrics': metrics
    }
    torch.save(checkpoint, path)
    print(f"  Checkpoint saved: {path}")


def load_checkpoint(path: str, model, loss_fn, optimizer, scheduler, device):
    """Load training checkpoint."""
    checkpoint = torch.load(path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    loss_fn.load_state_dict(checkpoint['loss_fn_state_dict'])
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    if scheduler and checkpoint['scheduler_state_dict']:
        scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
    return checkpoint['epoch'], checkpoint.get('metrics', {})


def main():
    """Main training function."""
    args = parse_args()

    # Load configuration
    config = load_config(args.config)

    # Override config with command line arguments
    if args.epochs:
        config['training']['epochs'] = args.epochs
    if args.batch_size:
        config['training']['batch_size'] = args.batch_size
    if args.lr:
        config['training']['backbone_lr'] = args.lr
        config['training']['head_lr'] = args.lr * 100

    # Setup device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n{'='*60}")
    print("HEIMDALL FACE RECOGNITION MODEL TRAINING")
    print(f"{'='*60}")
    print(f"Device: {device}")
    if device.type == 'cuda':
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # Initialize wandb
    use_wandb = WANDB_AVAILABLE and not args.no_wandb
    if use_wandb:
        wandb.init(
            project=config['logging'].get('wandb_project', 'heimdall-face-recognition'),
            config=config
        )
        print("Weights & Biases logging enabled")

    # Create model
    model = create_model(config, device)

    # Create dataloaders
    train_loader, val_loader, num_classes = create_dataloaders(config, debug=args.debug)

    # Create loss function
    loss_config = config['loss'].copy()
    loss_config['num_classes'] = num_classes
    loss_config['embedding_dim'] = config['model'].get('embedding_dim', 512)
    loss_fn = get_loss_function(loss_config).to(device)
    print(f"Loss function: {config['loss']['type']}")

    # Create optimizer with differential learning rates
    optimizer = AdamW([
        {'params': model.parameters(), 'lr': config['training']['backbone_lr']},
        {'params': loss_fn.parameters(), 'lr': config['training']['head_lr']}
    ], weight_decay=config['training'].get('weight_decay', 5e-4))

    # Create scheduler
    scheduler = CosineAnnealingWarmRestarts(
        optimizer,
        T_0=config['scheduler'].get('T_0', 10),
        T_mult=config['scheduler'].get('T_mult', 2),
        eta_min=config['scheduler'].get('eta_min', 1e-7)
    )

    # Create gradient scaler for mixed precision
    scaler = GradScaler(enabled=config['hardware'].get('mixed_precision', True))

    # Resume from checkpoint if specified
    start_epoch = 0
    best_accuracy = 0.0
    if args.resume:
        print(f"Resuming from checkpoint: {args.resume}")
        start_epoch, _ = load_checkpoint(args.resume, model, loss_fn, optimizer, scheduler, device)
        start_epoch += 1

    # Create checkpoint directory
    checkpoint_dir = Path(config['paths'].get('checkpoint_dir', 'models/checkpoints'))
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Training loop
    epochs = config['training']['epochs']
    early_stopping_patience = config['training'].get('early_stopping_patience', 10)
    patience_counter = 0

    print(f"\n{'='*60}")
    print(f"Starting training for {epochs} epochs...")
    print(f"{'='*60}\n")

    for epoch in range(start_epoch, epochs):
        epoch_start = time.time()
        print(f"Epoch {epoch + 1}/{epochs}")
        print("-" * 40)

        # Train
        train_metrics = train_epoch(
            model, loss_fn, train_loader, optimizer, scaler,
            config, device, epoch
        )
        print(f"  Train Loss: {train_metrics['loss']:.4f} | "
              f"Train Acc: {100 * train_metrics['accuracy']:.2f}%")

        # Validate
        if (epoch + 1) % config['training'].get('val_frequency', 1) == 0:
            val_metrics = validate(model, loss_fn, val_loader, device)
            print(f"  Val Loss: {val_metrics['loss']:.4f} | "
                  f"Val Acc: {100 * val_metrics['accuracy']:.2f}%")

            # Check for best model
            if val_metrics['accuracy'] > best_accuracy:
                best_accuracy = val_metrics['accuracy']
                patience_counter = 0
                save_checkpoint(
                    model, loss_fn, optimizer, scheduler, epoch,
                    {'train': train_metrics, 'val': val_metrics},
                    str(checkpoint_dir / 'best_model.pth')
                )
            else:
                patience_counter += 1

            # Early stopping
            if patience_counter >= early_stopping_patience:
                print(f"\nEarly stopping triggered after {epoch + 1} epochs")
                break

            # Log to wandb
            if use_wandb:
                wandb.log({
                    'epoch': epoch + 1,
                    'train_loss': train_metrics['loss'],
                    'train_accuracy': train_metrics['accuracy'],
                    'val_loss': val_metrics['loss'],
                    'val_accuracy': val_metrics['accuracy'],
                    'learning_rate': optimizer.param_groups[0]['lr'],
                    'best_accuracy': best_accuracy
                })

        # Update scheduler
        scheduler.step()

        # Save periodic checkpoint
        if (epoch + 1) % config['logging'].get('save_interval', 5) == 0:
            save_checkpoint(
                model, loss_fn, optimizer, scheduler, epoch,
                {'train': train_metrics},
                str(checkpoint_dir / f'checkpoint_epoch_{epoch + 1}.pth')
            )

        epoch_time = time.time() - epoch_start
        print(f"  Epoch time: {epoch_time:.1f}s\n")

    # Save final model
    final_dir = Path(config['paths'].get('final_model_dir', 'models/final'))
    final_dir.mkdir(parents=True, exist_ok=True)

    # Save model state dict
    torch.save(model.state_dict(), str(final_dir / 'heimdall_facenet_retrained.pth'))

    # Save as TorchScript for production
    model.eval()
    example_input = torch.randn(1, 3, 160, 160).to(device)
    traced_model = torch.jit.trace(model, example_input)
    traced_model.save(str(final_dir / 'heimdall_facenet_retrained.pt'))

    print(f"\n{'='*60}")
    print("TRAINING COMPLETE")
    print(f"{'='*60}")
    print(f"Best validation accuracy: {100 * best_accuracy:.2f}%")
    print(f"Final model saved to: {final_dir}")

    if use_wandb:
        wandb.finish()


if __name__ == '__main__':
    main()
