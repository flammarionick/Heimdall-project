#!/usr/bin/env python3
"""
Dataset Download Script for Heimdall Face Recognition Training

This script downloads and prepares face recognition datasets for training.

Datasets:
- LFW (Labeled Faces in the Wild) - 13K images, automatic download
- VGGFace2 - 3.31M images (requires manual registration)
- CASIA-WebFace - 500K images (requires manual registration)

Usage:
    cd backend/training
    python scripts/download_datasets.py --dataset lfw
    python scripts/download_datasets.py --dataset all --prepare

Requirements:
    - gdown (for Google Drive downloads)
    - tqdm
    - requests
"""

import os
import sys
import argparse
import shutil
import tarfile
import zipfile
from pathlib import Path
from typing import Optional
import urllib.request

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

try:
    import gdown
    GDOWN_AVAILABLE = True
except ImportError:
    GDOWN_AVAILABLE = False


# Dataset information
DATASETS = {
    'lfw': {
        'name': 'Labeled Faces in the Wild',
        'url': 'http://vis-www.cs.umass.edu/lfw/lfw.tgz',
        'size': '173 MB',
        'images': '~13,000',
        'identities': '5,749',
        'auto_download': True
    },
    'lfw_deepfunneled': {
        'name': 'LFW Deep Funneled (aligned)',
        'url': 'http://vis-www.cs.umass.edu/lfw/lfw-deepfunneled.tgz',
        'size': '112 MB',
        'images': '~13,000',
        'identities': '5,749',
        'auto_download': True
    },
    'vggface2': {
        'name': 'VGGFace2',
        'url': 'https://www.robots.ox.ac.uk/~vgg/data/vgg_face2/',
        'size': '~36 GB',
        'images': '3.31 million',
        'identities': '9,131',
        'auto_download': False,
        'instructions': '''
VGGFace2 requires manual registration:
1. Go to https://www.robots.ox.ac.uk/~vgg/data/vgg_face2/
2. Register and agree to terms
3. Download train.tar.gz and test.tar.gz
4. Place them in data/raw/vggface2/
5. Run: python scripts/download_datasets.py --dataset vggface2 --extract
'''
    },
    'casia': {
        'name': 'CASIA-WebFace',
        'url': 'https://drive.google.com/uc?id=1Of_EVz-yHV7QVWQGihYfvtny9Ne8qXVz',
        'size': '~4 GB',
        'images': '~500,000',
        'identities': '10,575',
        'auto_download': True,
        'google_drive': True
    }
}


class DownloadProgressBar:
    """Progress bar for urllib downloads."""
    def __init__(self, total_size):
        self.total_size = total_size
        self.downloaded = 0
        if TQDM_AVAILABLE:
            self.pbar = tqdm(total=total_size, unit='B', unit_scale=True)
        else:
            self.pbar = None

    def update(self, block_size):
        self.downloaded += block_size
        if self.pbar:
            self.pbar.update(block_size)
        else:
            pct = 100 * self.downloaded / self.total_size if self.total_size else 0
            print(f"\rDownloading: {pct:.1f}%", end='', flush=True)

    def close(self):
        if self.pbar:
            self.pbar.close()
        else:
            print()


def download_file(url: str, dest_path: str, desc: str = None) -> bool:
    """
    Download a file with progress bar.

    Args:
        url: URL to download
        dest_path: Destination file path
        desc: Description for progress bar

    Returns:
        True if successful
    """
    print(f"Downloading: {desc or url}")
    print(f"Destination: {dest_path}")

    try:
        # Get file size
        response = urllib.request.urlopen(url)
        total_size = int(response.headers.get('content-length', 0))

        # Download with progress
        progress = DownloadProgressBar(total_size)

        def reporthook(block_num, block_size, total_size):
            progress.update(block_size)

        urllib.request.urlretrieve(url, dest_path, reporthook=reporthook)
        progress.close()

        print(f"Download complete: {dest_path}")
        return True

    except Exception as e:
        print(f"Download failed: {e}")
        return False


