# Per-process stub to bypass a broken torchaudio (CUDA-mismatch) in the shared base env.
# transformers imports torchaudio for audio models we never use; serving text models
# only needs the import to succeed. This file is only on PYTHONPATH for our server
# processes — it does NOT modify any installed package.
__version__ = "0.0.0-stub"
def __getattr__(name):  # tolerate any attribute access
    raise AttributeError(name)
