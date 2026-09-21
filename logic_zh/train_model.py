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
    """加载已标注的 3x3 图块，施加径向权重并进行 ImageNet 归一化。"""

    def __init__(self, dataframe):
        self.dataframe = dataframe
        self.label_map = {"empty": 0, "bead": 1}
        self.valid_data = []


        self.normalize = transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )


        # 固定径向权重，不属于可学习注意力层。
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

        print(f"数据集加载完成: 总数 {len(dataframe)}, 有效 {len(self.valid_data)}")

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
    """微调 Swin-Tiny，并按现有保存和早停规则输出权重。"""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🚀 启动训练 (Swin-Transformer) | Device: {device}")
    print(f"配置文件: {label_csv}")
    print(f"训练参数: Epochs = {epochs}, Batch Size = {batch_size}, Patience = {patience}")


    try:
        df = pd.read_csv(label_csv)
        df['output_path'] = df['output_path'].apply(
            lambda x: os.path.normpath(str(x).replace('/', os.sep).replace('\\', os.sep))
        )
    except Exception as e:
        print(f"无法读取 CSV 文件: {e}")
        return


    try:
        train_df, val_df = train_test_split(df, test_size=0.2, stratify=df['label'], random_state=42)
    except Exception as e:
        print(f"无法进行分层抽样 (可能某类样本太少)，尝试随机划分: {e}")
        train_df, val_df = train_test_split(df, test_size=0.2, random_state=42)

    train_dataset = ComponentDataset(train_df)
    val_dataset = ComponentDataset(val_df)

    if len(train_dataset) == 0:
        print("❌ 训练集为空，请检查 CSV 中的路径是否正确！")
        return


    # 在当前进程加载数据，以适配 Windows GUI。
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0, pin_memory=True)


    print("正在初始化模型...")
    model = timm.create_model('swin_tiny_patch4_window7_224', pretrained=False, num_classes=2)

    if os.path.exists(pretrained_weight_path):
        print(f"正在加载预训练权重: {pretrained_weight_path}")
        checkpoint = torch.load(pretrained_weight_path, map_location='cpu')

        state_dict = checkpoint.get('model', checkpoint)


        new_state_dict = OrderedDict()
        for k, v in state_dict.items():
            # 加载骨干权重时排除预训练分类头。
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
            print("✅ 权重加载成功！(Swin-Tiny 官方权重已自动对齐)")
        else:
            print(f"⚠️ 警告：仍有非 Head 键缺失: {relevant_missing[:5]}")
    else:
        print(f"❌ 找不到预训练权重文件: {pretrained_weight_path}")
        raise FileNotFoundError(f"请确保预训练权重文件存在: {pretrained_weight_path}")

    model = model.to(device)
    print(f"使用设备: {device}")


    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.01)


    acc_check = [30.0]
    loss_check = [0.5]
    epochs_no_improve = 0

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


        # 准确率或训练损失改善时保存，并非仅按最优验证准确率选模。
        if val_acc - max(acc_check) > 1 or min(loss_check) - train_loss > 0.01:
            epochs_no_improve = 0
            # 仅保存模型参数，不包含优化器及训练轮次状态。
            torch.save(model.state_dict(), output_model_path)
            print(f"🚀 新纪录！模型已保存 (Acc: {val_acc:.2f}%)")
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                print(f"🛑 早停触发 (连续 {patience} 轮无提升)！停止训练。")
                break

        acc_check.append(val_acc)
        loss_check.append(train_loss)

    print(f"✅ 训练结束！最佳验证集准确率: {max(acc_check):.2f}%")
    print(f"模型路径: {output_model_path}")
