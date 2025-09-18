import PIL
import torch
from torch import nn, optim
import pytorch_lightning as pl
from torch.utils.data import DataLoader
from src.utils.viz import save_batch_out
from matplotlib import pyplot as plt
from src.model.components.decoder.GlpDecoder import GlpDecoder
from src.model.components.encoder.mit import mit_b4
from src.metrics.quantized_iou import QuantizedIoUMetric
from src.metrics.threshold_accuracy import ThresholdAccuracy


class GlpModel(pl.LightningModule):

    def __init__(self,
                 encoder: nn.Module,
                 decoder: nn.Module,
                 max_light=10.0,
                 loss_reduction: str = 'mean',
                 decoder_channels_out: int = 64,
                 batch_size: int = 32,
                 visualize: bool = False

        ):
        super(GlpModel, self).__init__()
        self.encoder = encoder
        self.decoder = decoder
        self.visualize = visualize
        self.max_light = max_light
        self.loss = nn.L1Loss(reduction=loss_reduction)

        self._train_set = None
        self._test_set = None
        self._val_set = None
        self.batch_size = batch_size

        self.quantized_iou = QuantizedIoUMetric(
            bins=[0.0, 0.05, 0.1, 0.2, 0.5, 1.0],
        )
        self.delta1 = ThresholdAccuracy(threshold=1.25)
        self.delta2 = ThresholdAccuracy(threshold=1.25 ** 2)
        self.delta3 = ThresholdAccuracy(threshold=1.25 ** 3)

        self.final_layer = nn.Sequential(
            nn.Conv2d(decoder_channels_out, decoder_channels_out, kernel_size=3, stride=1, padding=1),
            nn.ReLU(inplace=False),
            nn.Conv2d(decoder_channels_out, 1, kernel_size=3, stride=1, padding=1)
        )


    @classmethod
    def build(cls, batch_size, decoders_channels_in=None, decoders_channels_out=64)  -> 'EncoderDecoderModel':
        encoder  = mit_b4()
        if decoders_channels_in is None:
            decoders_channels_in = [512, 320, 128]
        decoder =GlpDecoder(
                in_channels=decoders_channels_in,
                out_channels=decoders_channels_out,
            )
        return GlpModel(encoder, decoder, decoder_channels_out=decoders_channels_out, batch_size=batch_size)

    @classmethod
    def load_from_checkpoint(cls, checkpoint_path: str, batch_size: int = 1) -> 'GlpModel':
        """Load model from PyTorch Lightning checkpoint"""
        model = cls.build(batch_size)
        checkpoint = torch.load(checkpoint_path, map_location='cpu')
        model.load_state_dict(checkpoint['state_dict'])
        return model

    def forward(self, x, masks=None):

        latent_rep = self.encoder(x)
        out = self.decoder(
            latent_rep[0],
            latent_rep[1],
            latent_rep[2],
            latent_rep[3]
        )
        out = self.final_layer(out)

        return torch.sigmoid(out) * self.max_light

    def validation_step(self, batch, batch_idx: int, dataloader_idx: int = 0):
        img, target, background_mask, img_names = batch
        img = img.float()
        target = target.float()
        out = self.forward(img)

        if self.visualize:
            self._visualize_batch(img, target, out, background_mask, img_names)

        out = out.squeeze()
        loss_val = self.loss(out, target)
        iou_less_0_10 = self.quantized_iou.mean_quantized_iou_le(output=out, target=target, max_value=0.1)
        quantized_iou_mean = self.quantized_iou(output=out, target=target)
        delta1 = self.delta1(out, target)
        delta2 = self.delta2(out, target)
        delta3 = self.delta3(out, target)
        self.log("MAE", loss_val, prog_bar=True)
        self.log("quantized_iou", quantized_iou_mean, prog_bar=True)
        self.log("qiou_le_10%", iou_less_0_10, prog_bar=True)
        self.log("delta1", delta1)
        self.log("delta2", delta2)
        self.log("delta3", delta3)
        return {
            'MAE': loss_val,
            'quantized_iou': quantized_iou_mean,
            'qiou_le_10%': iou_less_0_10,
            'delta1': delta1,
            'delta2': delta2,
            'delta3': delta3

        }

    def test_step(self, batch, batch_idx: int, dataloader_idx: int = 0):
        return self.validation_step(batch, batch_idx, dataloader_idx=0)

    def training_step(self, batch, batch_nb):
        img, target, background_mask, img_names = batch
        img = img.float()
        mask = target.float()
        out = self.forward(img, mask)
        loss_val = self.loss(out.squeeze(), mask)
        self.log("train_loss", loss_val, prog_bar=True)
        self.log("lr", self.opt.param_groups[0]['lr'], prog_bar=True)

        return {'loss': loss_val}


    def configure_optimizers(self):

        self.opt = torch.optim.Adam(self.parameters(), lr=1e-4 )
        self.sch = torch.optim.lr_scheduler.MultiStepLR(self.opt, milestones=[40_000, 60_000, 70_000, 80_000],
                                                        gamma=1/2)
        return [self.opt], [{
            'scheduler': self.sch,
            'interval': 'step',
            'monitor' : 'train_loss'
        }]

    @staticmethod
    def _visualize_batch(batch_img, batch_gt, batch_out, batck_background_mask, batch_img_names):
        save_batch_out(
            batch_img,
            batch_gt,
            batch_out,
            batck_background_mask,
            batch_img_names,
            folder_path="./outputs/viz/",
            save_comparisons=True
        )

    def set_training_dataset(self, trainset):
        self._train_set = trainset

    def set_test_dataset(self, testset):
        self._test_set = testset

    def set_val_dataset(self, valset):
        self._val_set = valset

    def train_dataloader(self):
        if self._train_set is None:
            raise ValueError("Training dataset not set. Use set_training_dataset() to set it.")
        return DataLoader(self._train_set, batch_size=self.batch_size, num_workers=8, persistent_workers=True, shuffle=True)

    def test_dataloader(self):
        if self._test_set is None:
            raise ValueError("Test dataset not set. Use set_test_dataset() to set it.")
        return DataLoader(self._test_set, batch_size=self.batch_size, num_workers=8, persistent_workers=True, shuffle=True)


    def val_dataloader(self):
        if self._val_set is None:
            raise ValueError("Validation dataset not set. Use set_val_dataset() to set it.")
        return DataLoader(self._val_set, batch_size=self.batch_size, num_workers=8, persistent_workers=True, shuffle=False)

