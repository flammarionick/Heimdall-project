"""
Face Dataset with Heavy Augmentation for Noise Robustness

This dataset implements aggressive augmentation strategies specifically
designed to improve recognition accuracy on noisy, distorted images.

Target: Improve noise accuracy from 13.3% to 97%
"""

import os
import random
from pathlib import Path
from typing import Tuple, List, Dict, Optional, Callable

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import cv2

try:
    import albumentations as A
    from albumentations.pytorch import ToTensorV2
    ALBUMENTATIONS_AVAILABLE = True
except ImportError:
    ALBUMENTATIONS_AVAILABLE = False
    print("Warning: albumentations not installed. Using basic transforms.")


def get_training_augmentation(config: dict = None) -> Callable:
    """
    Create heavy augmentation pipeline for training.

    This augmentation is specifically designed to improve noise robustness
    by exposing the model to various types of distortions during training.

    Args:
        config: Augmentation configuration dictionary

    Returns:
        Albumentations Compose object
    """
    if not ALBUMENTATIONS_AVAILABLE:
        return get_basic_transform()

    config = config or {}

    return A.Compose([
        # === NOISE AUGMENTATION (Critical for 13.3% -> 97%) ===
        A.OneOf([
            A.GaussNoise(
                var_limit=(100, 2500),  # sigma 10-50
                mean=0,
                p=1.0
            ),
            A.ISONoise(
                color_shift=(0.01, 0.05),
                intensity=(0.1, 0.5),
                p=1.0
            ),
            A.MultiplicativeNoise(
                multiplier=(0.8, 1.2),
                elementwise=True,
                p=1.0
            ),
        ], p=config.get('noise_probability', 0.7)),

        # === ROTATION ===
        A.Rotate(
            limit=config.get('rotation_limit', 45),
            border_mode=cv2.BORDER_REPLICATE,
            p=config.get('rotation_probability', 0.5)
        ),

        # === LIGHTING/EXPOSURE VARIATIONS ===
        A.OneOf([
            A.RandomBrightnessContrast(
                brightness_limit=config.get('brightness_limit', 0.3),
                contrast_limit=config.get('contrast_limit', 0.3),
                p=1.0
            ),
            A.RandomGamma(
                gamma_limit=config.get('gamma_limit', (80, 120)),
                p=1.0
            ),
            A.CLAHE(
                clip_limit=4.0,
                tile_grid_size=(8, 8),
                p=1.0
            ),
            A.RandomToneCurve(scale=0.1, p=1.0),
        ], p=config.get('lighting_probability', 0.6)),

        # === GRAYSCALE ===
        A.ToGray(p=config.get('grayscale_probability', 0.2)),

        # === QUALITY DEGRADATION ===
        A.OneOf([
            A.ImageCompression(
                quality_lower=config.get('jpeg_quality_range', [30, 100])[0],
                quality_upper=config.get('jpeg_quality_range', [30, 100])[1],
                p=1.0
            ),
            A.Downscale(
                scale_min=config.get('downscale_range', [0.5, 0.9])[0],
                scale_max=config.get('downscale_range', [0.5, 0.9])[1],
                interpolation=cv2.INTER_LINEAR,
                p=1.0
            ),
            A.GaussianBlur(
                blur_limit=config.get('blur_limit', 7),
                p=1.0
            ),
            A.MotionBlur(
                blur_limit=7,
                p=1.0
            ),
        ], p=config.get('quality_probability', 0.5)),

        # === OCCLUSION (glasses, hats, masks) ===
        A.CoarseDropout(
            max_holes=config.get('coarse_dropout_max_holes', 3),
            max_height=config.get('coarse_dropout_max_size', 30),
            max_width=config.get('coarse_dropout_max_size', 30),
            min_holes=1,
            min_height=10,
            min_width=10,
            fill_value=0,
            p=config.get('occlusion_probability', 0.3)
        ),

        # === SHADOWS AND LIGHTING EFFECTS ===
        A.RandomShadow(
            shadow_roi=(0, 0.5, 1, 1),
            num_shadows_lower=1,
            num_shadows_upper=2,
            shadow_dimension=5,
            p=0.2
        ),

        # === COLOR JITTER ===
        A.ColorJitter(
            brightness=0.1,
            contrast=0.1,
            saturation=0.1,
            hue=0.05,
            p=0.3
        ),

        # === FINAL NORMALIZATION ===
        A.Normalize(
            mean=[0.5, 0.5, 0.5],
            std=[0.5, 0.5, 0.5],
            max_pixel_value=255.0
        ),
        ToTensorV2()
    ])


