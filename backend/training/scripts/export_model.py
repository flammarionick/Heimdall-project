#!/usr/bin/env python3
"""
Model Export Script for Heimdall Face Recognition

Exports the trained model for production deployment.

Outputs:
    - TorchScript model (.pt) for production inference
    - ONNX model (.onnx) for cross-platform deployment
    - Model metadata (.json) with configuration

Usage:
    cd backend/training
    python scripts/export_model.py --checkpoint models/checkpoints/best_model.pth
"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).parent.parent))

from facenet_pytorch import InceptionResnetV1


def load_checkpoint(checkpoint_path: str, device: torch.device) -> nn.Module:
    """
    Load model from training checkpoint.

    Args:
        checkpoint_path: Path to checkpoint file
        device: Target device

    Returns:
        Loaded model
    """
    print(f"Loading checkpoint: {checkpoint_path}")

    checkpoint = torch.load(checkpoint_path, map_location=device)

    # Create model
    model = InceptionResnetV1(
        pretrained=None,
        classify=False,
        num_classes=None,
        dropout_prob=0.6
    )

    # Load state dict
    model.load_state_dict(checkpoint['model_state_dict'])
    model = model.to(device)
    model.eval()

    # Get training metrics if available
    metrics = checkpoint.get('metrics', {})
    epoch = checkpoint.get('epoch', 'unknown')

    print(f"  Loaded from epoch: {epoch}")
    if 'val' in metrics:
        print(f"  Validation accuracy: {metrics['val'].get('accuracy', 'N/A'):.2%}")

    return model, metrics


def export_torchscript(model: nn.Module, output_path: str, device: torch.device):
    """
    Export model to TorchScript format.

    Args:
        model: PyTorch model
        output_path: Output file path
        device: Target device
    """
    print(f"\nExporting TorchScript model...")

    model.eval()

    # Create example input
    example_input = torch.randn(1, 3, 160, 160).to(device)

    # Trace the model
    with torch.no_grad():
        traced_model = torch.jit.trace(model, example_input)

    # Optimize for inference
    traced_model = torch.jit.optimize_for_inference(traced_model)

    # Save
    traced_model.save(output_path)
    print(f"  Saved: {output_path}")

    # Verify
    loaded = torch.jit.load(output_path, map_location=device)
    with torch.no_grad():
        output1 = model(example_input)
        output2 = loaded(example_input)
        diff = torch.abs(output1 - output2).max().item()
        print(f"  Verification: max difference = {diff:.2e}")


def export_onnx(model: nn.Module, output_path: str, device: torch.device):
    """
    Export model to ONNX format.

    Args:
        model: PyTorch model
        output_path: Output file path
        device: Target device
    """
    print(f"\nExporting ONNX model...")

    model.eval()

    # Create example input
    example_input = torch.randn(1, 3, 160, 160).to(device)

    # Export to ONNX
    torch.onnx.export(
        model,
        example_input,
        output_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['face_image'],
        output_names=['embedding'],
        dynamic_axes={
            'face_image': {0: 'batch_size'},
            'embedding': {0: 'batch_size'}
        }
    )

    print(f"  Saved: {output_path}")

    # Verify with ONNX Runtime if available
    try:
        import onnxruntime as ort

        session = ort.InferenceSession(output_path)
        input_name = session.get_inputs()[0].name

        # Run inference
        with torch.no_grad():
            pytorch_output = model(example_input).cpu().numpy()

        onnx_output = session.run(None, {input_name: example_input.cpu().numpy()})[0]

        diff = abs(pytorch_output - onnx_output).max()
        print(f"  ONNX verification: max difference = {diff:.2e}")

    except ImportError:
        print("  (Install onnxruntime to verify ONNX export)")


def save_metadata(
    output_path: str,
    checkpoint_path: str,
    metrics: dict,
    config: dict = None
):
    """
    Save model metadata.

    Args:
        output_path: Output file path
        checkpoint_path: Source checkpoint path
        metrics: Training metrics
        config: Training configuration
    """
    print(f"\nSaving metadata...")

    metadata = {
        'model_info': {
            'architecture': 'InceptionResnetV1',
            'pretrained_base': 'vggface2',
            'embedding_dim': 512,
            'input_size': [160, 160],
            'input_channels': 3,
            'normalization': {
                'mean': [0.5, 0.5, 0.5],
                'std': [0.5, 0.5, 0.5]
            }
        },
        'training_info': {
            'source_checkpoint': checkpoint_path,
            'export_date': datetime.now().isoformat(),
            'loss_function': 'ArcFace',
            'metrics': metrics
        },
        'inference_info': {
            'recommended_threshold': 0.45,
            'output_format': '512-dimensional L2-normalized embedding',
            'distance_metric': 'cosine'
        },
        'performance_targets': {
            'overall_accuracy': 0.97,
            'noise_accuracy': 0.97,
            'combined_accuracy': 0.97,
            'max_inference_time_ms': 5000
        }
    }

    if config:
        metadata['training_config'] = config

    with open(output_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"  Saved: {output_path}")


def copy_to_backend(source_dir: Path, backend_dir: Path):
    """
    Copy exported model to backend for deployment.

    Args:
        source_dir: Directory containing exported models
        backend_dir: Backend directory
    """
    import shutil

    print(f"\nCopying to backend...")

    # Create models directory in backend
    models_dir = backend_dir / 'models'
    models_dir.mkdir(exist_ok=True)

    # Backup existing model
    existing_model = models_dir / 'heimdall_facenet_retrained.pt'
    if existing_model.exists():
        backup_path = models_dir / f'heimdall_facenet_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pt'
        shutil.copy(existing_model, backup_path)
        print(f"  Backed up existing model to: {backup_path}")

    # Copy new model
    source_model = source_dir / 'heimdall_facenet_retrained.pt'
    if source_model.exists():
        shutil.copy(source_model, existing_model)
        print(f"  Copied: {existing_model}")

    # Copy metadata
    source_meta = source_dir / 'model_metadata.json'
    if source_meta.exists():
        shutil.copy(source_meta, models_dir / 'model_metadata.json')
        print(f"  Copied: {models_dir / 'model_metadata.json'}")


def main():
    """Main export function."""
    parser = argparse.ArgumentParser(description='Export Heimdall face recognition model')
    parser.add_argument('--checkpoint', type=str, required=True,
                        help='Path to training checkpoint')
    parser.add_argument('--output-dir', type=str, default='models/final',
                        help='Output directory')
    parser.add_argument('--no-onnx', action='store_true',
                        help='Skip ONNX export')
    parser.add_argument('--deploy', action='store_true',
                        help='Copy to backend for deployment')
    parser.add_argument('--backend-dir', type=str, default='../../',
                        help='Backend directory path')

    args = parser.parse_args()

    # Setup
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load checkpoint
    model, metrics = load_checkpoint(args.checkpoint, device)

    # Export TorchScript
    torchscript_path = output_dir / 'heimdall_facenet_retrained.pt'
    export_torchscript(model, str(torchscript_path), device)

    # Export ONNX
    if not args.no_onnx:
        onnx_path = output_dir / 'heimdall_facenet_retrained.onnx'
        export_onnx(model, str(onnx_path), device)

    # Save state dict (for fine-tuning)
    state_dict_path = output_dir / 'heimdall_facenet_retrained.pth'
    torch.save(model.state_dict(), state_dict_path)
    print(f"\nSaved state dict: {state_dict_path}")

    # Save metadata
    metadata_path = output_dir / 'model_metadata.json'
    save_metadata(str(metadata_path), args.checkpoint, metrics)

    # Copy to backend if requested
    if args.deploy:
        backend_dir = Path(args.backend_dir).resolve()
        copy_to_backend(output_dir, backend_dir)

    print(f"\n{'='*60}")
    print("EXPORT COMPLETE")
    print(f"{'='*60}")
    print(f"\nExported files:")
    for f in output_dir.iterdir():
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f.name}: {size_mb:.1f} MB")

    print(f"\nNext steps:")
    print(f"1. Run evaluation: python scripts/evaluate.py --model {torchscript_path}")
    print(f"2. Deploy: Update embedding_service.py to use new model")
    print(f"3. Re-encode: Run scripts/reencode_with_new_model.py")


if __name__ == '__main__':
    main()
