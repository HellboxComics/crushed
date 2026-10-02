"""Exact object mask from a real photo with BiRefNet (MIT), the same cut-out model the drawing room uses."""
import numpy as np
from PIL import Image

_M = None


def mask(img, size=1024):
    global _M
    import torch
    from transformers import AutoModelForImageSegmentation
    from torchvision import transforms
    if _M is None:
        _M = AutoModelForImageSegmentation.from_pretrained("ZhengPeng7/BiRefNet", trust_remote_code=True).eval()
    im = img.convert("RGB")
    t = transforms.Compose([transforms.Resize((size, size)), transforms.ToTensor(),
                            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
    with torch.no_grad():
        p = _M(t(im).unsqueeze(0))[-1].sigmoid()[0, 0].numpy()
    return np.asarray(Image.fromarray((p * 255).astype(np.uint8)).resize(im.size, Image.BILINEAR)) / 255.0