def download_from_gdrive(file_id: str, dest_path: str) -> bool:
    """Download file from Google Drive."""
    if not GDOWN_AVAILABLE:
        print("Error: gdown not installed. Run: pip install gdown")
        return False

    try:
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, dest_path, quiet=False)
        return True
    except Exception as e:
        print(f"Google Drive download failed: {e}")
        return False


def extract_archive(archive_path: str, dest_dir: str) -> bool:
    """
    Extract tar or zip archive.

    Args:
        archive_path: Path to archive file
        dest_dir: Destination directory

    Returns:
        True if successful
    """
    print(f"Extracting: {archive_path}")
    print(f"Destination: {dest_dir}")

    try:
        if archive_path.endswith('.tgz') or archive_path.endswith('.tar.gz'):
            with tarfile.open(archive_path, 'r:gz') as tar:
                members = tar.getmembers()
                if TQDM_AVAILABLE:
                    for member in tqdm(members, desc="Extracting"):
                        tar.extract(member, dest_dir)
                else:
                    tar.extractall(dest_dir)

        elif archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                if TQDM_AVAILABLE:
                    for member in tqdm(zip_ref.namelist(), desc="Extracting"):
                        zip_ref.extract(member, dest_dir)
                else:
                    zip_ref.extractall(dest_dir)

        elif archive_path.endswith('.tar'):
            with tarfile.open(archive_path, 'r') as tar:
                tar.extractall(dest_dir)

        else:
            print(f"Unknown archive format: {archive_path}")
            return False

        print(f"Extraction complete")
        return True

    except Exception as e:
        print(f"Extraction failed: {e}")
        return False


def download_lfw(data_dir: Path, aligned: bool = True) -> bool:
    """Download LFW dataset."""
    dataset_key = 'lfw_deepfunneled' if aligned else 'lfw'
    dataset = DATASETS[dataset_key]

    raw_dir = data_dir / 'raw' / 'lfw'
    raw_dir.mkdir(parents=True, exist_ok=True)

    archive_name = 'lfw-deepfunneled.tgz' if aligned else 'lfw.tgz'
    archive_path = raw_dir / archive_name

    # Download if not exists
    if not archive_path.exists():
        success = download_file(dataset['url'], str(archive_path), dataset['name'])
        if not success:
            return False

    # Extract
    success = extract_archive(str(archive_path), str(raw_dir))
    return success


def download_casia(data_dir: Path) -> bool:
    """Download CASIA-WebFace dataset from Google Drive."""
    dataset = DATASETS['casia']

    raw_dir = data_dir / 'raw' / 'casia'
    raw_dir.mkdir(parents=True, exist_ok=True)

    archive_path = raw_dir / 'CASIA-WebFace.zip'

    if not archive_path.exists():
        print(f"\nDownloading {dataset['name']}...")
        print(f"Size: {dataset['size']}")

        # Extract file ID from URL
        file_id = '1Of_EVz-yHV7QVWQGihYfvtny9Ne8qXVz'
        success = download_from_gdrive(file_id, str(archive_path))
        if not success:
            return False

    # Extract
    success = extract_archive(str(archive_path), str(raw_dir))
    return success


