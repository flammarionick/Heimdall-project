#!/bin/bash
# =============================================================================
# Heimdall Face Recognition - Cloud GPU Training Setup
# =============================================================================
#
# This script sets up and runs the complete training pipeline on a cloud GPU.
#
# Usage:
#   # On Lambda Labs / RunPod / etc:
#   chmod +x scripts/cloud_gpu_setup.sh
#   ./scripts/cloud_gpu_setup.sh
#
# Estimated time: ~12 hours on A100, ~37 hours on RTX 3080
# =============================================================================

set -e  # Exit on error

echo "============================================================"
echo "HEIMDALL FACE RECOGNITION - CLOUD GPU TRAINING"
echo "============================================================"
echo ""

# Check for GPU
if ! command -v nvidia-smi &> /dev/null; then
    echo "ERROR: nvidia-smi not found. Please run on a GPU instance."
    exit 1
fi

echo "GPU Information:"
nvidia-smi --query-gpu=name,memory.total --format=csv
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TRAINING_DIR="$(dirname "$SCRIPT_DIR")"
cd "$TRAINING_DIR"

echo "Working directory: $TRAINING_DIR"
echo ""

# =============================================================================
# Step 1: Install Dependencies
# =============================================================================
echo "============================================================"
echo "Step 1: Installing Dependencies"
echo "============================================================"

pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
python -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
"

echo ""

# =============================================================================
# Step 2: Download Datasets
# =============================================================================
echo "============================================================"
echo "Step 2: Downloading Datasets"
echo "============================================================"

# Option 1: Quick test with LFW (13K images)
# python scripts/download_datasets.py --dataset lfw --prepare

# Option 2: Full training with CASIA-WebFace (500K images)
echo "Downloading CASIA-WebFace dataset (500K images)..."
echo "This may take 30-60 minutes depending on bandwidth."
python scripts/download_datasets.py --dataset casia --prepare

# Show dataset stats
echo ""
echo "Dataset Statistics:"
find data/processed/train -type f -name "*.jpg" -o -name "*.png" 2>/dev/null | wc -l | xargs echo "  Training images:"
find data/processed/val -type f -name "*.jpg" -o -name "*.png" 2>/dev/null | wc -l | xargs echo "  Validation images:"
find data/processed/test -type f -name "*.jpg" -o -name "*.png" 2>/dev/null | wc -l | xargs echo "  Test images:"
echo ""

# =============================================================================
# Step 3: Start Training
# =============================================================================
echo "============================================================"
echo "Step 3: Starting Training"
echo "============================================================"
echo "Target: 97% accuracy on noise and combined conditions"
echo ""

# Create logs directory
mkdir -p logs

# Start training with logging
python scripts/train.py --config configs/train_config.yaml 2>&1 | tee logs/training_$(date +%Y%m%d_%H%M%S).log

echo ""
echo "Training complete!"

# =============================================================================
# Step 4: Evaluate Model
# =============================================================================
echo "============================================================"
echo "Step 4: Evaluating Model"
echo "============================================================"

python scripts/evaluate.py --model models/final/heimdall_facenet_retrained.pt 2>&1 | tee logs/evaluation_$(date +%Y%m%d_%H%M%S).log

# =============================================================================
# Step 5: Export Model
# =============================================================================
echo "============================================================"
echo "Step 5: Exporting Model"
echo "============================================================"

python scripts/export_model.py --checkpoint models/checkpoints/best_model.pth

echo ""
echo "============================================================"
echo "TRAINING PIPELINE COMPLETE"
echo "============================================================"
echo ""
echo "Output files:"
echo "  - models/final/heimdall_facenet_retrained.pt (TorchScript)"
echo "  - models/final/heimdall_facenet_retrained.onnx (ONNX)"
echo "  - models/final/model_metadata.json"
echo ""
echo "Next steps:"
echo "  1. Download models/final/* to your local machine"
echo "  2. Copy heimdall_facenet_retrained.pt to backend/models/"
echo "  3. Run scripts/reencode_with_new_model.py to update all inmates"
echo ""
