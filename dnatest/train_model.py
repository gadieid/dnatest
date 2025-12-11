import argparse
import json
from pathlib import Path
from typing import List, Tuple, Dict

import pandas as pd
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader


def clean_sequence(seq: str) -> str:
    """Strip angle brackets and keep uppercase letters only."""
    if not isinstance(seq, str):
        return ""
    # Many rows look like <ACGT...>; keep inner content and uppercase it.
    seq = seq.strip()
    if seq.startswith("<") and seq.endswith(">"):
        seq = seq[1:-1]
    return "".join(ch for ch in seq.upper() if ch.isalpha())


def build_vocab(seqs: List[str]) -> Dict[str, int]:
    """Create a simple character vocabulary from sequences."""
    chars = sorted({ch for seq in seqs for ch in seq})
    vocab = {ch: idx + 1 for idx, ch in enumerate(chars)}  # reserve 0 for padding
    return vocab


def encode_sequence(seq: str, vocab: Dict[str, int], max_len: int) -> List[int]:
    token_ids = [vocab.get(ch, 0) for ch in seq[:max_len]]
    if len(token_ids) < max_len:
        token_ids += [0] * (max_len - len(token_ids))
    return token_ids


class SequenceDataset(Dataset):
    def __init__(
        self,
        df: pd.DataFrame,
        vocab: Dict[str, int],
        label_to_idx: Dict[str, int],
        max_len: int,
    ):
        self.vocab = vocab
        self.label_to_idx = label_to_idx
        self.max_len = max_len
        self.labels = df["GeneType"].tolist()
        self.seqs = df["NucleotideSequence"].tolist()

    def __len__(self) -> int:
        return len(self.seqs)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        seq = clean_sequence(self.seqs[idx])
        encoded = torch.tensor(encode_sequence(seq, self.vocab, self.max_len), dtype=torch.long)
        label = torch.tensor(self.label_to_idx[self.labels[idx]], dtype=torch.long)
        return encoded, label


class SmallGRUClassifier(nn.Module):
    def __init__(self, vocab_size: int, num_labels: int, embed_dim: int = 16, hidden_size: int = 32):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size + 1, embed_dim, padding_idx=0)
        self.gru = nn.GRU(embed_dim, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_labels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        emb = self.embedding(x)
        _, h_n = self.gru(emb)
        logits = self.fc(h_n.squeeze(0))
        return logits


def load_data(train_path: Path, val_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)

    # Drop potential unnamed index column
    for df in (train_df, val_df):
        if df.columns[0].startswith("Unnamed") or df.columns[0] == "":
            df.drop(columns=df.columns[0], inplace=True)
    return train_df, val_df


def prepare_datasets(train_df: pd.DataFrame, val_df: pd.DataFrame, max_len: int):
    # Clean sequences for vocab building
    train_seqs = train_df["NucleotideSequence"].map(clean_sequence).tolist()
    vocab = build_vocab(train_seqs)

    labels = sorted(train_df["GeneType"].unique().tolist())
    label_to_idx = {lbl: i for i, lbl in enumerate(labels)}
    idx_to_label = {i: lbl for lbl, i in label_to_idx.items()}

    train_ds = SequenceDataset(train_df, vocab, label_to_idx, max_len)
    val_ds = SequenceDataset(val_df, vocab, label_to_idx, max_len)
    return train_ds, val_ds, vocab, label_to_idx, idx_to_label


def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0.0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad()
        logits = model(x)
        loss = criterion(logits, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * x.size(0)
    return total_loss / len(loader.dataset)


def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    correct = 0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            logits = model(x)
            loss = criterion(logits, y)
            total_loss += loss.item() * x.size(0)
            preds = logits.argmax(dim=1)
            correct += (preds == y).sum().item()
    avg_loss = total_loss / len(loader.dataset)
    acc = correct / len(loader.dataset)
    return avg_loss, acc


def save_artifacts(
    path: Path,
    model_state,
    vocab,
    label_to_idx,
    idx_to_label,
    config: Dict,
):
    payload = {
        "model_state": model_state,
        "vocab": vocab,
        "label_to_idx": label_to_idx,
        "idx_to_label": idx_to_label,
        "config": config,
    }
    torch.save(payload, path)

    meta = {
        "artifact": str(path),
        "config": config,
        "num_labels": len(label_to_idx),
        "vocab_size": len(vocab),
    }
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Train a small GRU classifier on gene sequences.")
    parser.add_argument("--train_csv", type=Path, default=Path("train.csv"))
    parser.add_argument("--val_csv", type=Path, default=Path("validation.csv"))
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=64)
    parser.add_argument("--max_len", type=int, default=512, help="Pad/truncate sequences to this length.")
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--save_path", type=Path, default=Path("model_artifacts.pt"))
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    train_df, val_df = load_data(args.train_csv, args.val_csv)
    train_ds, val_ds, vocab, label_to_idx, idx_to_label = prepare_datasets(train_df, val_df, args.max_len)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size)

    model = SmallGRUClassifier(vocab_size=len(vocab), num_labels=len(label_to_idx)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    for epoch in range(1, args.epochs + 1):
        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc = evaluate(model, val_loader, criterion, device)
        print(f"Epoch {epoch}/{args.epochs} - train loss: {train_loss:.4f} | val loss: {val_loss:.4f} | val acc: {val_acc:.3f}")

    config = {
        "max_len": args.max_len,
        "embed_dim": 16,
        "hidden_size": 32,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
    }
    save_artifacts(args.save_path, model.state_dict(), vocab, label_to_idx, idx_to_label, config)
    print(f"Saved model and metadata to {args.save_path} and {args.save_path.with_suffix('.json')}")


if __name__ == "__main__":
    main()

