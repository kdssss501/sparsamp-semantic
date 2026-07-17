# Experiment Environment

## Local GPU

- gpu: local
- GPU: NVIDIA GeForce RTX 3060 Laptop GPU, 6GB VRAM
- Python: `.venv\Scripts\python.exe` (CPython 3.11)
- CUDA PyTorch: `2.7.1+cu126`
- Primary model: `models/qwen2.5-1.5b-instruct`
- Code sync: git
- W&B: false
- Initial ARIS pilot budget: 8 GPU-hours

## Execution Rules

- Check `nvidia-smi` before every GPU experiment.
- Stop the local Web API before experiments when it holds Qwen weights in VRAM.
- Save logs below `outputs/logs/` and machine-readable rows below `outputs/`.
- Model weights, official artifacts, API recordings, keys, and outputs remain Git-ignored.
- Run one GPU experiment at a time on the 6GB device.
