from .LinsooSaveImage import LinsooSaveImage
from .LinsooEmptyLatentImage import LinsooEmptyLatentImage
from .LinsooMultiInputOutput import LinsooMultiOutputs, LinsooMultiInputs


NODE_CLASS_MAPPINGS = {
    "LinsooSaveImage": LinsooSaveImage,
    "LinsooEmptyLatentImage": LinsooEmptyLatentImage,
    "LinsooMultiInputs": LinsooMultiInputs,
    "LinsooMultiOutputs": LinsooMultiOutputs,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LinsooSaveImage": "Linsoo Save Image",
    "LinsooEmptyLatentImage": "Linsoo Empty Latent Image",
    "LinsooMultiInputs": "Linsoo Multi Inputs",
    "LinsooMultiOutputs": "Linsoo Multi Outputs",
}
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']