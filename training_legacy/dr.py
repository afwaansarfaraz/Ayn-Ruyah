# ==============================================================================
# RetinaLens AI – Modular Retinal Diagnostic Platform
# ==============================================================================
# LEGACY TRAINING SCRIPT — BINARY CLASSIFIER (EfficientNet-B0)
# NOTE: This script trains a 2-class (DR / No DR) model and is NOT compatible
# with the production 5-class EfficientNet-B4 multi-tenant platform.
# Preserved strictly for experimental and benchmark archival purposes.
# ==============================================================================

import os
import sys
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
import timm

# ────────────────────────────────────────────────
#  Transforms & Dataset Definitions (Module Scope)
# ────────────────────────────────────────────────
train_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

val_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])


class APTOSDataset(Dataset):
    """PyTorch Dataset for legacy APTOS 2019 binary classification."""
    def __init__(self, dataframe, image_dir, transform=None):
        self.dataframe = dataframe.reset_index(drop=True)
        self.image_dir = image_dir
        self.transform = transform

    def __len__(self):
        return len(self.dataframe)

    def __getitem__(self, idx):
        img_name = self.dataframe.loc[idx, "id_code"] + ".png"
        img_path = os.path.join(self.image_dir, img_name)
        image = Image.open(img_path).convert("RGB")
        label = self.dataframe.loc[idx, "diagnosis"]
        if self.transform:
            image = self.transform(image)
        return image, torch.tensor(label, dtype=torch.long)


def train_one_epoch(model, loader, optimizer, criterion, device):
    """Trains for one epoch, keeping frozen modules in eval mode to protect BatchNorm."""
    model.train()
    # Ensure frozen backbone modules remain in eval mode so running statistics do not change
    for m in model.modules():
        if not any(p.requires_grad for p in m.parameters(recurse=False)):
            m.eval()
    for block in model.blocks[-2:]:
        block.train()
    model.classifier.train()

    total_loss = 0.0
    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * images.size(0)
    return total_loss / len(loader.dataset)


def evaluate(model, loader, device):
    """Evaluates the model on validation data."""
    model.eval()
    all_preds, all_probs, all_labels = [], [], []
    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            probs = torch.softmax(outputs, dim=1)[:, 1]
            _, preds = torch.max(outputs, 1)
            all_preds.extend(preds.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    acc = (all_preds == all_labels).mean()
    prec = precision_score(all_labels, all_preds, zero_division=0)
    rec = recall_score(all_labels, all_preds, zero_division=0)
    f1 = f1_score(all_labels, all_preds, zero_division=0)
    auc = roc_auc_score(all_labels, all_probs) if len(set(all_labels)) > 1 else 0.5
    return acc, prec, rec, f1, auc


def main():
    save_path = os.environ.get("MODEL_SAVE_PATH", "best_model.pth")
    base_path = os.environ.get(
        "APTOS_DATA_PATH",
        os.path.join(os.path.dirname(__file__), "data")
    )
    try:
        epochs = int(os.environ.get("EPOCHS", "10"))
    except ValueError:
        print("Invalid EPOCHS environment variable: must be an integer.", file=sys.stderr)
        sys.exit(1)

    if epochs <= 0:
        print(f"Invalid EPOCHS value '{epochs}': must be a positive integer greater than 0.", file=sys.stderr)
        sys.exit(1)

    batch_size = int(os.environ.get("BATCH_SIZE", "8"))
    lr = float(os.environ.get("LR", "1e-4"))

    train_csv_path = os.path.join(base_path, "train.csv")
    train_images_path = os.path.join(base_path, "train_images")

    if not os.path.exists(train_csv_path):
        print(f"APTOS train.csv not found at: {train_csv_path}. Set APTOS_DATA_PATH environment variable.")
        sys.exit(1)

    df = pd.read_csv(train_csv_path)
    df["diagnosis"] = df["diagnosis"].apply(lambda x: 0 if x == 0 else 1)

    train_df, val_df = train_test_split(
        df, test_size=0.2, stratify=df["diagnosis"], random_state=42
    )
    print(f"Train samples: {len(train_df):,}   Val samples: {len(val_df):,}")

    train_dataset = APTOSDataset(train_df, train_images_path, train_transforms)
    val_dataset = APTOSDataset(val_df, train_images_path, val_transforms)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0, pin_memory=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model = timm.create_model("efficientnet_b0", pretrained=True)
    for param in model.parameters():
        param.requires_grad = False
    for param in model.blocks[-2:].parameters():
        param.requires_grad = True

    model.classifier = nn.Linear(model.classifier.in_features, 2)
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=lr)

    best_auc = -1.0
    best_epoch = -1
    print("\nStarting training...\n")

    for epoch in range(epochs):
        train_loss = train_one_epoch(model, train_loader, optimizer, criterion, device)
        val_acc, val_prec, val_rec, val_f1, val_auc = evaluate(model, val_loader, device)

        print(f"Epoch {epoch+1:2d}/{epochs} | "
              f"Train Loss: {train_loss:.4f} | "
              f"Val AUC: {val_auc:.4f}  Acc: {val_acc:.4f}  F1: {val_f1:.4f}")

        if val_auc > best_auc:
            best_auc = val_auc
            best_epoch = epoch + 1
            torch.save(model.state_dict(), save_path)
            print(f"  → New best AUC! Saved model to: {os.path.abspath(save_path)}")

    print("\n" + "═"*70)
    print(f"Training finished. Best AUC = {best_auc:.4f} (epoch {best_epoch})")
    print(f"Final model file: {os.path.abspath(save_path)}")
    print("═"*70)


if __name__ == "__main__":
    main()
