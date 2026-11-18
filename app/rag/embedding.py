from functools import lru_cache
from pathlib import Path
import threading
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

MODEL_NAME = 'intfloat/multilingual-e5-small'
EXPORT_REPO = 'Xenova/multilingual-e5-small'
REVISION = '761b726dd34fb83930e26aab4e9ac3899aa1fa78'
MODEL_ID = f'{EXPORT_REPO}@{REVISION}:int8:mean:l2'
DIMENSION = 384
MODEL_DIR = Path('models/multilingual-e5-small')


class EmbeddingUnavailable(RuntimeError):
    pass


class Embedder:
    def __init__(self, directory: Path = MODEL_DIR):
        if not (directory / 'onnx/model_quantized.onnx').is_file():
            raise EmbeddingUnavailable('Run python -m scripts.download_embedding first')
        self.tokenizer = Tokenizer.from_file(str(directory / 'tokenizer.json'))
        self.tokenizer.enable_padding(pad_id=1, pad_token='<pad>')
        self.tokenizer.no_truncation()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(directory / 'onnx/model_quantized.onnx'), sess_options=options,
                                            providers=['CPUExecutionProvider'])
        self.lock = threading.Lock()

    def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
        vectors = []
        for start in range(0, len(texts), 8):
            prefixed = [('query: ' if query else 'passage: ') + s for s in texts[start:start+8]]
            with self.lock:
                encoded = self.tokenizer.encode_batch(prefixed)
            if any(len(x.ids) > 512 for x in encoded):
                raise ValueError('Embedding text exceeds 512 tokens; split before indexing')
            ids = np.asarray([x.ids for x in encoded], dtype=np.int64)
            mask = np.asarray([x.attention_mask for x in encoded], dtype=np.int64)
            inputs = {'input_ids': ids, 'attention_mask': mask}
            if any(x.name == 'token_type_ids' for x in self.session.get_inputs()):
                inputs['token_type_ids'] = np.asarray([x.type_ids for x in encoded], dtype=np.int64)
            hidden = self.session.run(None, inputs)[0]
            pooled = (hidden * mask[...,None]).sum(axis=1) / mask.sum(axis=1)[:,None]
            pooled = pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)
            if pooled.shape[1] != DIMENSION or not np.isfinite(pooled).all():
                raise EmbeddingUnavailable('Unexpected embedding shape or values')
            vectors.extend(pooled.astype(np.float32).tolist())
        return vectors


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    return Embedder()
