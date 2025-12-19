from pathlib import Path

from matplotlib import pyplot as plt
import PIL


def save_comparison(img, gt, out, path):
    fig, ax = plt.subplots(1, 4, figsize=(12, 4))
    clip_out = out.clamp(0, 1)
    ax[0].imshow(img.permute(1, 2, 0).cpu().numpy())
    ax[0].set_title("Input Image")
    ax[1].imshow((gt.cpu().numpy() * 255).astype('uint8'))
    ax[1].set_title("Ground Truth")
    ax[2].imshow((clip_out.squeeze().cpu().numpy() * 255).astype('uint8'))
    ax[2].set_title("Predicted Output")
    ax[3].imshow(((clip_out - gt).abs().squeeze().cpu().numpy() * 255).astype('uint8'))
    ax[3].set_title("Prediction - target")
    plt.savefig(path)
    plt.close(fig)


def save_out(out, background_mask, path):
    clip_out = out.clamp(0, 1)
    res_img = PIL.Image.fromarray(
        (clip_out.squeeze().clamp(0.0, 1.0).cpu().numpy() * 255).astype('uint8'))
    # add alpha channel to res_img
    res_img.putalpha(PIL.Image.fromarray((background_mask.cpu().numpy() * 255).astype('uint8')))

    res_img.save(path)


def save_batch_out(
        batch_img,
        batch_gt,
        batch_out,
        batch_background_mask,
        batch_img_names,
        folder_path,
        save_comparisons=True
):
    path_comparison = Path(folder_path) / "comparison"
    path_out = Path(folder_path) / "simulations"
    path_comparison.mkdir(parents=True, exist_ok=True)
    path_out.mkdir(parents=True, exist_ok=True)

    for i in range(batch_img.shape[0]):
        if save_comparisons:
            path_img_comparison = path_comparison / f"comparison_{batch_img_names[i]}"
            save_comparison(batch_img[i], batch_gt[i], batch_out[i], path_img_comparison)

        path_img_out = path_out / f"res_{batch_img_names[i]}"
        save_out(batch_out[i], batch_background_mask[i], path_img_out)