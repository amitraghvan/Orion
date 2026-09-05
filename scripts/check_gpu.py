"""Hardware accelerator diagnostic utility for NVIDIA CUDA, Apple MPS, and CPU fallback."""

import shutil
import subprocess


def check_gpu() -> None:
    print("==================================================================")
    print("⚡ Hardware Accelerator Diagnostic")
    print("==================================================================")

    # Check nvidia-smi
    smi_path = shutil.which("nvidia-smi")
    if smi_path:
        print(f"✅ nvidia-smi discovered at {smi_path}")
        try:
            res = subprocess.run(
                [
                    smi_path,
                    "--query-gpu=name,memory.total,memory.free,temperature.gpu",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                print("   GPU Telemetry:")
                for line in res.stdout.strip().split("\n"):
                    print(f"   - {line}")
        except Exception as e:
            print(f"   ⚠️ Could not query nvidia-smi: {e}")
    else:
        print("ℹ️ NVIDIA CUDA (nvidia-smi) not detected on host system.")

    # Check PyTorch device availability if installed
    try:
        import importlib.util

        if importlib.util.find_spec("torch") is not None:
            torch = importlib.import_module("torch")
            print(f"🐍 PyTorch version: {torch.__version__}")
            if torch.cuda.is_available():
                print(f"   ✅ CUDA available: {torch.cuda.get_device_name(0)}")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                print("   ✅ Apple Silicon MPS (Metal Performance Shaders) available.")
            else:
                print("   ℹ️ PyTorch running on CPU execution provider.")
        else:
            print("ℹ️ PyTorch is not installed in current environment (CPU baseline active).")
    except Exception:
        print("ℹ️ PyTorch inspection skipped.")

    print("==================================================================")


if __name__ == "__main__":
    check_gpu()