def get_validation_transform() -> Callable:
    """
    Create minimal transform for validation (no augmentation).
    """
    if not ALBUMENTATIONS_AVAILABLE:
        return get_basic_transform()

    return A.Compose([
        A.Normalize(
            mean=[0.5, 0.5, 0.5],
            std=[0.5, 0.5, 0.5],
            max_pixel_value=255.0
        ),
        ToTensorV2()
    ])


def get_basic_transform():
    """Fallback transform without albumentations."""
    import torchvision.transforms as T
    return T.Compose([
        T.ToTensor(),
        T.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
    ])


class FaceDataset(Dataset):
    """
    Face dataset with aggressive augmentation for noise robustness.

    Directory structure expected:
        root_dir/
            identity_001/
                image1.jpg
                image2.jpg
            identity_002/
                image1.jpg
            ...

    Args:
        root_dir: Path to dataset root directory
        transform: Augmentation transform to apply
        min_samples_per_class: Minimum images required per identity
        image_size: Target image size (width, height)
    """

    def __init__(
        self,
        root_dir: str,
        transform: Optional[Callable] = None,
        min_samples_per_class: int = 5,
        image_size: Tuple[int, int] = (160, 160)
    ):
        self.root_dir = Path(root_dir)
        self.transform = transform
        self.image_size = image_size

        # Build class mapping and sample list
        self.class_to_idx: Dict[str, int] = {}
        self.idx_to_class: Dict[int, str] = {}
        self.samples: List[Tuple[str, int]] = []

        self._build_dataset(min_samples_per_class)

    def _build_dataset(self, min_samples_per_class: int):
        """Build dataset from directory structure."""
        if not self.root_dir.exists():
            raise ValueError(f"Dataset directory not found: {self.root_dir}")

        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
        idx = 0

        # Iterate through identity folders
        for class_dir in sorted(self.root_dir.iterdir()):
            if not class_dir.is_dir():
                continue

            class_name = class_dir.name

            # Find all valid images
            images = [
                f for f in class_dir.iterdir()
                if f.suffix.lower() in valid_extensions
            ]

            # Skip classes with too few samples
            if len(images) < min_samples_per_class:
                continue

            # Add class mapping
            self.class_to_idx[class_name] = idx
            self.idx_to_class[idx] = class_name

            # Add samples
            for img_path in images:
                self.samples.append((str(img_path), idx))

            idx += 1

        self.num_classes = len(self.class_to_idx)

        print(f"Loaded dataset from {self.root_dir}")
        print(f"  Classes: {self.num_classes}")
        print(f"  Samples: {len(self.samples)}")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        img_path, label = self.samples[idx]

        # Load image
        image = cv2.imread(img_path)
        if image is None:
            # Fallback to PIL if cv2 fails
            image = np.array(Image.open(img_path).convert('RGB'))
        else:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Resize if needed
        if image.shape[:2] != self.image_size:
            image = cv2.resize(image, self.image_size, interpolation=cv2.INTER_LINEAR)

        # Apply transform
        if self.transform:
            if ALBUMENTATIONS_AVAILABLE:
                augmented = self.transform(image=image)
                image = augmented['image']
            else:
                image = self.transform(Image.fromarray(image))

        return image, label

    def get_class_name(self, idx: int) -> str:
        """Get class name from index."""
        return self.idx_to_class.get(idx, "unknown")


