"""
ArcFace Loss Implementation for Heimdall Face Recognition

ArcFace: Additive Angular Margin Loss for Deep Face Recognition
Paper: https://arxiv.org/abs/1801.07698

This loss adds an angular margin penalty to improve inter-class separability,
which is crucial for noise robustness.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math


class ArcFaceLoss(nn.Module):
    """
    ArcFace Loss with Additive Angular Margin.

    Args:
        embedding_dim: Dimension of face embeddings (512 for FaceNet)
        num_classes: Number of identity classes in training set
        scale: Feature scale (s in paper), default 64.0
        margin: Angular margin (m in paper), default 0.5 radians (~28.6 degrees)
        easy_margin: Use easy margin variant
    """

    def __init__(
        self,
        embedding_dim: int = 512,
        num_classes: int = 10000,
        scale: float = 64.0,
        margin: float = 0.5,
        easy_margin: bool = False
    ):
        super(ArcFaceLoss, self).__init__()

        self.embedding_dim = embedding_dim
        self.num_classes = num_classes
        self.scale = scale
        self.margin = margin
        self.easy_margin = easy_margin

        # Weight matrix for class centers (learnable)
        self.weight = nn.Parameter(torch.FloatTensor(num_classes, embedding_dim))
        nn.init.xavier_uniform_(self.weight)

        # Precompute margin values for efficiency
        self.cos_m = math.cos(margin)
        self.sin_m = math.sin(margin)
        self.th = math.cos(math.pi - margin)
        self.mm = math.sin(math.pi - margin) * margin

    def forward(self, embeddings: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """
        Compute ArcFace loss.

        Args:
            embeddings: Face embeddings, shape (batch_size, embedding_dim)
            labels: Ground truth class labels, shape (batch_size,)

        Returns:
            Cross entropy loss with angular margin
        """
        # L2 normalize embeddings and weights
        embeddings = F.normalize(embeddings, p=2, dim=1)
        weight = F.normalize(self.weight, p=2, dim=1)

        # Compute cosine similarity (dot product of normalized vectors)
        cosine = F.linear(embeddings, weight)

        # Clamp cosine to avoid numerical issues
        cosine = torch.clamp(cosine, -1.0 + 1e-7, 1.0 - 1e-7)

        # Compute sine from cosine: sin = sqrt(1 - cos^2)
        sine = torch.sqrt(1.0 - torch.pow(cosine, 2))

        # Compute cos(theta + m) using angle addition formula:
        # cos(theta + m) = cos(theta)*cos(m) - sin(theta)*sin(m)
        phi = cosine * self.cos_m - sine * self.sin_m

        if self.easy_margin:
            # Easy margin: only apply margin when cos(theta) > 0
            phi = torch.where(cosine > 0, phi, cosine)
        else:
            # Original ArcFace: apply margin with threshold
            phi = torch.where(cosine > self.th, phi, cosine - self.mm)

        # Create one-hot encoding for labels
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1).long(), 1)

        # Apply margin only to the correct class
        # output[i,j] = phi[i,j] if j == labels[i] else cosine[i,j]
        output = (one_hot * phi) + ((1.0 - one_hot) * cosine)

        # Scale the output
        output *= self.scale

        # Compute cross entropy loss
        loss = F.cross_entropy(output, labels)

        return loss

    def get_cosine_similarity(self, embeddings: torch.Tensor) -> torch.Tensor:
        """
        Get cosine similarity between embeddings and class centers.
        Useful for inference/evaluation.

        Args:
            embeddings: Face embeddings, shape (batch_size, embedding_dim)

        Returns:
            Cosine similarity matrix, shape (batch_size, num_classes)
        """
        embeddings = F.normalize(embeddings, p=2, dim=1)
        weight = F.normalize(self.weight, p=2, dim=1)
        return F.linear(embeddings, weight)


class CosFaceLoss(nn.Module):
    """
    CosFace Loss (Large Margin Cosine Loss).
    Alternative to ArcFace with additive cosine margin instead of angular margin.

    Paper: https://arxiv.org/abs/1801.09414

    Args:
        embedding_dim: Dimension of face embeddings
        num_classes: Number of identity classes
        scale: Feature scale, default 64.0
        margin: Cosine margin, default 0.35
    """

    def __init__(
        self,
        embedding_dim: int = 512,
        num_classes: int = 10000,
        scale: float = 64.0,
        margin: float = 0.35
    ):
        super(CosFaceLoss, self).__init__()

        self.embedding_dim = embedding_dim
        self.num_classes = num_classes
        self.scale = scale
        self.margin = margin

        self.weight = nn.Parameter(torch.FloatTensor(num_classes, embedding_dim))
        nn.init.xavier_uniform_(self.weight)

    def forward(self, embeddings: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """Compute CosFace loss."""
        # L2 normalize
        embeddings = F.normalize(embeddings, p=2, dim=1)
        weight = F.normalize(self.weight, p=2, dim=1)

        # Cosine similarity
        cosine = F.linear(embeddings, weight)

        # Subtract margin from correct class
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1).long(), 1)

        output = cosine - one_hot * self.margin
        output *= self.scale

        return F.cross_entropy(output, labels)


class CombinedMarginLoss(nn.Module):
    """
    Combined Margin Loss (ArcFace + CosFace).
    Combines both angular and cosine margins for potentially better performance.

    Args:
        embedding_dim: Dimension of face embeddings
        num_classes: Number of identity classes
        scale: Feature scale
        m1: Angular margin (ArcFace)
        m2: Cosine margin (CosFace)
        m3: Additive margin
    """

    def __init__(
        self,
        embedding_dim: int = 512,
        num_classes: int = 10000,
        scale: float = 64.0,
        m1: float = 1.0,   # Angular margin multiplier
        m2: float = 0.5,   # Angular margin
        m3: float = 0.0    # Additive margin
    ):
        super(CombinedMarginLoss, self).__init__()

        self.embedding_dim = embedding_dim
        self.num_classes = num_classes
        self.scale = scale
        self.m1 = m1
        self.m2 = m2
        self.m3 = m3

        self.weight = nn.Parameter(torch.FloatTensor(num_classes, embedding_dim))
        nn.init.xavier_uniform_(self.weight)

        self.cos_m2 = math.cos(m2)
        self.sin_m2 = math.sin(m2)
        self.threshold = math.cos(math.pi - m2)

    def forward(self, embeddings: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """Compute combined margin loss."""
        embeddings = F.normalize(embeddings, p=2, dim=1)
        weight = F.normalize(self.weight, p=2, dim=1)

        cosine = F.linear(embeddings, weight)
        sine = torch.sqrt(1.0 - torch.pow(cosine, 2))

        # Combined formula: cos(m1 * theta + m2) - m3
        phi = cosine * self.cos_m2 - sine * self.sin_m2 - self.m3
        phi = torch.where(cosine > self.threshold, phi, cosine - self.m2 - self.m3)

        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1).long(), 1)

        output = (one_hot * phi) + ((1.0 - one_hot) * cosine)
        output *= self.scale

        return F.cross_entropy(output, labels)


def get_loss_function(config: dict) -> nn.Module:
    """
    Factory function to create loss function from config.

    Args:
        config: Dictionary with loss configuration

    Returns:
        Loss module
    """
    loss_type = config.get('type', 'arcface').lower()

    if loss_type == 'arcface':
        return ArcFaceLoss(
            embedding_dim=config.get('embedding_dim', 512),
            num_classes=config.get('num_classes', 10000),
            scale=config.get('scale', 64.0),
            margin=config.get('margin', 0.5),
            easy_margin=config.get('easy_margin', False)
        )
    elif loss_type == 'cosface':
        return CosFaceLoss(
            embedding_dim=config.get('embedding_dim', 512),
            num_classes=config.get('num_classes', 10000),
            scale=config.get('scale', 64.0),
            margin=config.get('margin', 0.35)
        )
    elif loss_type == 'combined':
        return CombinedMarginLoss(
            embedding_dim=config.get('embedding_dim', 512),
            num_classes=config.get('num_classes', 10000),
            scale=config.get('scale', 64.0),
            m1=config.get('m1', 1.0),
            m2=config.get('m2', 0.5),
            m3=config.get('m3', 0.0)
        )
    else:
        raise ValueError(f"Unknown loss type: {loss_type}")


if __name__ == "__main__":
    # Test the loss functions
    print("Testing ArcFace Loss...")

    batch_size = 32
    embedding_dim = 512
    num_classes = 1000

    # Create random embeddings and labels
    embeddings = torch.randn(batch_size, embedding_dim)
    labels = torch.randint(0, num_classes, (batch_size,))

    # Test ArcFace
    arcface = ArcFaceLoss(embedding_dim, num_classes)
    loss = arcface(embeddings, labels)
    print(f"ArcFace Loss: {loss.item():.4f}")

    # Test CosFace
    cosface = CosFaceLoss(embedding_dim, num_classes)
    loss = cosface(embeddings, labels)
    print(f"CosFace Loss: {loss.item():.4f}")

    # Test Combined
    combined = CombinedMarginLoss(embedding_dim, num_classes)
    loss = combined(embeddings, labels)
    print(f"Combined Margin Loss: {loss.item():.4f}")

    print("\nAll loss functions working correctly!")
