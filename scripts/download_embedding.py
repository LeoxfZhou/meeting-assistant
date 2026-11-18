"""Download pinned public ONNX assets with TLS verification and bounded retries."""
import hashlib
import json
import time
from pathlib import Path
import httpx

REPO = 'Xenova/multilingual-e5-small'
REVISION = '761b726dd34fb83930e26aab4e9ac3899aa1fa78'
FILES = ['tokenizer.json', 'tokenizer_config.json', 'config.json', 'onnx/model_quantized.onnx']


def main():
    directory = Path('models/multilingual-e5-small')
    manifest_path = directory / 'manifest.json'
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    hashes = {}
    with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(60, connect=15)) as client:
        for filename in FILES:
            target = directory / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and old.get('revision') == REVISION and old.get('sha256',{}).get(filename)==hashlib.sha256(target.read_bytes()).hexdigest():
                hashes[filename] = old['sha256'][filename]
                continue
            for attempt in range(3):
                try:
                    with client.stream('GET',f'https://huggingface.co/{REPO}/resolve/{REVISION}/{filename}') as response:
                        response.raise_for_status()
                        digest=hashlib.sha256()
                        with target.with_suffix(target.suffix+'.part').open('wb') as out:
                            for data in response.iter_bytes():
                                out.write(data);digest.update(data)
                    target.with_suffix(target.suffix+'.part').replace(target)
                    hashes[filename]=digest.hexdigest()
                    print('Downloaded',filename,flush=True)
                    break
                except httpx.HTTPError:
                    if attempt==2:
                        raise SystemExit('Public model download failed after 3 attempts; retry later.') from None
                    time.sleep(2**attempt)
    manifest_path.write_text(json.dumps({'repo':REPO,'revision':REVISION,'sha256':hashes},indent=2))
    print('Pinned CPU embedding model ready; manifest saved locally.')


if __name__ == '__main__':
    main()
