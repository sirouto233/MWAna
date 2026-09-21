import os
import cv2
import numpy as np
import pandas as pd
from collections import OrderedDict

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from sklearn.model_selection import train_test_split
import timm


class ComponentDataset(Dataset):
    """Load labeled 3x3 patches with radial weighting and ImageNet normalization."""

    def __init__(self, dataframe):
        self.dataframe = dataframe
        self.label_map = {"empty": 0, "bead": 1}
        self.valid_data = []

        self.normalize = transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )


        # Fixed radial weighting; this is not a learned attention layer.
        x = np.linspace(-1, 1, 224)
        y = np.linspace(-1, 1, 224)
        xx, yy = np.meshgrid(x, y)
        r = np.sqrt(xx ** 2 + yy ** 2)
        self.vignette = np.clip(np.exp(-(r ** 2) / (2 * 1.2 ** 2)), 0.6, 1.0).astype(np.float32)


        for idx in range(len(dataframe)):
            img_path = dataframe.iloc[idx]['output_path']
            img_path = os.path.normpath(str(img_path).replace('/', os.sep).replace('\\', os.sep))

            if os.path.exists(img_path):
                self.valid_data.append((idx, img_path))

        print(f"Dataset initialized: {len(dataframe)} total records, {len(self.valid_data)} valid files.")

    def __len__(self):
        return len(self.valid_data)

    def __getitem__(self, idx):
        actual_idx, img_path = self.valid_data[idx]
        label_str = self.dataframe.iloc[actual_idx]['label']
        label = self.label_map[label_str]

        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            img = np.zeros((224, 224), dtype=np.uint8)

        img = cv2.resize(img, (224, 224))


        img = (img.astype(np.float32) * self.vignette).astype(np.uint8)


        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

        img_tensor = torch.from_numpy(img).permute(2, 0, 1).float() / 255.0
        img_tensor = self.normalize(img_tensor)

        return img_tensor, label


def run_training(label_csv, output_model_path, pretrained_weight_path, epochs=30, batch_size=16, patience=5):
    """Fine-tune Swin-Tiny with the existing checkpoint and early-stopping rule."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Starting Swin-Transformer training pipeline | Device: {device}")
    print(f"Config: Epochs={epochs}, Batch Size={batch_size}, Patience={patience}")
    print(f"Dataset: {label_csv}")


    try:
        df = pd.read_csv(label_csv)
        df['output_path'] = df['output_path'].apply(
            lambda x: os.path.normpath(str(x).replace('/', os.sep).replace('\\', os.sep))
        )
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        return

    try:
        train_df, val_df = train_test_split(df, test_size=0.2, stratify=df['label'], random_state=42)
    except Exception as e:
        print(
            f"Warning: Stratified split failed (likely insufficient samples in one class). Falling back to random split: {e}")
        train_df, val_df = train_test_split(df, test_size=0.2, random_state=42)

    train_dataset = ComponentDataset(train_df)
    val_dataset = ComponentDataset(val_df)

    if len(train_dataset) == 0:
        print("Error: Training dataset is empty. Verify the image paths in the CSV.")
        return


    # Keep loading in this process for the Windows GUI workflow.
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0, pin_memory=True)


    print("Initializing model...")
    model = timm.create_model('swin_tiny_patch4_window7_224', pretrained=False, num_classes=2)

    if os.path.exists(pretrained_weight_path):
        print(f"Loading pretrained weights: {pretrained_weight_path}")
        checkpoint = torch.load(pretrained_weight_path, map_location='cpu')
        state_dict = checkpoint.get('model', checkpoint)


        new_state_dict = OrderedDict()
        for k, v in state_dict.items():
            # Discard the pretraining classifier before loading the backbone.
            if k.startswith('head'):
                continue
            if 'downsample' in k:
                parts = k.split('.')
                if parts[0] == 'layers' and parts[2] == 'downsample':
                    layer_idx = int(parts[1])
                    new_key = f"layers.{layer_idx + 1}.{'.'.join(parts[2:])}"
                    new_state_dict[new_key] = v
                    continue
            new_state_dict[k] = v

        msg = model.load_state_dict(new_state_dict, strict=False)
        relevant_missing = [k for k in msg.missing_keys if not k.startswith('head') and 'downsample' not in k]

        if len(relevant_missing) == 0:
            print("Pretrained weights loaded successfully.")
        else:
            print(f"Warning: Missing non-head keys detected: {relevant_missing[:5]}")
    else:
        raise FileNotFoundError(f"Pretrained weight file not found: {pretrained_weight_path}")

    model = model.to(device)


    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.01)


    acc_history = [30.0]
    loss_history = [0.5]
    epochs_without_improvement = 0

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0

        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()

        train_loss = running_loss / len(train_loader)


        model.eval()
        correct = 0
        total = 0
        with torch.inference_mode():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                _, predicted = torch.max(outputs.data, 1)

                total += labels.size(0)
                correct += (predicted == labels).sum().item()

        val_acc = 100 * correct / total
        print(f"Epoch {epoch + 1}/{epochs} | Train Loss: {train_loss:.4f} | Val Acc: {val_acc:.2f}%")


        # Save on accuracy OR training-loss improvement; not validation-best selection.
        if val_acc - max(acc_history) > 1 or min(loss_history) - train_loss > 0.01:
            epochs_without_improvement = 0
            # Save model parameters only; optimizer and epoch state are not included.
            torch.save(model.state_dict(), output_model_path)
            print(f"New best model saved! (Val Acc: {val_acc:.2f}%)")
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= patience:
                print(f"Early stopping triggered after {patience} epochs without improvement.")
                break

        acc_history.append(val_acc)
        loss_history.append(train_loss)

    print(f"Training completed. Best validation accuracy: {max(acc_history):.2f}%")
    print(f"Model saved to: {output_model_path}")


if __name__ == "__main__":
    pass