def prepare_dataset(data_dir: Path, train_ratio: float = 0.8) -> bool:
    """
    Prepare downloaded datasets for training.

    Creates train/val/test splits.

    Args:
        data_dir: Data directory
        train_ratio: Ratio of data for training

    Returns:
        True if successful
    """
    import random

    raw_dir = data_dir / 'raw'
    processed_dir = data_dir / 'processed'

    train_dir = processed_dir / 'train'
    val_dir = processed_dir / 'val'
    test_dir = processed_dir / 'test'

    # Create directories
    for d in [train_dir, val_dir, test_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Find all identity directories
    identity_dirs = []
    for dataset_dir in raw_dir.iterdir():
        if not dataset_dir.is_dir():
            continue
        for identity_dir in dataset_dir.iterdir():
            if identity_dir.is_dir():
                identity_dirs.append(identity_dir)

    print(f"\nFound {len(identity_dirs)} identity directories")

    # Process each identity
    total_train = 0
    total_val = 0
    total_test = 0

    for identity_dir in tqdm(identity_dirs, desc="Processing identities") if TQDM_AVAILABLE else identity_dirs:
        identity_name = identity_dir.name

        # Find all images
        images = list(identity_dir.glob('*.jpg')) + list(identity_dir.glob('*.png'))
        if len(images) < 2:
            continue

        # Shuffle images
        random.shuffle(images)

        # Split
        n_train = max(1, int(len(images) * train_ratio))
        n_val = max(1, (len(images) - n_train) // 2)

        train_images = images[:n_train]
        val_images = images[n_train:n_train + n_val]
        test_images = images[n_train + n_val:]

        # Copy to processed directories
        for split_dir, split_images in [
            (train_dir, train_images),
            (val_dir, val_images),
            (test_dir, test_images)
        ]:
            if not split_images:
                continue

            identity_split_dir = split_dir / identity_name
            identity_split_dir.mkdir(exist_ok=True)

            for img_path in split_images:
                dest_path = identity_split_dir / img_path.name
                shutil.copy2(img_path, dest_path)

        total_train += len(train_images)
        total_val += len(val_images)
        total_test += len(test_images)

    print(f"\nDataset prepared:")
    print(f"  Training: {total_train} images")
    print(f"  Validation: {total_val} images")
    print(f"  Test: {total_test} images")

    return True


def show_dataset_info():
    """Display information about available datasets."""
    print("\n" + "=" * 60)
    print("AVAILABLE DATASETS FOR HEIMDALL TRAINING")
    print("=" * 60)

    for key, info in DATASETS.items():
        print(f"\n{key.upper()}: {info['name']}")
        print(f"  Images: {info['images']}")
        print(f"  Identities: {info['identities']}")
        print(f"  Size: {info['size']}")
        print(f"  Auto-download: {'Yes' if info['auto_download'] else 'No'}")

        if 'instructions' in info:
            print(f"\n  Instructions:{info['instructions']}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Download datasets for Heimdall training')
    parser.add_argument('--dataset', type=str, choices=['lfw', 'casia', 'vggface2', 'all', 'info'],
                        default='info', help='Dataset to download')
    parser.add_argument('--data-dir', type=str, default='data',
                        help='Data directory')
    parser.add_argument('--extract', action='store_true',
                        help='Extract already downloaded archives')
    parser.add_argument('--prepare', action='store_true',
                        help='Prepare train/val/test splits')
    parser.add_argument('--aligned', action='store_true', default=True,
                        help='Download aligned version (for LFW)')

    args = parser.parse_args()
    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    if args.dataset == 'info':
        show_dataset_info()
        return

    print(f"\n{'='*60}")
    print("HEIMDALL DATASET DOWNLOADER")
    print(f"{'='*60}")
    print(f"Data directory: {data_dir.absolute()}")

    success = True

    if args.dataset in ['lfw', 'all']:
        print(f"\n--- Downloading LFW ---")
        success = download_lfw(data_dir, aligned=args.aligned) and success

    if args.dataset in ['casia', 'all']:
        print(f"\n--- Downloading CASIA-WebFace ---")
        success = download_casia(data_dir) and success

    if args.dataset == 'vggface2':
        print(DATASETS['vggface2']['instructions'])

    if args.prepare and success:
        print(f"\n--- Preparing Dataset Splits ---")
        success = prepare_dataset(data_dir) and success

    if success:
        print(f"\n{'='*60}")
        print("DOWNLOAD COMPLETE")
        print(f"{'='*60}")
        print(f"\nNext steps:")
        print(f"1. Run training: python scripts/train.py --config configs/train_config.yaml")
    else:
        print(f"\nSome downloads failed. Please check errors above.")

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
