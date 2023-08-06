import torch
from torch import Tensor, nn
from vocos.spectral_ops import ISTFT


class ISTFTHead(nn.Module):
    """
    ISTFT Head module for predicting STFT complex coefficients.

    Args:
        dim (int): Hidden dimension of the model.
        n_fft (int): Size of Fourier transform.
        hop_length (int): The distance between neighboring sliding window frames, which should align with
                          the resolution of the input features.
        win_length (int): The size of window frame and STFT filter.
        padding (str, optional): Type of padding. Options are "center" or "same". Defaults to "same".
    """  # noqa: E501

    def __init__(
        self,
        dim: int,
        n_fft: int,
        hop_length: int,
        win_length: int,
        padding: str = "same",
    ):
        super().__init__()

        self.n_fft = n_fft
        self.hop_length = hop_length
        self.win_length = win_length

        self.istft = ISTFT(
            n_fft=n_fft,
            hop_length=hop_length,
            win_length=win_length,
            padding=padding,
        )

        out_dim = n_fft * 2
        self.out = nn.Conv1d(dim, out_dim, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass of the ISTFTHead module.

        Args:
            x (Tensor): Input tensor of shape (B, H, L), where B is the batch size,
                        L is the sequence length, and H denotes the model dimension.

        Returns:
            Tensor: Reconstructed time-domain audio signal of shape (B, T), where T is the length of the output signal.
        """  # noqa: E501

        x = self.out(x)

        mag, p = x.chunk(2, dim=1)
        mag = torch.exp(mag)
        mag = torch.clip(
            mag, max=1e2
        )  # safeguard to prevent excessively large magnitudes

        # wrapping happens here. These two lines produce real and imaginary value
        x = torch.cos(p)
        y = torch.sin(p)

        S = mag * (x + 1j * y)

        return self.istft(S)

        # x = torch.istft(
        #     S,
        #     n_fft=self.n_fft,
        #     hop_length=self.hop_length,
        #     win_length=self.win_length,
        #     window=self.istft.window,
        #     center=False,
        #     normalized=False,
        #     return_complex=False,
        # )

        # pad = (self.win_length - self.hop_length) // 2
        # x = x[:, pad:-pad]
        # return x


class VocosGenerator(nn.Module):
    def __init__(self, backbone: nn.Module, head: nn.Module):
        super().__init__()

        self.backbone = backbone
        self.head = head

    def forward(self, x: Tensor) -> Tensor:
        x = self.backbone(x)
        x = self.head(x)

        if x.ndim == 2:
            x = x[:, None, :]

        return x

    def remove_weight_norm(self):
        if hasattr(self.backbone, "remove_weight_norm"):
            self.backbone.remove_weight_norm()

        if hasattr(self.head, "remove_weight_norm"):
            self.head.remove_weight_norm()