class BalancedBatchSampler:
    """
    Sampler that ensures each batch has samples from multiple identities.
    Helps with contrastive learning and hard negative mining.

    Args:
        dataset: FaceDataset instance
        batch_size: Batch size
        samples_per_class: Number of samples per identity in each batch
    """

    def __init__(
        self,
        dataset: FaceDataset,
        batch_size: int = 128,
        samples_per_class: int = 4
    ):
        self.dataset = dataset
        self.batch_size = batch_size
        self.samples_per_class = samples_per_class
        self.classes_per_batch = batch_size // samples_per_class

        # Build class to samples mapping
        self.class_to_samples: Dict[int, List[int]] = {}
        for idx, (_, label) in enumerate(dataset.samples):
            if label not in self.class_to_samples:
                self.class_to_samples[label] = []
            self.class_to_samples[label].append(idx)

        # Filter classes with enough samples
        self.valid_classes = [
            c for c, samples in self.class_to_samples.items()
            if len(samples) >= samples_per_class
        ]

    def __iter__(self):
        """Generate balanced batches."""
        # Shuffle classes
        classes = self.valid_classes.copy()
        random.shuffle(classes)

        batch = []
        for class_idx in classes:
            # Sample from this class
            samples = self.class_to_samples[class_idx]
            selected = random.sample(samples, min(self.samples_per_class, len(samples)))
            batch.extend(selected)

            # Yield batch when full
            if len(batch) >= self.batch_size:
                yield batch[:self.batch_size]
                batch = batch[self.batch_size:]

        # Yield remaining samples
        if batch:
            yield batch

    def __len__(self):
        return len(self.dataset) // self.batch_size


def create_dataloaders(
    train_dir: str,
    val_dir: str,
    config: dict,
    use_balanced_sampler: bool = False
) -> Tuple[DataLoader, DataLoader]:
    """
    Create training and validation dataloaders.

    Args:
        train_dir: Path to training data
        val_dir: Path to validation data
        config: Configuration dictionary
        use_balanced_sampler: Use balanced batch sampling

    Returns:
        Tuple of (train_loader, val_loader)
    """
    # Create datasets
    train_dataset = FaceDataset(
        root_dir=train_dir,
        transform=get_training_augmentation(config.get('augmentation', {})),
        min_samples_per_class=config.get('min_samples_per_class', 5),
        image_size=(config.get('image_size', 160), config.get('image_size', 160))
    )

    val_dataset = FaceDataset(
        root_dir=val_dir,
        transform=get_validation_transform(),
        min_samples_per_class=1,  # Allow all samples for validation
        image_size=(config.get('image_size', 160), config.get('image_size', 160))
    )

    # Create dataloaders
    if use_balanced_sampler:
        train_sampler = BalancedBatchSampler(
            train_dataset,
            batch_size=config.get('batch_size', 128),
            samples_per_class=4
        )
        train_loader = DataLoader(
            train_dataset,
            batch_sampler=train_sampler,
            num_workers=config.get('num_workers', 8),
            pin_memory=config.get('pin_memory', True)
        )
    else:
        train_loader = DataLoader(
            train_dataset,
            batch_size=config.get('batch_size', 128),
            shuffle=True,
            num_workers=config.get('num_workers', 8),
            pin_memory=config.get('pin_memory', True),
            drop_last=True
        )

    val_loader = DataLoader(
        val_dataset,
        batch_size=config.get('batch_size', 128),
        shuffle=False,
        num_workers=config.get('num_workers', 4),
        pin_memory=config.get('pin_memory', True)
    )

    return train_loader, val_loader, train_dataset.num_classes


if __name__ == "__main__":
    # Test the dataset
    print("Testing FaceDataset...")

    # Create a dummy dataset structure for testing
    import tempfile
    import shutil

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create dummy structure
        for i in range(10):
            class_dir = Path(tmpdir) / f"identity_{i:03d}"
            class_dir.mkdir()
            for j in range(6):
                # Create dummy image
                img = np.random.randint(0, 255, (160, 160, 3), dtype=np.uint8)
                cv2.imwrite(str(class_dir / f"img_{j}.jpg"), img)

        # Test dataset
        transform = get_training_augmentation()
        dataset = FaceDataset(tmpdir, transform=transform, min_samples_per_class=5)

        print(f"\nDataset size: {len(dataset)}")
        print(f"Number of classes: {dataset.num_classes}")

        # Test loading
        image, label = dataset[0]
        print(f"Image shape: {image.shape}")
        print(f"Label: {label}")

        # Test dataloader
        loader = DataLoader(dataset, batch_size=4, shuffle=True)
        batch_images, batch_labels = next(iter(loader))
        print(f"Batch images shape: {batch_images.shape}")
        print(f"Batch labels: {batch_labels}")

    print("\nDataset test completed successfully!")
